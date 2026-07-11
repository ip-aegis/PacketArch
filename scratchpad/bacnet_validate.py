"""Independent BACnet validation: build packets with PacketArch builders,
decode them with bacpypes (independent reference), report mismatches.

Run inside backend container: python /tmp/bacnet_validate.py
"""
import sys
import struct

from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether

from app.protocol_engines.bacnet import packets as P
from app.protocol_engines.bacnet.types import (
    BACnetObjectType, BACnetPropertyIdentifier, BACnetSegmentation, BVLCFunction,
)
from app.protocol_engines.types import DeviceContext

# bacpypes reference decoder
from bacpypes.pdu import PDU
from bacpypes.bvll import BVLPDU, bvl_pdu_types
from bacpypes.npdu import NPDU, npdu_types
from bacpypes.apdu import (
    APDU, apdu_types, confirmed_request_types, unconfirmed_request_types,
    complex_ack_types, error_types,
    IAmRequest, WhoIsRequest, ReadPropertyRequest, ReadPropertyACK,
)

PASS = "PASS"
FAIL = "FAIL"
results = []

def check(name, cond, detail=""):
    results.append((name, cond))
    flag = PASS if cond else FAIL
    print(f"[{flag}] {name}" + (f"  -- {detail}" if detail and not cond else ""))


def bacnet_payload(full_pkt: bytes) -> bytes:
    """Strip Ether/IP/UDP, return BACnet/IP payload (BVLC+NPDU+APDU)."""
    pkt = Ether(full_pkt)
    udp = pkt[UDP]
    return bytes(udp.payload)


def decode_apdu(payload: bytes):
    """Decode BVLC+NPDU+APDU via bacpypes; return the concrete APDU object."""
    pdu = PDU(payload)
    bvlpdu = BVLPDU()
    bvlpdu.decode(pdu)
    btype = bvl_pdu_types[bvlpdu.bvlciFunction]
    xpdu = btype()
    xpdu.decode(bvlpdu)
    npdu = NPDU()
    npdu.decode(xpdu)
    # network-layer message?
    if npdu.npduNetMessage is not None:
        return ("npdu_net", npdu)
    apdu = APDU()
    apdu.decode(npdu)
    atype = apdu_types[apdu.apduType]
    concrete = atype()
    concrete.decode(apdu)
    # service-specific
    if apdu.apduType == 0x01:  # unconfirmed
        st = unconfirmed_request_types.get(concrete.apduService)
        if st:
            obj = st()
            obj.decode(concrete)
            return ("unconfirmed", obj)
    elif apdu.apduType == 0x00:  # confirmed
        st = confirmed_request_types.get(concrete.apduService)
        if st:
            obj = st()
            obj.decode(concrete)
            return ("confirmed", obj)
    elif apdu.apduType == 0x03:  # complex ack
        st = complex_ack_types.get(concrete.apduService)
        if st:
            obj = st()
            obj.decode(concrete)
            return ("complex_ack", obj)
    elif apdu.apduType == 0x05:  # error
        st = error_types.get(concrete.apduService)
        if st:
            obj = st()
            obj.decode(concrete)
            return ("error", obj)
    return ("apdu", concrete)


def mkdev(did, mac, ip, fp=None):
    return DeviceContext(device_id=did, mac_address=mac, ip_address=ip, port=47808,
                         vendor_fingerprint=fp or {})


src = mkdev("mgr", "00:11:22:33:44:55", "192.168.1.10")
dst = mkdev("ctrl", "66:77:88:99:aa:bb", "192.168.1.20")

print("=" * 70)
print("WHO-IS")
print("=" * 70)
p = P.build_who_is_packet(src)
pay = bacnet_payload(p)
kind, obj = decode_apdu(pay)
check("who-is decodes as WhoIsRequest", isinstance(obj, WhoIsRequest), f"got {type(obj).__name__}")
# UDP ports
pk = Ether(p)
check("who-is dst port 47808", pk[UDP].dport == 47808)
check("who-is src port 47808", pk[UDP].sport == 47808)
check("who-is dst ip broadcast", pk[IP].dst == "255.255.255.255")

print("=" * 70)
print("I-AM")
print("=" * 70)
p = P.build_i_am_packet(dst, device_instance=1001, max_apdu_length=1476,
                        segmentation=BACnetSegmentation.NO_SEGMENTATION, vendor_id=5)
pay = bacnet_payload(p)
kind, obj = decode_apdu(pay)
check("i-am decodes as IAmRequest", isinstance(obj, IAmRequest), f"got {type(obj).__name__}")
if isinstance(obj, IAmRequest):
    devid = obj.iAmDeviceIdentifier  # (objType, instance)
    check("i-am device instance == 1001", devid[1] == 1001, f"got {devid}")
    check("i-am device objtype == device", str(devid[0]) == "device", f"got {devid[0]}")
    check("i-am maxAPDU == 1476", obj.maxAPDULengthAccepted == 1476, f"got {obj.maxAPDULengthAccepted}")
    check("i-am segmentation == noSegmentation", str(obj.segmentationSupported) == "noSegmentation", f"got {obj.segmentationSupported}")
    check("i-am vendorID == 5", obj.vendorID == 5, f"got {obj.vendorID}")

print("=" * 70)
print("READ-PROPERTY REQUEST")
print("=" * 70)
p = P.build_read_property_request_packet(src, dst, invoke_id=7,
        object_type=BACnetObjectType.DEVICE, object_instance=1001,
        property_id=BACnetPropertyIdentifier.VENDOR_NAME)
pay = bacnet_payload(p)
kind, obj = decode_apdu(pay)
check("rp-req decodes as ReadPropertyRequest", isinstance(obj, ReadPropertyRequest), f"got {type(obj).__name__}")
if isinstance(obj, ReadPropertyRequest):
    check("rp-req invokeID == 7", obj.apduInvokeID == 7, f"got {obj.apduInvokeID}")
    oid = obj.objectIdentifier
    check("rp-req object == device:1001", str(oid[0]) == "device" and oid[1] == 1001, f"got {oid}")
    check("rp-req property == vendorName", str(obj.propertyIdentifier) == "vendorName", f"got {obj.propertyIdentifier}")
    # expecting-reply bit in NPDU
    pdu = PDU(pay); bvl = BVLPDU(); bvl.decode(pdu)
    xt = bvl_pdu_types[bvl.bvlciFunction](); xt.decode(bvl)
    np = NPDU(); np.decode(xt)
    check("rp-req NPDU expectingReply set", bool(np.npduControl & 0x04))

def rp_resp_check(prop, ptype, value, expect_fn, label):
    p = P.build_read_property_response_packet(dst, src, invoke_id=7,
            object_type=BACnetObjectType.DEVICE if prop in (
                BACnetPropertyIdentifier.VENDOR_NAME,
                BACnetPropertyIdentifier.MODEL_NAME,
                BACnetPropertyIdentifier.FIRMWARE_REVISION,
            ) else BACnetObjectType.ANALOG_INPUT,
            object_instance=1001 if ptype == "string" else 1,
            property_id=prop, property_value=value, property_type=ptype)
    pay = bacnet_payload(p)
    try:
        kind, obj = decode_apdu(pay)
    except Exception as e:
        check(f"rp-resp {label} decodes", False, f"decode error: {e}")
        return
    ok = isinstance(obj, ReadPropertyACK)
    check(f"rp-resp {label} decodes as ReadPropertyACK", ok, f"got {type(obj).__name__}")
    if not ok:
        return
    try:
        # propertyValue is an Any; cast to the expected primitive
        from bacpypes.constructeddata import Any
        val = obj.propertyValue.cast_out(expect_fn)
        check(f"rp-resp {label} value roundtrip", True, str(val))
        print(f"        decoded value = {val!r}")
    except Exception as e:
        check(f"rp-resp {label} value cast", False, f"cast error: {e}")

print("=" * 70)
print("READ-PROPERTY RESPONSES (value encoding)")
print("=" * 70)
from bacpypes.primitivedata import CharacterString, Real, Unsigned, Enumerated, Boolean
rp_resp_check(BACnetPropertyIdentifier.VENDOR_NAME, "string", "Johnson Controls", CharacterString, "vendorName(str)")
rp_resp_check(BACnetPropertyIdentifier.PRESENT_VALUE, "real", 72.5, Real, "presentValue(real)")
rp_resp_check(BACnetPropertyIdentifier.PROTOCOL_REVISION, "unsigned", 19, Unsigned, "protocolRevision(uint)")
rp_resp_check(BACnetPropertyIdentifier.SYSTEM_STATUS, "enumerated", 0, Enumerated, "systemStatus(enum)")

print("=" * 70)
total = len(results)
passed = sum(1 for _, c in results if c)
print(f"TOTAL: {passed}/{total} passed, {total - passed} FAILED")
sys.exit(0 if passed == total else 1)
