"""BACnet edge-case validation against bacpypes reference decoder."""
import sys
from scapy.layers.inet import UDP
from scapy.layers.l2 import Ether

from app.protocol_engines.bacnet import packets as P
from app.protocol_engines.bacnet.types import (
    BACnetObjectType, BACnetPropertyIdentifier, BACnetSegmentation,
    BACnetErrorClass, BACnetErrorCode,
)
from app.protocol_engines.types import DeviceContext

from bacpypes.pdu import PDU
from bacpypes.bvll import BVLPDU, bvl_pdu_types
from bacpypes.npdu import NPDU
from bacpypes.apdu import (
    APDU, apdu_types, confirmed_request_types, unconfirmed_request_types,
    complex_ack_types, error_types,
    ReadPropertyACK, WritePropertyRequest, WhoIsRequest, Error,
)
from bacpypes.primitivedata import CharacterString, Real, Unsigned, Enumerated, Boolean, BitString
from bacpypes.basetypes import StatusFlags

results = []
def check(name, cond, detail=""):
    results.append(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail and not cond else ""))

def payload(p):
    return bytes(Ether(p)[UDP].payload)

def decode(pay):
    pdu = PDU(pay); bvl = BVLPDU(); bvl.decode(pdu)
    xt = bvl_pdu_types[bvl.bvlciFunction](); xt.decode(bvl)
    np = NPDU(); np.decode(xt)
    if np.npduNetMessage is not None:
        return ("net", np)
    apdu = APDU(); apdu.decode(np)
    concrete = apdu_types[apdu.apduType](); concrete.decode(apdu)
    reg = {0x00: confirmed_request_types, 0x01: unconfirmed_request_types,
           0x03: complex_ack_types, 0x05: error_types}.get(apdu.apduType)
    if reg:
        st = reg.get(concrete.apduService)
        if st:
            o = st(); o.decode(concrete); return ("svc", o)
    return ("apdu", concrete)

def dev(did, mac, ip, fp=None):
    return DeviceContext(device_id=did, mac_address=mac, ip_address=ip, port=47808,
                         vendor_fingerprint=fp or {})

src = dev("mgr", "00:11:22:33:44:55", "192.168.1.10")
dst = dev("ctrl", "66:77:88:99:aa:bb", "192.168.1.20")

print("== STATUS_FLAGS bitstring ==")
p = P.build_read_property_response_packet(dst, src, invoke_id=1,
        object_type=BACnetObjectType.ANALOG_INPUT, object_instance=1,
        property_id=BACnetPropertyIdentifier.STATUS_FLAGS,
        property_value=0, property_type="bitstring")
try:
    kind, o = decode(payload(p))
    ok = isinstance(o, ReadPropertyACK)
    check("status_flags decodes as ReadPropertyACK", ok, f"got {type(o).__name__}")
    if ok:
        sf = o.propertyValue.cast_out(StatusFlags)
        check("status_flags casts to StatusFlags", True, str(sf))
        print("        StatusFlags =", sf)
except Exception as e:
    check("status_flags decodes", False, f"{type(e).__name__}: {e}")

print("== boolean value (out_of_service) ==")
p = P.build_read_property_response_packet(dst, src, invoke_id=1,
        object_type=BACnetObjectType.ANALOG_INPUT, object_instance=1,
        property_id=BACnetPropertyIdentifier.OUT_OF_SERVICE,
        property_value=False, property_type="boolean")
try:
    kind, o = decode(payload(p))
    val = o.propertyValue.cast_out(Boolean)
    check("boolean roundtrip", val == 0, f"got {val}")
except Exception as e:
    check("boolean roundtrip", False, f"{type(e).__name__}: {e}")

print("== object_identifier value ==")
p = P.build_read_property_response_packet(dst, src, invoke_id=1,
        object_type=BACnetObjectType.DEVICE, object_instance=1001,
        property_id=BACnetPropertyIdentifier.OBJECT_IDENTIFIER,
        property_value=(8, 1001), property_type="object_identifier")
try:
    from bacpypes.primitivedata import ObjectIdentifier
    kind, o = decode(payload(p))
    val = o.propertyValue.cast_out(ObjectIdentifier)
    check("object_identifier roundtrip", val[1] == 1001, f"got {val}")
except Exception as e:
    check("object_identifier roundtrip", False, f"{type(e).__name__}: {e}")

print("== long character string (200 bytes, triggers extended length) ==")
longname = "X" * 200
p = P.build_read_property_response_packet(dst, src, invoke_id=1,
        object_type=BACnetObjectType.DEVICE, object_instance=1001,
        property_id=BACnetPropertyIdentifier.DESCRIPTION,
        property_value=longname, property_type="string")
try:
    kind, o = decode(payload(p))
    val = o.propertyValue.cast_out(CharacterString)
    check("long string roundtrip", val == longname, f"len got {len(val)} want 200")
except Exception as e:
    check("long string roundtrip", False, f"{type(e).__name__}: {e}")

print("== WriteProperty request ==")
apdu = P.build_write_property_request_apdu(invoke_id=9,
        object_type=BACnetObjectType.ANALOG_VALUE, object_instance=1,
        property_id=BACnetPropertyIdentifier.PRESENT_VALUE,
        property_value=72.0, property_type="real", priority=8)
# wrap in npdu+bvlc manually using builder
from app.protocol_engines.bacnet.packets import build_bacnet_packet
from app.protocol_engines.bacnet.types import BVLCFunction
p = build_bacnet_packet(src.mac_address, dst.mac_address, src.ip_address, dst.ip_address,
        47808, 47808, BVLCFunction.ORIGINAL_UNICAST_NPDU, apdu, expecting_reply=True)
try:
    kind, o = decode(payload(p))
    ok = isinstance(o, WritePropertyRequest)
    check("writeproperty decodes", ok, f"got {type(o).__name__}")
    if ok:
        check("writeproperty value", abs(o.propertyValue.cast_out(Real) - 72.0) < 0.01)
        check("writeproperty priority==8", o.priority == 8, f"got {o.priority}")
except Exception as e:
    check("writeproperty decodes", False, f"{type(e).__name__}: {e}")

print("== Error APDU ==")
from app.protocol_engines.bacnet.types import BACnetConfirmedService
apdu = P.build_error_apdu(invoke_id=3, service=BACnetConfirmedService.READ_PROPERTY,
        error_class=BACnetErrorClass.PROPERTY, error_code=BACnetErrorCode.UNKNOWN_PROPERTY)
p = build_bacnet_packet(src.mac_address, dst.mac_address, src.ip_address, dst.ip_address,
        47808, 47808, BVLCFunction.ORIGINAL_UNICAST_NPDU, apdu)
try:
    kind, o = decode(payload(p))
    check("error decodes as Error", isinstance(o, Error), f"got {type(o).__name__}")
    if isinstance(o, Error):
        ec = o.errorClass; code = o.errorCode
        check("error class==property", str(ec) == "property", f"got {ec}")
        check("error code==unknownProperty", str(code) == "unknownProperty", f"got {code}")
except Exception as e:
    check("error decodes", False, f"{type(e).__name__}: {e}")

print("== Who-Is with limits ==")
p = P.build_who_is_packet(src, low_limit=10, high_limit=20)
try:
    kind, o = decode(payload(p))
    ok = isinstance(o, WhoIsRequest)
    check("who-is(limits) decodes", ok, f"got {type(o).__name__}")
    if ok:
        check("who-is low==10", o.deviceInstanceRangeLowLimit == 10, f"got {o.deviceInstanceRangeLowLimit}")
        check("who-is high==20", o.deviceInstanceRangeHighLimit == 20, f"got {o.deviceInstanceRangeHighLimit}")
except Exception as e:
    check("who-is(limits) decodes", False, f"{type(e).__name__}: {e}")

print("== Routed NPDU (DNET+SNET) ==")
from app.protocol_engines.bacnet.packets import build_npdu, build_who_is_apdu, build_bvlc_header
napdu = build_who_is_apdu()
npdu = build_npdu(expecting_reply=False, destination_net=2000, destination_addr=None,
                  source_net=1, source_addr=b"\x0a", hop_count=255)
bvlc = build_bvlc_header(BVLCFunction.ORIGINAL_BROADCAST_NPDU, len(npdu)+len(napdu))
from scapy.layers.inet import IP
from scapy.packet import Raw
full = bytes(Ether(src="00:11:22:33:44:55", dst="ff:ff:ff:ff:ff:ff")/IP(src="1.1.1.1",dst="255.255.255.255")/UDP(sport=47808,dport=47808)/Raw(bvlc+npdu+napdu))
try:
    pay = bytes(Ether(full)[UDP].payload)
    pdu = PDU(pay); bvl = BVLPDU(); bvl.decode(pdu)
    xt = bvl_pdu_types[bvl.bvlciFunction](); xt.decode(bvl)
    np = NPDU(); np.decode(xt)
    check("routed NPDU dnet==2000", np.npduDADR is not None and np.npduDADR.addrNet == 2000, f"got {getattr(np.npduDADR,'addrNet',None)}")
    check("routed NPDU snet==1", np.npduSADR is not None and np.npduSADR.addrNet == 1, f"got {getattr(np.npduSADR,'addrNet',None)}")
    apdu = APDU(); apdu.decode(np)
    concrete = apdu_types[apdu.apduType](); concrete.decode(apdu)
    wi = unconfirmed_request_types[concrete.apduService](); wi.decode(concrete)
    check("routed NPDU carries Who-Is", isinstance(wi, WhoIsRequest))
except Exception as e:
    check("routed NPDU decodes", False, f"{type(e).__name__}: {e}")

print(f"\nTOTAL: {sum(results)}/{len(results)} passed, {len(results)-sum(results)} FAILED")
sys.exit(0 if all(results) else 1)
