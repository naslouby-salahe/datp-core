# Raw Data Structure Report

Generated 2026-07-28. All facts verified by direct file inspection followed by independent cross-check agents. No files modified.

---

## 1. Overview

| Dataset | Total Size | CSV Files | RAR Files | PCAP Files |
|---|---|---|---|---|
| CIC_IOT_Dataset2023 | 18.2 GB | 372 | 0 | 0 |
| Edge-IIoTset | 9.0 GB | 26 | 0 | 24 |
| N-BaIoT | 8.1 GB | 90 | 16 | 0 |

All CSVs use comma delimiter, UTF-8 encoding, no BOM. Headers present on every file. No quoting of field values.

---

## 2. CIC_IOT_Dataset2023

### 2.1 Directory Structure

```
CIC_IOT_Dataset2023/CSV/
├── README.pdf
├── CSV/                              # Per-attack files (309 CSVs, 34 subdirectories)
│   ├── Benign_Final/                 (4 files)
│   ├── Backdoor_Malware/             (1 file)
│   ├── BrowserHijacking/             (1 file)
│   ├── CommandInjection/             (1 file)
│   ├── DDoS-ACK_Fragmentation/       (13 files)
│   ├── DDoS-HTTP_Flood/              (1 file)
│   ├── DDoS-ICMP_Flood/              (27 files)
│   ├── DDoS-ICMP_Fragmentation/      (20 files)
│   ├── DDoS-PSHACK_FLOOD/            (16 files)
│   ├── DDoS-RSTFINFLOOD/             (16 files)
│   ├── DDoS-SYN_Flood/               (16 files)
│   ├── DDoS-SlowLoris/               (1 file)
│   ├── DDoS-SynonymousIP_Flood/      (14 files)
│   ├── DDoS-TCP_Flood/               (18 files)
│   ├── DDoS-UDP_Flood/               (21 files)
│   ├── DDoS-UDP_Fragmentation/       (13 files)
│   ├── DNS_Spoofing/                 (1 file)
│   ├── DictionaryBruteForce/         (1 file)
│   ├── DoS-HTTP_Flood/               (2 files)
│   ├── DoS-SYN_Flood/                (8 files)
│   ├── DoS-TCP_Flood/                (11 files)
│   ├── DoS-UDP_Flood/                (17 files)
│   ├── MITM-ArpSpoofing/             (2 files)
│   ├── Mirai-greeth_flood/           (29 files)
│   ├── Mirai-greip_flood/            (22 files)
│   ├── Mirai-udpplain/               (25 files)
│   ├── Recon-HostDiscovery/          (1 file)
│   ├── Recon-OSScan/                 (1 file)
│   ├── Recon-PingSweep/              (1 file)
│   ├── Recon-PortScan/               (1 file)
│   ├── SqlInjection/                 (1 file)
│   ├── Uploading_Attack/             (1 file)
│   ├── VulnerabilityScan/            (1 file)
│   └── XSS/                          (1 file)
└── MERGED_CSV/                       # Merged labeled files (63 CSVs)
    ├── Merged01.csv ... Merged63.csv
```

34 classes total: 33 attack subdirectories + Benign_Final. The MERGED_CSV files contain 34 distinct `Label` values (33 attack classes + `BENIGN`).

### 2.2 Schema: Per-Attack Files (all 309 files — identical)

39 columns. No label column. Attack class encoded in directory name.

**All columns are numeric.** Column names contain spaces and mixed case.

| # | Column | Inferred Type | Category |
|---|---|---|---|
| 0 | `Header_Length` | float64 | Header stat |
| 1 | `Protocol Type` | int64 | IANA protocol number (1=ICMP, 6=TCP, 17=UDP, 47=GRE) |
| 2 | `Time_To_Live` | float64 | IP TTL |
| 3 | `Rate` | float64 | Flow rate |
| 4 | `fin_flag_number` | float64 | TCP FIN flag |
| 5 | `syn_flag_number` | float64 | TCP SYN flag |
| 6 | `rst_flag_number` | float64 | TCP RST flag |
| 7 | `psh_flag_number` | float64 | TCP PSH flag |
| 8 | `ack_flag_number` | float64 | TCP ACK flag |
| 9 | `ece_flag_number` | float64 | TCP ECE flag |
| 10 | `cwr_flag_number` | float64 | TCP CWR flag |
| 11 | `ack_count` | int64 | ACK count |
| 12 | `syn_count` | int64 | SYN count |
| 13 | `fin_count` | int64 | FIN count |
| 14 | `rst_count` | int64 | RST count |
| 15–29 | `HTTP`, `HTTPS`, `DNS`, `Telnet`, `SMTP`, `SSH`, `IRC`, `TCP`, `UDP`, `DHCP`, `ARP`, `ICMP`, `IGMP`, `IPv`, `LLC` | float64 | Protocol indicators |
| 30 | `Tot sum` | int64 | Flow aggregate total |
| 31 | `Min` | int64 | Flow aggregate min |
| 32 | `Max` | int64 | Flow aggregate max |
| 33 | `AVG` | float64 | Flow aggregate average |
| 34 | `Std` | float64 | Flow aggregate stddev |
| 35 | `Tot size` | float64 | Total size |
| 36 | `IAT` | float64 | Inter-arrival time (seconds) |
| 37 | `Number` | int64 | Aggregation window size (10=benign, 100=high-volume DDoS) |
| 38 | `Variance` | float64 | Variance |

**Integer columns (6):** `Protocol Type`, `ack_count`, `syn_count`, `fin_count`, `rst_count`, `Number`.
**Float columns (33):** All remaining.

### 2.3 Schema: Merged Files (all 63 files — identical)

40 columns: the 39 per-attack columns above, plus:

| # | Column | Type | Notes |
|---|---|---|---|
| 39 | `Label` | string | Attack class in UPPERCASE |

Label values (34 distinct, verified): `BACKDOOR_MALWARE`, `BENIGN`, `BROWSERHIJACKING`, `COMMANDINJECTION`, `DDOS-ACK_FRAGMENTATION`, `DDOS-HTTP_FLOOD`, `DDOS-ICMP_FLOOD`, `DDOS-ICMP_FRAGMENTATION`, `DDOS-PSHACK_FLOOD`, `DDOS-RSTFINFLOOD`, `DDOS-SLOWLORIS`, `DDOS-SYNONYMOUSIP_FLOOD`, `DDOS-SYN_FLOOD`, `DDOS-TCP_FLOOD`, `DDOS-UDP_FLOOD`, `DDOS-UDP_FRAGMENTATION`, `DICTIONARYBRUTEFORCE`, `DNS_SPOOFING`, `DOS-HTTP_FLOOD`, `DOS-SYN_FLOOD`, `DOS-TCP_FLOOD`, `DOS-UDP_FLOOD`, `MIRAI-GREETH_FLOOD`, `MIRAI-GREIP_FLOOD`, `MIRAI-UDPPLAIN`, `MITM-ARPSPOOFING`, `RECON-HOSTDISCOVERY`, `RECON-OSSCAN`, `RECON-PINGSWEEP`, `RECON-PORTSCAN`, `SQLINJECTION`, `UPLOADING_ATTACK`, `VULNERABILITYSCAN`, `XSS`.

Each Merged file is multi-class — contains samples from many attack types, not one per file.

### 2.4 Row Counts

| Category | Range | Notes |
|---|---|---|
| Per-attack files | 1,253 – 374,000 | Single-attack-type; varies by class |
| Merged files | 65,724 – 920,544 | Merged52.csv anomalously small (final chunk) |
| Per-attack total | ~46.8M rows | |
| Merged total | ~45.0M rows | |

### 2.5 Anomalies

1. **`inf` in `Rate`:** One occurrence in `DDoS-UDP_Fragmentation/DDoS-UDP_Fragmentation.pcap.csv`, row 982. Division by zero in rate calculation.
2. **Empty cells:** 2 empty cells in same DDoS-UDP_Fragmentation file.
3. **Sparsely populated protocol columns:** `Telnet` (18), `SMTP` (19), `IRC` (21) are 0.0 in most attack types but have non-zero values in some (e.g., VulnerabilityScan has `Telnet` up to 0.5, `SMTP` up to 0.8, `IRC` up to 0.2; DoS-SYN_Flood has non-zero values for all three). These columns are informative for certain attacks — do not drop globally.
4. **`Number` semantics:** 10 for benign flows, 100 for high-volume DDoS — encodes aggregation window size.
5. **No missing headers, no BOM, no encoding issues, no empty files.**

### 2.6 Key Facts for Loader Configuration

- 34 classes. Label format: UPPERCASE with underscores/hyphens.
- Per-attack files: label derived from directory basename (e.g., `DDoS-ICMP_Flood`, `Benign_Final`).
- Merged files: label from column `Label`.
- `Protocol Type` column is IP protocol number, NOT a label.
- No timestamp, IP, port, device, or flow-ID columns exist.
- 6 int + 33 float + 1 string (Label, merged only).

---

## 3. Edge-IIoTset

### 3.1 Directory Structure

```
Edge-IIoTset/
├── Readme.txt
├── Edge_IIoTset__DatasetFL.pdf
└── Edge-IIoTset dataset/
    ├── Normal traffic/            (10 device subdirectories)
    │   ├── Distance/Distance.csv
    │   ├── Flame_Sensor/Flame_Sensor.csv
    │   ├── Heart_Rate/Heart_Rate.csv
    │   ├── IR_Receiver/IR_Receiver.csv
    │   ├── Modbus/Modbus.csv
    │   ├── Soil_Moisture/Soil_Moisture.csv
    │   ├── Sound_Sensor/Sound_Sensor.csv
    │   ├── Temperature_and_Humidity/Temperature_and_Humidity.csv
    │   ├── Water_Level/Water_Level.csv
    │   └── phValue/phValue.csv
    ├── Attack traffic/            (14 CSV files + 14 PCAP files)
    │   ├── Backdoor_attack.csv
    │   ├── DDoS_HTTP_Flood_attack.csv
    │   ├── DDoS_ICMP_Flood_attack.csv
    │   ├── DDoS_TCP_SYN_Flood_attack.csv
    │   ├── DDoS_UDP_Flood_attack.csv
    │   ├── MITM_attack.csv
    │   ├── OS_Fingerprinting_attack.csv
    │   ├── Password_attack.csv
    │   ├── Port_Scanning_attack.csv
    │   ├── Ransomware_attack.csv
    │   ├── SQL_injection_attack.csv
    │   ├── Uploading_attack.csv
    │   ├── Vulnerability_scanner_attack.csv
    │   └── XSS_attack.csv
    └── Selected dataset for ML and DL/
        ├── DNN-EdgeIIoT-dataset.csv
        └── ML-EdgeIIoT-dataset.csv
```

PCAP files exist alongside CSVs. They are raw packet captures — not processed data.

### 3.2 Schema (all 26 CSV files — identical)

63 columns. Two label columns (61, 62). No device identifier column.

**Label columns:**

| # | Column | Type | Values |
|---|---|---|---|
| 61 | `Attack_label` | int64 | 0 = Normal, 1 = Attack |
| 62 | `Attack_type` | string | `Normal` or one of 14 attack type strings |

**14 attack type strings:** `Backdoor`, `DDoS_HTTP`, `DDoS_ICMP`, `DDoS_TCP`, `DDoS_UDP`, `MITM`, `OS_Fingerprinting`, `Password`, `Port_Scanning`, `Ransomware`, `SQL_injection`, `Uploading`, `Vulnerability_scanner`, `XSS`.

**Label encoding difference in DNN/ML datasets:** `OS_Fingerprinting` is renamed to `Fingerprinting` in both `DNN-EdgeIIoT-dataset.csv` and `ML-EdgeIIoT-dataset.csv`. This is the only label mismatch between raw and processed datasets.

**Feature columns (61 columns, 0–60):** Protocol-level packet fields. Categorized by protocol layer:

| Category | Count | Example columns |
|---|---|---|
| Frame | 1 | `frame.time` (mixed quality — see anomalies) |
| Network identity | 2 | `ip.src_host`, `ip.dst_host` (dotted-decimal IP strings, mixed type) |
| ARP | 4 | `arp.dst.proto_ipv4`, `arp.opcode`, `arp.hw.size`, `arp.src.proto_ipv4` |
| ICMP | 4 | `icmp.checksum`, `icmp.seq_le`, `icmp.transmit_timestamp`, `icmp.unused` |
| HTTP | 9 | `http.file_data`, `http.content_length`, `http.request.uri.query`, etc. |
| TCP | 15 | `tcp.ack`, `tcp.checksum`, `tcp.dstport`, `tcp.flags`, `tcp.payload`, `tcp.srcport`, etc. |
| UDP | 3 | `udp.port`, `udp.stream`, `udp.time_delta` |
| DNS | 6 | `dns.qry.name`, `dns.qry.name.len`, `dns.retransmission`, etc. |
| MQTT | 13 | `mqtt.conack.flags`, `mqtt.hdrflags`, `mqtt.topic`, `mqtt.protoname`, etc. |
| Modbus | 3 | `mbtcp.len`, `mbtcp.trans_id`, `mbtcp.unit_id` |

**Column dtype is inconsistent across files.** `frame.time` is `object` (string) in most files but `float64` in ML dataset and MITM_attack.csv. `ip.src_host` is consistently `object` (dotted-decimal IP strings). `ip.dst_host` varies: `object` in most files, `int64` in DDoS_UDP_Flood, `float64` in MITM and ML datasets. `tcp.checksum`, `tcp.flags`, `tcp.options`, `tcp.payload`, `mqtt.hdrflags`, `mqtt.msg`, `mqtt.protoname`, `mqtt.topic` also vary between `object` and numeric. Load with `low_memory=False` or explicit dtype mapping.

### 3.3 Device Identity

No device-ID column. Device identity encoded three ways:

1. **File path:** `Normal traffic/{DeviceName}/{DeviceName}.csv` — 10 device names.
2. **IP subnet:** Each normal device uses distinct 192.168.x.x /24 subnet (observed via `ip.src_host`):
   - 192.168.0.x: Temperature_and_Humidity, Modbus
   - 192.168.1.x: Distance, 192.168.2.x: phValue
   - 192.168.3.x: Heart_Rate, 192.168.4.x: Water_Level
   - 192.168.5.x: IR_Receiver, 192.168.6.x: Sound_Sensor
   - 192.168.7.x: Flame_Sensor, 192.168.8.x: Soil_Moisture
3. **MQTT topic** (column `mqtt.topic`): Contains device name for 9/10 normal devices. Modbus is the exception — it uses DNS, not MQTT.

Attack traffic files have no device identity.

### 3.4 Row Counts

| File Category | Files | Row Range |
|---|---|---|
| Attack traffic | 14 | 1,001 – 3,201,627 |
| Normal traffic (per device) | 10 | 159,502 – 2,295,289 |
| DNN dataset | 1 | 2,219,202 |
| ML dataset | 1 | 157,801 |

Largest: `DDoS_UDP_Flood_attack.csv` (3.2M rows). Smallest: `OS_Fingerprinting_attack.csv` (1,001 rows).

DNN dataset: heavily normal-weighted (~72.8% Normal rows). ML dataset: attack-heavy (~15.4% Normal).

### 3.5 Anomalies

1. **`frame.time` corruption in 3 raw files:**
   - `DDoS_UDP_Flood_attack.csv`: ~95% of rows have IP addresses instead of timestamps. ~5% have proper timestamps. Column alignment is correct — this is a data capture issue.
   - `Modbus.csv`: 100% of rows have IP addresses in `frame.time` (e.g., `192.168.0.128`).
   - `MITM_attack.csv`: 100% of rows have `0.0` in `frame.time`.
2. **`frame.time` in ML dataset:** All values are small numeric (e.g., `6.0`) — preprocessing dropped the timestamp.
3. **Leading/trailing whitespace:** Proper `frame.time` values have format `" YYYY HH:MM:SS.fffffffff "` with leading and trailing spaces.
4. **`OS_Fingerprinting` → `Fingerprinting`:** Renamed in DNN and ML datasets. Only label encoding difference between raw and processed files.
5. **Protocol sparsity:** Protocol-specific columns contain meaningful values only when that protocol is used in the packet. ICMP attacks populate ICMP columns and leave TCP/HTTP/MQTT at 0.0. TCP attacks populate TCP columns and leave ICMP at 0.0. Which columns are constant varies per file.
6. **Column misalignment in MITM_attack.csv:** Row 0 shows DNS service names in port columns (`tcp.srcport = '_ipps._tcp.local'`, `udp.port = '_ipp._tcp.local'`), indicating column-shift issues in this file.
7. **Mixed hex/decimal:** `tcp.flags`, `mqtt.hdrflags`, `tcp.checksum` mix hex (`0x...`) and decimal values.

### 3.6 Key Facts for Loader Configuration

- Device identity only in file path, IP subnet, or MQTT topic — must be parsed from path.
- Attack traffic files: one attack type per file, device unknown.
- DNN and ML datasets are pre-split, multi-class, shuffled. Share the same 63-column schema.
- `frame.time` is unreliable in 4/26 files — do not depend on it as a primary feature.
- All files schema-identical. No missing values or encoding issues found.

---

## 4. N-BaIoT

### 4.1 Directory Structure

```
N-BaIoT/
├── N_BaIoT_dataset_description_v1.txt
├── demonstrate_structure.csv           (1-row documentation example, 115 cols)
└── <device>/                           (9 devices)
    ├── benign_traffic.csv
    ├── gafgyt_attacks/
    │   ├── combo.csv
    │   ├── junk.csv
    │   ├── scan.csv
    │   ├── tcp.csv
    │   └── udp.csv
    ├── gafgyt_attacks.rar              (original archive, 16 total)
    ├── mirai_attacks/
    │   ├── ack.csv
    │   ├── scan.csv
    │   ├── syn.csv
    │   ├── udp.csv
    │   └── udpplain.csv
    └── mirai_attacks.rar               (original archive, 16 total)
```

**9 devices:**

| Device | Benign | Gafgyt | Mirai |
|---|---|---|---|
| Danmini_Doorbell | 49,549 | 5 files | 5 files |
| Ecobee_Thermostat | 13,114 | 5 files | 5 files |
| Ennio_Doorbell | 39,101 | 5 files | — |
| Philips_B120N10_Baby_Monitor | 175,241 | 5 files | 5 files |
| Provision_PT_737E_Security_Camera | 62,155 | 5 files | 5 files |
| Provision_PT_838_Security_Camera | 98,515 | 5 files | 5 files |
| Samsung_SNH_1011_N_Webcam | 52,151 | 5 files | — |
| SimpleHome_XCS7_1002_WHT_Security_Camera | 46,586 | 5 files | 5 files |
| SimpleHome_XCS7_1003_WHT_Security_Camera | 19,529 | 5 files | 5 files |

Samsung and Ennio have gafgyt attacks only (no mirai). All others have both botnet families.

### 4.2 Schema (all 89 data CSVs — identical headers)

115 columns. No label column. No device identifier column. All numeric (float64/int64).

**Benign/malicious separation is by FILE, not by column.** Benign rows in `benign_traffic.csv`. Attack rows in `gafgyt_attacks/*.csv` and `mirai_attacks/*.csv`. No file mixes benign and attack.

**Attack sub-type** (combo, junk, scan, tcp, udp, ack, syn, udpplain) encoded in filename.

**Botnet family** encoded in parent directory (`gafgyt_attacks/` vs `mirai_attacks/`).

### 4.3 Column Categories (115 total)

Statistical features extracted over time windows at 5 decay factors (L5, L3, L1, L0.1, L0.01):

| Prefix | Stats per decay | Total columns | Description |
|---|---|---|---|
| `MI_dir_*` | weight, mean, variance (3) | 15 | Marginal distribution of packet directions |
| `H_*` | weight, mean, variance (3) | 15 | Host entropy |
| `HH_*` | weight, mean, std, magnitude, radius, covariance, pcc (7) | 35 | Host-to-host joint entropy |
| `HH_jit_*` | weight, mean, variance (3) | 15 | Host-to-host jitter |
| `HpHp_*` | weight, mean, std, magnitude, radius, covariance, pcc (7) | 35 | Host-to-host port-based joint entropy |

Total: 15 + 15 + 35 + 15 + 35 = 115. All columns accounted for. No extra or missing columns.

### 4.4 Constant / All-Zero Columns

Varies by attack type, not by device. Verified on Danmini_Doorbell (representative):

| File | Constant cols | All-zero cols | Notes |
|---|---|---|---|
| benign_traffic.csv | 0 | 0 | All columns informative |
| gafgyt/combo.csv | 0 | 0 | |
| gafgyt/junk.csv | 1 | 1 | |
| gafgyt/scan.csv | 0 | 0 | |
| gafgyt/tcp.csv | 3 | 3 | HpHp covariance/pcc |
| gafgyt/udp.csv | 3 | 3 | HpHp_L5_pcc, HpHp_L0.01_covariance, HpHp_L0.01_pcc |
| mirai/ack.csv | 24 | 24 | All HH_*_covariance/pcc + many HpHp_* columns |
| mirai/scan.csv | 20 | 20 | |
| mirai/syn.csv | 26 | 24 | All HH_*_covariance/pcc + many HpHp_* |
| mirai/udp.csv | 35 | 30 | |
| mirai/udpplain.csv | 20 | 20 | |

Constant columns are attack-type-specific. Do not drop columns globally — different attack sub-types have different informative subsets.

### 4.5 Row Counts

| Category | Range |
|---|---|
| Benign per device | 13,114 – 175,241 |
| Gafgyt attack per file | 29,068 – 105,874 |
| Mirai attack per file | 61,852 – 237,665 |

Largest: Danmini mirai/udp.csv (237,665 rows). Smallest: Ecobee benign_traffic.csv (13,114 rows).

### 4.6 Key Facts for Loader Configuration

- Device identity only in path (9 device names). Parse from directory.
- Label construction: `(botnet_family, attack_sub_type)` for attacks, `BENIGN` for benign. Example: `(gafgyt, combo)`, `(mirai, udpplain)`. Both botnet families have `scan` and `udp` — disambiguate via parent directory.
- All files have headers. All columns numeric.
- No IP, timestamp, MAC, or flow-ID columns.
- 16 RAR archives are original compressed files — use extracted CSVs.
- `demonstrate_structure.csv` is documentation only, not data.
- Column dtype varies per file (int64 in benign, float64 in attack for some columns). Cast consistently.
- No missing values found. No encoding issues.

---

## 5. Cross-Dataset Comparison

| Property | CIC_IOT_Dataset2023 | Edge-IIoTset | N-BaIoT |
|---|---|---|---|
| Feature columns | 39 | 61 | 115 |
| Label in data | `Label` (merged only) | `Attack_label` + `Attack_type` | None (file-separated) |
| Label encoding | String (UPPERCASE) | int (0/1) + string | Path-derived |
| Device identity in data | No | Via path/IP/MQTT | No |
| Timestamp | No | `frame.time` (corrupted in 4/26 files) | No |
| IP/port/flow ID | No | `ip.src_host`, `ip.dst_host`, port cols (dotted-decimal strings) | No |
| Schema uniformity | 100% | 100% | 100% |
| Number of classes | 34 | 15 | 1 benign + 10 gafgyt + 10 mirai = 21 |
| Missing values | Rare (<0.01%) | None found | None found |
| Inf values | 1 occurrence | None found | None found |
| Constant columns | 3 (sparse, varies by attack) | Per-protocol sparsity (varies per file) | 0–35 per attack type |

---

## 6. Loader Design Recommendations

1. **One loader per dataset** — schemas differ too much for unification.
2. **Parse device/label from path** for CIC per-attack, all N-BaIoT, and Edge-IIoTset normal traffic.
3. **Cast all numeric columns to float64** on load for consistency across mixed int/float files.
4. **Handle `inf` explicitly** in CIC `Rate` column.
5. **Do not drop constant columns globally** — informativeness depends on attack type.
6. **Edge-IIoTset `frame.time` is unreliable** — do not use as primary feature. Has IP addresses, `0.0`, or numeric junk in 4/26 files.
7. **Edge-IIoTset label rename:** `OS_Fingerprinting` → `Fingerprinting` in DNN/ML datasets. Normalize to canonical name.
8. **Edge-IIoTset IP columns:** `ip.src_host` and `ip.dst_host` store IPs as dotted-decimal strings. `ip.dst_host` has mixed dtype across files.
9. **N-BaIoT RAR files:** 16 archives still present. Do not load them.
10. **Edge-IIoTset PCAP files:** 24 raw captures alongside CSVs. Not for CSV loaders.
