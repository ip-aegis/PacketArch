"""Extract learned pattern values and generate template enhancement recommendations.

This script queries the learned patterns from processed PCAPs and outputs
recommended values for updating scenario template definitions.

Usage:
    python scripts/enhance_templates_from_learned.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.models.learned_pattern import LearnedPattern
from app.models.learned_protocol_pattern import LearnedProtocolPattern
from app.models.device_template import DeviceTemplate, TemplateSource
from app.models.learned_sequence import LearnedSequence


def infer_jitter_type(timing_data: dict) -> str:
    """Infer the best jitter type based on timing distribution."""
    if not timing_data:
        return "uniform"

    # Check for distribution shape indicators
    std_dev = timing_data.get("std_dev", 0)
    mean = timing_data.get("mean", 1)

    if std_dev == 0:
        return "uniform"

    # Coefficient of variation
    cv = std_dev / mean if mean > 0 else 0

    # High CV suggests exponential (common in WAN/remote systems)
    if cv > 0.5:
        return "exponential"
    # Medium CV suggests gaussian (common in LAN systems)
    elif cv > 0.1:
        return "gaussian"
    # Low CV suggests uniform (deterministic systems)
    else:
        return "uniform"


async def get_timing_patterns_by_protocol(db: AsyncSession) -> dict:
    """Get aggregated timing patterns for each protocol."""
    from app.models.learned_pattern import PatternType

    result = await db.execute(
        select(LearnedPattern).where(LearnedPattern.pattern_type == PatternType.TIMING)
    )
    patterns = result.scalars().all()

    timing_by_protocol = {}

    for pattern in patterns:
        protocol = pattern.protocol.lower()
        if protocol not in timing_by_protocol:
            timing_by_protocol[protocol] = {
                "intervals": [],
                "jitters": [],
                "sample_count": 0,
            }

        # Use the actual model fields
        if pattern.mean_value is not None:
            timing_by_protocol[protocol]["intervals"].append(pattern.mean_value)
        if pattern.std_dev is not None:
            timing_by_protocol[protocol]["jitters"].append(pattern.std_dev)
        timing_by_protocol[protocol]["sample_count"] += pattern.sample_count or 0

    # Aggregate
    aggregated = {}
    for protocol, data in timing_by_protocol.items():
        if data["intervals"]:
            mean_interval = sum(data["intervals"]) / len(data["intervals"])
            mean_jitter = sum(data["jitters"]) / len(data["jitters"]) if data["jitters"] else 0
            aggregated[protocol] = {
                "poll_interval_ms": round(mean_interval, 1),
                "jitter_ms": round(mean_jitter, 1),
                "jitter_type": infer_jitter_type({"mean": mean_interval, "std_dev": mean_jitter}),
                "sample_count": data["sample_count"],
                "pattern_count": len(data["intervals"]),
            }

    return aggregated


async def get_protocol_patterns_by_protocol(db: AsyncSession) -> dict:
    """Get function code distributions and address patterns for each protocol."""
    result = await db.execute(select(LearnedProtocolPattern))
    patterns = result.scalars().all()

    patterns_by_protocol = {}

    for pattern in patterns:
        protocol = pattern.protocol.lower()
        if protocol not in patterns_by_protocol:
            patterns_by_protocol[protocol] = {
                "function_codes_all": {},
                "address_patterns_all": [],
                "sample_count": 0,
            }

        # Aggregate function codes
        if pattern.function_codes:
            for fc, data in pattern.function_codes.items():
                fc_key = str(fc)
                if fc_key not in patterns_by_protocol[protocol]["function_codes_all"]:
                    patterns_by_protocol[protocol]["function_codes_all"][fc_key] = {
                        "name": data.get("name", f"fc_{fc}"),
                        "total_count": 0,
                    }
                patterns_by_protocol[protocol]["function_codes_all"][fc_key]["total_count"] += data.get("count", 0)

        # Collect address patterns
        if pattern.address_patterns:
            patterns_by_protocol[protocol]["address_patterns_all"].append(pattern.address_patterns)

        patterns_by_protocol[protocol]["sample_count"] += pattern.sample_count or 0

    # Calculate distributions
    result = {}
    for protocol, data in patterns_by_protocol.items():
        total_fc_count = sum(fc["total_count"] for fc in data["function_codes_all"].values())

        function_codes = {}
        if total_fc_count > 0:
            for fc, fc_data in data["function_codes_all"].items():
                freq = fc_data["total_count"] / total_fc_count
                if freq >= 0.01:  # Only include if >= 1% frequency
                    function_codes[int(fc)] = {
                        "name": fc_data["name"],
                        "frequency": round(freq, 4),
                    }

        # Merge address patterns
        merged_addresses = {}
        for addr_pattern in data["address_patterns_all"]:
            for addr_type, addr_data in addr_pattern.items():
                if addr_type not in merged_addresses:
                    merged_addresses[addr_type] = {
                        "min_address": float("inf"),
                        "max_address": 0,
                        "total_accesses": 0,
                    }
                if "min_address" in addr_data:
                    merged_addresses[addr_type]["min_address"] = min(
                        merged_addresses[addr_type]["min_address"],
                        addr_data["min_address"]
                    )
                if "max_address" in addr_data:
                    merged_addresses[addr_type]["max_address"] = max(
                        merged_addresses[addr_type]["max_address"],
                        addr_data["max_address"]
                    )
                merged_addresses[addr_type]["total_accesses"] += addr_data.get("total_accesses", 0)

        # Clean up inf values
        for addr_type in merged_addresses:
            if merged_addresses[addr_type]["min_address"] == float("inf"):
                merged_addresses[addr_type]["min_address"] = 0

        result[protocol] = {
            "function_codes": function_codes,
            "address_patterns": merged_addresses,
            "sample_count": data["sample_count"],
        }

    return result


async def get_fingerprint_stats(db: AsyncSession) -> dict:
    """Get device fingerprint statistics by protocol and role."""
    result = await db.execute(
        select(DeviceTemplate).where(
            DeviceTemplate.source == TemplateSource.PCAP_LEARNED.value,
        )
    )
    fingerprints = result.scalars().all()

    stats = {}
    response_timings = {}

    for fp in fingerprints:
        # Collect response timings by protocol
        if fp.response_timings:
            for protocol, timing in fp.response_timings.items():
                protocol = protocol.lower()
                if protocol not in response_timings:
                    response_timings[protocol] = {
                        "means": [],
                        "mins": [],
                        "maxs": [],
                    }
                if "mean_ms" in timing:
                    response_timings[protocol]["means"].append(timing["mean_ms"])
                if "min_ms" in timing:
                    response_timings[protocol]["mins"].append(timing["min_ms"])
                if "max_ms" in timing:
                    response_timings[protocol]["maxs"].append(timing["max_ms"])

        # Count by role
        role = fp.role or "unknown"
        for protocol in (fp.active_protocols or []):
            protocol = protocol.lower()
            if protocol not in stats:
                stats[protocol] = {"master": 0, "slave": 0, "both": 0, "unknown": 0}
            stats[protocol][role] = stats[protocol].get(role, 0) + 1

    # Aggregate response timings
    aggregated_response = {}
    for protocol, data in response_timings.items():
        if data["means"]:
            aggregated_response[protocol] = {
                "mean_ms": round(sum(data["means"]) / len(data["means"]), 2),
                "min_ms": round(min(data["mins"]) if data["mins"] else 0, 2),
                "max_ms": round(max(data["maxs"]) if data["maxs"] else 0, 2),
            }

    return {
        "role_counts": stats,
        "response_timings": aggregated_response,
    }


async def get_sequence_stats(db: AsyncSession) -> dict:
    """Get sequence statistics by protocol and type."""
    result = await db.execute(select(LearnedSequence))
    sequences = result.scalars().all()

    stats = {}

    for seq in sequences:
        protocol = seq.protocol.lower()
        seq_type = str(seq.sequence_type).replace("SequenceType.", "").lower()

        if protocol not in stats:
            stats[protocol] = {}

        if seq_type not in stats[protocol]:
            stats[protocol][seq_type] = {
                "count": 0,
                "avg_duration_ms": [],
                "avg_steps": [],
            }

        stats[protocol][seq_type]["count"] += 1
        if seq.average_duration_ms:
            stats[protocol][seq_type]["avg_duration_ms"].append(seq.average_duration_ms)
        if seq.step_count:
            stats[protocol][seq_type]["avg_steps"].append(seq.step_count)

    # Aggregate
    for protocol in stats:
        for seq_type in stats[protocol]:
            data = stats[protocol][seq_type]
            if data["avg_duration_ms"]:
                data["avg_duration_ms"] = round(
                    sum(data["avg_duration_ms"]) / len(data["avg_duration_ms"]), 1
                )
            else:
                data["avg_duration_ms"] = None
            if data["avg_steps"]:
                data["avg_steps"] = round(
                    sum(data["avg_steps"]) / len(data["avg_steps"]), 1
                )
            else:
                data["avg_steps"] = None

    return stats


async def generate_template_enhancements():
    """Generate comprehensive template enhancement recommendations."""
    async with async_session_maker() as db:
        print("=" * 70)
        print("TEMPLATE ENHANCEMENT RECOMMENDATIONS FROM LEARNED PATTERNS")
        print("=" * 70)

        # Get all data
        timing_data = await get_timing_patterns_by_protocol(db)
        protocol_data = await get_protocol_patterns_by_protocol(db)
        fingerprint_data = await get_fingerprint_stats(db)
        sequence_data = await get_sequence_stats(db)

        # Merge into comprehensive recommendations
        recommendations = {}

        all_protocols = set(timing_data.keys()) | set(protocol_data.keys())

        for protocol in sorted(all_protocols):
            recommendations[protocol] = {
                "timing": timing_data.get(protocol, {}),
                "protocol_patterns": protocol_data.get(protocol, {}),
                "response_timing": fingerprint_data["response_timings"].get(protocol, {}),
                "device_roles": fingerprint_data["role_counts"].get(protocol, {}),
                "sequences": sequence_data.get(protocol, {}),
            }

        # Print summary
        print("\n" + "=" * 70)
        print("LEARNED DEFAULTS BY PROTOCOL")
        print("=" * 70)

        for protocol, data in recommendations.items():
            print(f"\n### {protocol.upper()} ###")

            # Timing
            if data["timing"]:
                print(f"  Timing ({data['timing'].get('sample_count', 0):,} samples):")
                print(f"    poll_interval_ms: {data['timing'].get('poll_interval_ms', 'N/A')}")
                print(f"    jitter_ms: {data['timing'].get('jitter_ms', 'N/A')}")
                print(f"    jitter_type: {data['timing'].get('jitter_type', 'N/A')}")

            # Response timing
            if data["response_timing"]:
                print(f"  Response Timing:")
                print(f"    mean: {data['response_timing'].get('mean_ms', 'N/A')}ms")
                print(f"    range: {data['response_timing'].get('min_ms', 'N/A')} - {data['response_timing'].get('max_ms', 'N/A')}ms")

            # Function codes
            if data["protocol_patterns"].get("function_codes"):
                print(f"  Function Codes:")
                for fc, fc_data in sorted(
                    data["protocol_patterns"]["function_codes"].items(),
                    key=lambda x: x[1]["frequency"],
                    reverse=True
                )[:5]:
                    print(f"    FC {fc} ({fc_data['name']}): {fc_data['frequency']*100:.1f}%")

            # Address patterns
            if data["protocol_patterns"].get("address_patterns"):
                print(f"  Address Patterns:")
                for addr_type, addr_data in data["protocol_patterns"]["address_patterns"].items():
                    print(f"    {addr_type}: {addr_data['min_address']} - {addr_data['max_address']}")

            # Sequences
            if data["sequences"]:
                print(f"  Sequences:")
                for seq_type, seq_data in data["sequences"].items():
                    print(f"    {seq_type}: {seq_data['count']}x (avg {seq_data['avg_steps']} steps, {seq_data['avg_duration_ms']}ms)")

        # Generate Python code for templates
        print("\n" + "=" * 70)
        print("PYTHON CODE FOR TEMPLATE learned_defaults")
        print("=" * 70)

        print("\nLEARNED_DEFAULTS = {")
        for protocol, data in recommendations.items():
            timing = data["timing"]
            response = data["response_timing"]
            fc = data["protocol_patterns"].get("function_codes", {})
            addr = data["protocol_patterns"].get("address_patterns", {})

            print(f'    "{protocol}": {{')
            if timing:
                print(f'        "poll_interval_ms": {timing.get("poll_interval_ms", 100)},')
                print(f'        "jitter_ms": {timing.get("jitter_ms", 0)},')
                print(f'        "jitter_type": "{timing.get("jitter_type", "uniform")}",')
            if response:
                print(f'        "response_time_ms": {{"mean": {response.get("mean_ms", 5)}, "min": {response.get("min_ms", 1)}, "max": {response.get("max_ms", 20)}}},')
            if fc:
                fc_dict = {int(k): round(v["frequency"], 3) for k, v in fc.items()}
                print(f'        "function_codes": {fc_dict},')
            if addr:
                addr_dict = {k: {"start": v["min_address"], "end": v["max_address"]} for k, v in addr.items()}
                print(f'        "address_ranges": {addr_dict},')
            print(f'        "sample_count": {timing.get("sample_count", 0) if timing else 0},')
            print('    },')
        print("}")

        # Output JSON for programmatic use
        print("\n" + "=" * 70)
        print("JSON OUTPUT (for programmatic use)")
        print("=" * 70)
        print(json.dumps(recommendations, indent=2, default=str))

        return recommendations


if __name__ == "__main__":
    asyncio.run(generate_template_enhancements())
