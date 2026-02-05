"""Standardized confidence score calculation for learned patterns.

This module provides a unified approach to calculating confidence scores
across all pattern types (timing, protocol, fingerprint, sequence).
The goal is to ensure confidence scores are comparable and meaningful.
"""

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConfidenceLevel(str, Enum):
    """Qualitative confidence levels."""

    VERY_LOW = "very_low"  # 0.0 - 0.2
    LOW = "low"  # 0.2 - 0.4
    MODERATE = "moderate"  # 0.4 - 0.6
    HIGH = "high"  # 0.6 - 0.8
    VERY_HIGH = "very_high"  # 0.8 - 1.0


@dataclass
class ConfidenceFactors:
    """Factors that contribute to confidence score.

    Each factor is normalized to 0-1 range and weighted.
    """

    sample_count: int = 0
    pattern_consistency: float = 1.0  # 0-1, how consistent the patterns are
    fit_quality: float | None = None  # 0-1, statistical fit quality (for timing)
    coverage: float = 1.0  # 0-1, how much of expected patterns are present
    source_quality: float = 1.0  # 0-1, quality of source data
    diversity: float = 1.0  # 0-1, diversity of observations


# Standard thresholds for sample-based confidence
SAMPLE_THRESHOLDS = {
    "minimum": 10,  # Below this, confidence is very low
    "low": 50,  # At this point, base confidence is ~0.4
    "moderate": 200,  # At this point, base confidence is ~0.6
    "high": 1000,  # At this point, base confidence is ~0.8
    "very_high": 5000,  # At this point, base confidence is ~0.95
}


def calculate_sample_confidence(sample_count: int) -> float:
    """Calculate confidence contribution from sample count.

    Uses a logarithmic scale with diminishing returns to ensure:
    - 10 samples -> ~0.25 confidence
    - 50 samples -> ~0.40 confidence
    - 200 samples -> ~0.60 confidence
    - 1000 samples -> ~0.80 confidence
    - 5000+ samples -> ~0.95 confidence

    Args:
        sample_count: Number of samples observed

    Returns:
        Confidence score between 0 and 1
    """
    if sample_count <= 0:
        return 0.0

    if sample_count < SAMPLE_THRESHOLDS["minimum"]:
        # Linear ramp-up for very small samples
        return (sample_count / SAMPLE_THRESHOLDS["minimum"]) * 0.25

    # Logarithmic growth with diminishing returns
    # log10(sample_count) / log10(max_samples) * scaling
    log_sample = math.log10(sample_count)
    log_high = math.log10(SAMPLE_THRESHOLDS["very_high"])

    # Scale logarithm to 0.25-0.95 range
    base_confidence = 0.25 + (log_sample / log_high) * 0.70

    return min(0.95, base_confidence)


def calculate_consistency_confidence(values: list[float] | None) -> float:
    """Calculate confidence based on value consistency.

    Lower variance relative to mean indicates higher confidence.

    Args:
        values: List of observed values

    Returns:
        Confidence score between 0 and 1
    """
    if not values or len(values) < 2:
        return 0.5  # Neutral if insufficient data

    import statistics

    try:
        mean = statistics.mean(values)
        if mean == 0:
            return 0.5

        stdev = statistics.stdev(values)
        cv = stdev / abs(mean)  # Coefficient of variation

        # Lower CV = higher consistency = higher confidence
        # CV of 0 -> confidence 1.0
        # CV of 0.5 -> confidence ~0.67
        # CV of 1.0 -> confidence ~0.50
        # CV of 2.0+ -> confidence ~0.33
        return max(0.33, 1.0 / (1.0 + cv))
    except (statistics.StatisticsError, ZeroDivisionError):
        return 0.5


def calculate_fit_confidence(fit_score: float | None) -> float:
    """Calculate confidence based on statistical fit quality.

    For timing patterns, this is typically the KS-test p-value.

    Args:
        fit_score: Statistical fit score (p-value or similar)

    Returns:
        Confidence score between 0 and 1
    """
    if fit_score is None:
        return 0.5  # Neutral if no fit score

    # P-value interpretation:
    # > 0.1 -> good fit (high confidence)
    # 0.05 - 0.1 -> acceptable fit
    # 0.01 - 0.05 -> marginal fit
    # < 0.01 -> poor fit (low confidence)

    if fit_score > 0.1:
        return 0.9 + (min(fit_score, 1.0) - 0.1) * 0.1  # 0.90-1.0
    elif fit_score > 0.05:
        return 0.7 + (fit_score - 0.05) * 4.0  # 0.70-0.90
    elif fit_score > 0.01:
        return 0.4 + (fit_score - 0.01) * 7.5  # 0.40-0.70
    else:
        return fit_score * 40  # 0.0-0.40


def calculate_coverage_confidence(
    observed_items: int,
    expected_items: int | None = None,
    unique_categories: int = 0,
) -> float:
    """Calculate confidence based on coverage of expected patterns.

    Args:
        observed_items: Number of unique items observed
        expected_items: Expected number of items (if known)
        unique_categories: Number of unique categories/types observed

    Returns:
        Confidence score between 0 and 1
    """
    if observed_items <= 0:
        return 0.0

    if expected_items and expected_items > 0:
        # If we know expected count, calculate coverage ratio
        coverage = min(1.0, observed_items / expected_items)
        return 0.5 + coverage * 0.5  # 0.5-1.0 range
    else:
        # Use unique categories as proxy for coverage
        # More categories = potentially better coverage
        if unique_categories <= 1:
            return 0.5
        elif unique_categories <= 3:
            return 0.6
        elif unique_categories <= 5:
            return 0.7
        elif unique_categories <= 10:
            return 0.8
        else:
            return 0.9


def calculate_confidence(factors: ConfidenceFactors) -> float:
    """Calculate overall confidence score from multiple factors.

    The final score is a weighted combination of:
    - Sample count (40% weight)
    - Pattern consistency (25% weight)
    - Fit quality (20% weight, if available)
    - Coverage (15% weight)

    Args:
        factors: ConfidenceFactors with contributing scores

    Returns:
        Overall confidence score between 0 and 1
    """
    # Calculate component scores
    sample_conf = calculate_sample_confidence(factors.sample_count)
    consistency_conf = factors.pattern_consistency

    # Weights depend on whether fit quality is available
    if factors.fit_quality is not None:
        fit_conf = calculate_fit_confidence(factors.fit_quality)

        # Weighted combination with fit quality
        weights = {
            "sample": 0.40,
            "consistency": 0.25,
            "fit": 0.20,
            "coverage": 0.15,
        }

        score = (
            sample_conf * weights["sample"]
            + consistency_conf * weights["consistency"]
            + fit_conf * weights["fit"]
            + factors.coverage * weights["coverage"]
        )
    else:
        # Weighted combination without fit quality
        weights = {
            "sample": 0.50,
            "consistency": 0.30,
            "coverage": 0.20,
        }

        score = (
            sample_conf * weights["sample"]
            + consistency_conf * weights["consistency"]
            + factors.coverage * weights["coverage"]
        )

    # Apply source quality multiplier (affects final score)
    score *= factors.source_quality

    # Apply diversity bonus (up to 5% boost)
    diversity_bonus = (factors.diversity - 0.5) * 0.1  # -0.05 to +0.05
    score += diversity_bonus

    return max(0.0, min(1.0, score))


def get_confidence_level(score: float) -> ConfidenceLevel:
    """Convert numeric confidence score to qualitative level.

    Args:
        score: Confidence score between 0 and 1

    Returns:
        ConfidenceLevel enum value
    """
    if score < 0.2:
        return ConfidenceLevel.VERY_LOW
    elif score < 0.4:
        return ConfidenceLevel.LOW
    elif score < 0.6:
        return ConfidenceLevel.MODERATE
    elif score < 0.8:
        return ConfidenceLevel.HIGH
    else:
        return ConfidenceLevel.VERY_HIGH


def calculate_aggregate_confidence(
    confidence_scores: list[float],
    weights: list[float] | None = None,
) -> float:
    """Calculate aggregate confidence from multiple sources.

    Useful for combining confidence from multiple PCAP captures
    in a learning session.

    Args:
        confidence_scores: List of individual confidence scores
        weights: Optional weights for each score (e.g., based on sample size)

    Returns:
        Aggregate confidence score
    """
    if not confidence_scores:
        return 0.0

    if weights is None:
        # Equal weighting
        return sum(confidence_scores) / len(confidence_scores)
    else:
        # Weighted average
        if len(weights) != len(confidence_scores):
            raise ValueError("Weights must match confidence scores length")

        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(s * w for s, w in zip(confidence_scores, weights))
        return weighted_sum / total_weight


# Convenience functions for specific pattern types


def calculate_timing_pattern_confidence(
    sample_count: int,
    fit_score: float | None,
    cv: float | None = None,
) -> float:
    """Calculate confidence for timing patterns.

    Args:
        sample_count: Number of timing samples
        fit_score: Distribution fit score (KS-test p-value)
        cv: Coefficient of variation (optional)

    Returns:
        Confidence score between 0 and 1
    """
    consistency = 1.0
    if cv is not None:
        consistency = max(0.33, 1.0 / (1.0 + cv))

    factors = ConfidenceFactors(
        sample_count=sample_count,
        pattern_consistency=consistency,
        fit_quality=fit_score,
    )
    return calculate_confidence(factors)


def calculate_protocol_pattern_confidence(
    sample_count: int,
    unique_function_codes: int,
    error_rate: float = 0.0,
) -> float:
    """Calculate confidence for protocol patterns.

    Args:
        sample_count: Number of protocol packets analyzed
        unique_function_codes: Number of unique function codes observed
        error_rate: Rate of parsing errors or exceptions

    Returns:
        Confidence score between 0 and 1
    """
    # Coverage based on function code diversity
    coverage = calculate_coverage_confidence(unique_function_codes, unique_categories=unique_function_codes)

    # Error rate affects source quality
    source_quality = 1.0 - min(0.5, error_rate)  # Max 50% penalty

    factors = ConfidenceFactors(
        sample_count=sample_count,
        pattern_consistency=1.0 - error_rate,
        coverage=coverage,
        source_quality=source_quality,
    )
    return calculate_confidence(factors)


def calculate_fingerprint_confidence(
    packet_count: int,
    has_tcp_signature: bool,
    has_protocol_identity: bool,
    has_mac_oui: bool,
    behavior_clarity: float = 1.0,
) -> float:
    """Calculate confidence for device fingerprints.

    Args:
        packet_count: Number of packets from this device
        has_tcp_signature: Whether TCP stack signature was captured
        has_protocol_identity: Whether protocol-level identity was found
        has_mac_oui: Whether MAC OUI vendor was identified
        behavior_clarity: How clear the role (master/slave) is (0-1)

    Returns:
        Confidence score between 0 and 1
    """
    # Coverage based on identity data completeness
    identity_score = 0.0
    if has_tcp_signature:
        identity_score += 0.4
    if has_protocol_identity:
        identity_score += 0.4
    if has_mac_oui:
        identity_score += 0.2

    factors = ConfidenceFactors(
        sample_count=packet_count,
        pattern_consistency=behavior_clarity,
        coverage=identity_score,
    )
    return calculate_confidence(factors)


def calculate_sequence_confidence(
    occurrence_count: int,
    consistency: float,
    timing_variance: float | None = None,
) -> float:
    """Calculate confidence for learned sequences.

    Args:
        occurrence_count: How many times this sequence was observed
        consistency: How consistently the sequence appeared (0-1)
        timing_variance: Variance in inter-step timing (optional)

    Returns:
        Confidence score between 0 and 1
    """
    # Timing variance affects fit quality (lower variance = better fit)
    fit_quality = None
    if timing_variance is not None:
        # Convert variance to a 0-1 fit quality score
        # Lower variance = higher quality
        fit_quality = 1.0 / (1.0 + timing_variance / 100)  # Normalize

    factors = ConfidenceFactors(
        sample_count=occurrence_count,
        pattern_consistency=consistency,
        fit_quality=fit_quality,
    )
    return calculate_confidence(factors)
