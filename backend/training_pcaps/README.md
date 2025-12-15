# Training PCAPs for PacketArch

This directory contains publicly available PCAP files for industrial/OT protocols, used to train PacketArch's PCAP learning pipeline.

## Directory Structure

```
training_pcaps/
├── modbus/      # Modbus TCP protocol captures
├── ethernetip/  # EtherNet/IP (CIP) protocol captures
├── profinet/    # PROFINET protocol captures
├── dnp3/        # DNP3 protocol captures
├── s7comm/      # Siemens S7comm protocol captures
└── mixed/       # Multi-protocol captures from real ICS environments
```

## Sources

### ITI/ICS-Security-Tools
- **URL:** https://github.com/ITI/ICS-Security-Tools
- **License:** Various (mostly open source)
- **Protocols:** Modbus, PROFINET, DNP3, EtherNet/IP, S7comm
- **Contents:**
  - Bro-IDS test captures for parser testing
  - Covert Modbus communications (CSET 2016)
  - Electra dataset (electric traction substation)
  - Various industrial protocol samples

### 4SICS ICS Lab (Netresec/CS3Sthlm)
- **URL:** https://www.netresec.com/?page=PCAP4SICS
- **License:** Public domain (conference capture, attribution requested)
- **Size:** ~360 MB
- **Files:**
  - `4SICS-GeekLounge-151020.pcap` (25 MB)
  - `4SICS-GeekLounge-151021.pcap` (134 MB)
  - `4SICS-GeekLounge-151022.pcap` (200 MB)
- **Notes:** Real traffic from ICS village at 4SICS 2015 conference. Contains Modbus TCP, S7comm, and various industrial protocols.

### Additional Sources (Not Downloaded)

#### Coimbra ICS_PCAPS (Optional)
- **URL:** https://github.com/tjcruz-dei/ICS_PCAPS/releases
- **License:** CC BY 3.0
- **Size:** ~670 MB (compressed)
- **Notes:** Extensive Modbus TCP dataset for ML research. Download manually if more Modbus data is needed:
  ```bash
  curl -L -o captures1_v2.zip "https://github.com/tjcruz-dei/ICS_PCAPS/releases/download/MODBUSTCP%231/captures1_v2.zip"
  ```

#### CIC Modbus Dataset 2023
- **URL:** https://www.unb.ca/cic/datasets/modbus-2023.html
- **License:** Research/Academic
- **Notes:** Requires registration. Contains attack and benign Modbus traffic.

## Protocol Coverage

| Protocol | Directory | File Count | Notes |
|----------|-----------|------------|-------|
| Modbus TCP | `modbus/` | 11+ | From ITI repo + Bro-IDS |
| EtherNet/IP | `ethernetip/` | 8+ | CIP protocol samples |
| PROFINET | `profinet/` | 5+ | Layer 2 protocol captures |
| DNP3 | `dnp3/` | 200+ | Extensive test dataset |
| S7comm | `s7comm/` | 37+ | Siemens PLC protocol |
| Mixed | `mixed/` | 3 | 4SICS multi-protocol |

## Usage with PacketArch

These PCAPs can be uploaded to PacketArch's Learning page to:
1. Extract device fingerprints and communication patterns
2. Learn realistic traffic timing and behavior
3. Generate scenario templates from real-world captures

## Attribution

If using these datasets for research or redistribution:
- 4SICS data: Credit CS3Sthlm (https://cs3sthlm.se)
- Coimbra data: Cite DOI 10.1007/978-3-030-05849-4_19
- ITI data: See individual dataset licenses in repository

## Last Updated

December 2025
