"""Review /tmp/bacnet_demo.pcap: decode every BACnet packet with bacpypes
(independent reference), validate correctness, print a Wireshark-style summary.
"""
import sys
from collections import Counter
from scapy.all import rdpcap
from scapy.layers.inet import IP, UDP

from bacpypes.pdu import PDU
from bacpypes.bvll import BVLPDU, bvl_pdu_types
from bacpypes.npdu import NPDU
from bacpypes.apdu import (
    APDU, apdu_types, confirmed_request_types, unconfirmed_request_types,
    complex_ack_types, error_types,
    IAmRequest, WhoIsRequest, ReadPropertyRequest, ReadPropertyACK,
)
from bacpypes.primitivedata import CharacterString, Real, Unsigned, Enumerated
from bacpypes.basetypes import StatusFlags

pkts = rdpcap("/tmp/bacnet_demo.pcap")
print(f"Loaded {len(pkts)} packets from /tmp/bacnet_demo.pcap\n")

def decode(pay):
    pdu = PDU(pay); bvl = BVLPDU(); bvl.decode(pdu)
    bfunc = bvl.bvlciFunction
    xt = bvl_pdu_types[bfunc](); xt.decode(bvl)
    np = NPDU(); np.decode(xt)
    if np.npduNetMessage is not None:
        return bfunc, ("net", np)
    apdu = APDU(); apdu.decode(np)
    concrete = apdu_types[apdu.apduType](); concrete.decode(apdu)
    reg = {0x00: confirmed_request_types, 0x01: unconfirmed_request_types,
           0x03: complex_ack_types, 0x05: error_types}.get(apdu.apduType)
    if reg:
        st = reg.get(concrete.apduService)
        if st:
            o = st(); o.decode(concrete); return bfunc, ("svc", o)
    return bfunc, ("apdu", concrete)

errors = []
kinds = Counter()
bvlc_kinds = Counter()
iams = []
status_flag_ok = 0
status_flag_total = 0
sample_lines = []

for i, p in enumerate(pkts):
    if UDP not in p:
        kinds["non-udp"] += 1
        continue
    pay = bytes(p[UDP].payload)
    src = p[IP].src if IP in p else "?"
    dst = p[IP].dst if IP in p else "?"
    try:
        bfunc, (kind, obj) = decode(pay)
    except Exception as e:
        errors.append((i, f"{type(e).__name__}: {e}", pay.hex()))
        kinds["DECODE-ERROR"] += 1
        continue
    bvlc_kinds[bvl_pdu_types[bfunc].__name__] += 1
    name = type(obj).__name__
    kinds[name] += 1
    label = name

    if isinstance(obj, IAmRequest):
        did = obj.iAmDeviceIdentifier
        iams.append((src, did[1], obj.vendorID, obj.maxAPDULengthAccepted, str(obj.segmentationSupported)))
        label = f"I-Am dev={did[1]} vendor={obj.vendorID} maxAPDU={obj.maxAPDULengthAccepted}"
    elif isinstance(obj, WhoIsRequest):
        label = "Who-Is"
    elif isinstance(obj, ReadPropertyRequest):
        label = f"ReadProperty-Req {obj.objectIdentifier} {obj.propertyIdentifier}"
    elif isinstance(obj, ReadPropertyACK):
        prop = str(obj.propertyIdentifier)
        val = "?"
        try:
            if prop == "statusFlags":
                status_flag_total += 1
                sf = obj.propertyValue.cast_out(StatusFlags)
                val = str(sf); status_flag_ok += 1
            elif prop in ("vendorName", "modelName", "firmwareRevision", "objectName", "description"):
                val = obj.propertyValue.cast_out(CharacterString)
            elif prop == "presentValue":
                try: val = obj.propertyValue.cast_out(Real)
                except Exception: val = obj.propertyValue.cast_out(Enumerated)
            else:
                try: val = obj.propertyValue.cast_out(Unsigned)
                except Exception:
                    try: val = obj.propertyValue.cast_out(Enumerated)
                    except Exception: val = "(value)"
        except Exception as e:
            errors.append((i, f"value cast {prop}: {type(e).__name__}: {e}", pay.hex()))
            val = "CAST-ERROR"
        label = f"ReadProperty-ACK {obj.objectIdentifier} {prop}={val}"

    if len(sample_lines) < 30:
        sample_lines.append(f"  #{i:3} {src:11}->{dst:11} {label}")

print("=== First 30 decoded packets ===")
print("\n".join(sample_lines))

print("\n=== BVLC function distribution ===")
for k, v in bvlc_kinds.items():
    print(f"  {k:30} {v}")

print("\n=== APDU type distribution ===")
for k, v in sorted(kinds.items(), key=lambda x: -x[1]):
    print(f"  {k:30} {v}")

print("\n=== I-Am announcements (device identity) ===")
for src, dev, vid, maxapdu, seg in iams:
    print(f"  {src:11} device={dev:>8} vendorID={vid} maxAPDU={maxapdu} seg={seg}")

print(f"\n=== Status_Flags responses ===  {status_flag_ok}/{status_flag_total} decoded as valid StatusFlags")

print(f"\n=== ERRORS: {len(errors)} ===")
for i, msg, hx in errors[:20]:
    print(f"  pkt #{i}: {msg}")
    print(f"      {hx}")

ok = (len(errors) == 0 and status_flag_ok == status_flag_total and status_flag_total > 0)
print("\nRESULT:", "ALL PACKETS VALID" if ok else "ISSUES FOUND")
sys.exit(0 if ok else 1)
