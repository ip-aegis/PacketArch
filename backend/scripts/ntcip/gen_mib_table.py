# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Regenerate app/protocol_engines/snmp/ntcip/_mib_table.py from NTCIP MIB files.

The MIB files are NOT committed (AASHTO/ITE/NEMA copyright). Fetch them first:

  NTCIP 1201/1203/1204/1209: https://github.com/ite-org (NTCIP-1201, NTCIP-1203, ...)
  NTCIP 1202 v01 (ASC-MIB1):  https://github.com/igorpopovicz/SnmpGetAPI/tree/master/mibs

Usage:
  python -I scripts/ntcip/gen_mib_table.py <mib_dir> > app/protocol_engines/snmp/ntcip/_mib_table.py

Only the objects in WANT are emitted: name, full OID, SNMP value type, access
and whether the object is a table column (instance = index) or a scalar
(instance = .0). That is a fact table, not MIB text.
"""
import re
import sys
from pathlib import Path

# The 1203 MIB in ite-org/NTCIP-1203 declares `dms MODULE-IDENTITY ::= { devices 6 }`
# while its own DESCRIPTION (and every deployed sign, e.g. MnDOT IRIS MIB1203)
# uses 1.3.6.1.4.1.1206.4.2.3. ESS/TSS modules carry no parent clause at all.
ROOTS = {
    "enterprises": "1.3.6.1.4.1",
    "nema": "1.3.6.1.4.1.1206",
    "transportation": "1.3.6.1.4.1.1206.4",
    "devices": "1.3.6.1.4.1.1206.4.2",
    "dms": "1.3.6.1.4.1.1206.4.2.3",
    "tss": "1.3.6.1.4.1.1206.4.2.4",
    "ess": "1.3.6.1.4.1.1206.4.2.5",
}

FILES = ["1202ASC.mib", "NTCIP1201-Glo.mib", "ntcip1201-Global.mib",
         "NTCIP1203-Dms.mib", "NTCIP1204-Ess.mib"]

WANT = {
    "1201": """globalTime globalDaylightSaving globalLocalTimeDifferential controllerLocalTime
        globalMaxModules moduleMake moduleModel moduleVersion moduleType
        controllerBaseStandards dbCreateTransaction""",
    "1202": """maxPhases maxPhaseGroups phaseStatusGroupNumber phaseStatusGroupReds
        phaseStatusGroupYellows phaseStatusGroupGreens phaseStatusGroupDontWalks
        phaseStatusGroupPedClears phaseStatusGroupWalks phaseStatusGroupVehCalls
        phaseStatusGroupPedCalls phaseStatusGroupPhaseOns phaseStatusGroupPhaseNexts
        maxVehicleDetectors maxVehicleDetectorStatusGroups vehicleDetectorStatusGroupActive
        vehicleDetectorStatusGroupAlarms volumeOccupancySequence volumeOccupancyPeriod
        activeVolumeOccupancyDetectors detectorVolume detectorOccupancy
        unitControlStatus unitFlashStatus unitAlarmStatus1 unitAlarmStatus2 shortAlarmStatus
        coordPatternStatus localFreeStatus coordCycleStatus coordSyncStatus
        systemPatternControl maxPatterns patternCycleTime patternOffsetTime maxRings""",
    "1203": """dmsSignType vmsSignHeightPixels vmsSignWidthPixels dmsNumChangeableMsg
        dmsMaxChangeableMsg dmsMessageMultiString dmsMessageOwner dmsMessageCRC
        dmsMessageBeacon dmsMessagePixelService dmsMessageRunTimePriority dmsMessageStatus
        dmsMsgTableSource dmsActivateMessage dmsMessageTimeRemaining dmsControlMode
        dmsIllumControl dmsIllumPhotocellLevelStatus dmsIllumBrightLevelStatus
        shortErrorStatus dmsStatDoorOpen lineVolts tempMinAmbient tempMaxAmbient
        tempMinSignHousing tempMaxSignHousing""",
    "1204": """essNtcipCategory essTypeofStation essAirTemperature essNumTemperatureSensors
        essDewpointTemp essMaxTemp essMinTemp essRelativeHumidity essAvgWindDirection
        essAvgWindSpeed essSpotWindSpeed essMaxWindGustSpeed essPrecipRate
        essPrecipSituation essAtmosphericPressure essVisibility essVisibilitySituation
        numEssPavementSensors essSurfaceStatus essSurfaceTemperature
        essPavementTemperature essSurfaceFreezePoint essSurfaceBlackIceSignal""",
}

# SMI syntax -> engine VarBind.value_type
OCTET_TC = {"MessageIDCode", "MessageActivationCode"}
STRING_TC = {"MultiString", "NtcipOwnerString", "DisplayString", "OwnerString"}


def value_type(syntax: str) -> str:
    head = syntax.split()[0].split("(")[0]
    if head in ("Counter", "Counter32"):
        return "counter"
    if head in ("Gauge", "Gauge32"):
        return "gauge"
    if head in OCTET_TC:
        return "octets"
    if head in STRING_TC or syntax.startswith("OCTET STRING"):
        return "string"
    return "integer"


def parse(mib_dir: Path) -> dict:
    defs = {}
    for name in FILES:
        txt = re.sub(r"--[^\n]*", "", (mib_dir / name).read_text(encoding="latin-1"))
        for m in re.finditer(
            r"\b([a-z][A-Za-z0-9-]*)\s+(OBJECT-TYPE|OBJECT IDENTIFIER|OBJECT-IDENTITY|MODULE-IDENTITY)"
            r"(.*?)::=\s*\{\s*([A-Za-z0-9-]+)\s+(\d+)\s*\}", txt, re.S):
            obj, kind, body, parent, num = m.groups()
            if "::=" in body or obj in ROOTS:
                continue
            syn = re.search(r"SYNTAX\s+(.+?)\n\s*(?:UNITS|MAX-ACCESS|ACCESS)", body, re.S)
            acc = re.search(r"(?:MAX-ACCESS|ACCESS)\s+([a-z-]+)", body)
            defs.setdefault(obj, dict(
                parent=parent, num=int(num),
                syntax=" ".join(syn.group(1).split()) if syn else "",
                access=acc.group(1) if acc else "",
            ))
    return defs


def main() -> None:
    defs = parse(Path(sys.argv[1]))

    def oid(n):
        if n in ROOTS:
            return ROOTS[n]
        return f"{oid(defs[n]['parent'])}.{defs[n]['num']}"

    print("# PacketArch — OT Traffic Simulation Platform")
    print("# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>")
    print("# Licensed under GPL-3.0. See LICENSE at the repo root.")
    print('"""NTCIP object table generated by scripts/ntcip/gen_mib_table.py. Do not edit."""')
    print("# name: (oid, value_type, access, columnar)")
    print("MIB_OBJECTS: dict[str, tuple[str, str, str, bool]] = {")
    for std, names in WANT.items():
        print(f"    # NTCIP {std}")
        for n in names.split():
            d = defs[n]
            parent = defs.get(d["parent"], {})
            columnar = parent.get("syntax", "").endswith("Entry")
            print(f'    "{n}": ("{oid(n)}", "{value_type(d["syntax"])}", "{d["access"]}", {columnar}),')
    print("}")


if __name__ == "__main__":
    main()
