# Raw Data Structure Report

Generated 2026-07-28. All facts verified by direct file inspection. No files modified.

---

## 1. Overview

| Dataset | Total Size | CSV Files | RAR Files | PCAP Files |
|---|---|---|---|---|
| CIC_IOT_Dataset2023 | 18.2 GB | 372 | 0 | 0 |
| Edge-IIoTset | 9.0 GB | 26 | 0 | 24 |
| N-BaIoT | 8.1 GB | 90 | 16 | 0 |

All CSVs use comma delimiter, UTF-8 encoding, no BOM. Headers present on every file. No quoting of field values detected.

---

## 2. CIC_IOT_Dataset2023

### 2.1 Directory Structure

```
CIC_IOT_Dataset2023/CSV/
├── README.pdf
├── CSV/                              # Per-attack files (309 CSVs)
│   ├── README_CSV.pdf
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

34 classes total: 32 attack types + BENIGN + Benign_Final.

### 2.2 Schema: Per-Attack Files (all 309 files — identical)

39 columns. No label column. Attack class encoded in directory name.

**All columns are numeric.**

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
| 15 | `HTTP` | float64 | HTTP indicator |
| 16 | `HTTPS` | float64 | HTTPS indicator |
| 17 | `DNS` | float64 | DNS indicator |
| 18 | `Telnet` | float64 | Telnet indicator (always 0) |
| 19 | `SMTP` | float64 | SMTP indicator (always 0) |
| 20 | `SSH` | float64 | SSH indicator |
| 21 | `IRC` | float64 | IRC indicator (always 0) |
| 22 | `TCP` | float64 | TCP indicator |
| 23 | `UDP` | float64 | UDP indicator |
| 24 | `DHCP` | float64 | DHCP indicator |
| 25 | `ARP` | float64 | ARP indicator |
| 26 | `ICMP` | float64 | ICMP indicator |
| 27 | `IGMP` | float64 | IGMP indicator |
| 28 | `IPv` | float64 | IP version indicator |
| 29 | `LLC` | float64 | LLC indicator |
| 30 | `Tot sum` | int64 | Total sum |
| 31 | `Min` | int64 | Minimum |
| 32 | `Max` | int64 | Maximum |
| 33 | `AVG` | float64 | Average |
| 34 | `Std` | float64 | Standard deviation |
| 35 | `Tot size` | float64 | Total size |
| 36 | `IAT` | float64 | Inter-arrival time (seconds) |
| 37 | `Number` | int64 | Aggregation window size |
| 38 | `Variance` | float64 | Variance |

**Integer columns (6):** `Protocol Type`, `ack_count`, `syn_count`, `fin_count`, `rst_count`, `Number`.
**Float columns (33):** All others.

### 2.3 Schema: Merged Files (all 63 files — identical)

40 columns: the 39 per-attack columns above, plus:

| # | Column | Type | Notes |
|---|---|---|---|
| 39 | `Label` | string (object) | Attack class in UPPERCASE |

Label values (33 distinct, verified across Merged01.csv): `BACKDOOR_MALWARE`, `BENIGN`, `BROWSERHIJACKING`, `COMMANDINJECTION`, `DDOS-ACK_FRAGMENTATION`, `DDOS-HTTP_FLOOD`, `DDOS-ICMP_FLOOD`, `DDOS-ICMP_FRAGMENTATION`, `DDOS-PSHACK_FLOOD`, `DDOS-RSTFINFLOOD`, `DDOS-SLOWLORIS`, `DDOS-SYNONYMOUSIP_FLOOD`, `DDOS-SYN_FLOOD`, `DDOS-TCP_FLOOD`, `DDOS-UDP_FLOOD`, `DDOS-UDP_FRAGMENTATION`, `DICTIONARYBRUTEFORCE`, `DNS_SPOOFING`, `DOS-HTTP_FLOOD`, `DOS-SYN_FLOOD`, `DOS-TCP_FLOOD`, `DOS-UDP_FLOOD`, `MIRAI-GREETH_FLOOD`, `MIRAI-GREIP_FLOOD`, `MIRAI-UDPPLAIN`, `MITM-ARPSPOOFING`, `RECON-HOSTDISCOVERY`, `RECON-OSSCAN`, `RECON-PINGSWEEP`, `RECON-PORTSCAN`, `SQLINJECTION`, `VULNERABILITYSCAN`, `XSS`.

Each Merged file is multi-class — contains samples from many attack types, not one per file.

### 2.4 Row Counts

| Category | Range | Notes |
|---|---|---|
| Per-attack files | 1,253 – 374,000 | Single-attack-type files vary by attack class |
| Merged files | 65,724 – 920,544 | Merged52.csv is anomalously small (final chunk) |
| Total per-attack | 46.8M rows | |
| Total merged | 45.0M rows | |

### 2.5 Anomalies

1. **`inf` value in `Rate`:** One occurrence in `DDoS-UDP_Fragmentation/DDoS-UDP_Fragmentation.pcap.csv`, row 982. Division-by-zero in rate calculation.
2. **Empty cells:** 2 empty cells in same DDoS-UDP_Fragmentation file (out of 78K sampled).
3. **Perpetually constant columns:** `Telnet` (18), `SMTP` (19), `IRC` (21) are always 0.0 in all inspected files. These are protocol indicators with no traffic in the dataset.
4. **`Number` column semantics:** 10 for benign flows, 100 for high-volume DDoS flows — encodes aggregation window size.
5. **No missing headers, no BOM, no encoding issues.**
6. **No empty files** — all 372 files have at least 1 data row.

### 2.6 Key Facts for Loader Configuration

- 34 classes. Label format: UPPERCASE with underscores/hyphens.
- Per-attack files: label = directory basename (e.g., `DDoS-ICMP_Flood`, `Benign_Final`). Need mapping to canonical enum.
- Merged files: label = column `Label`.
- `Protocol Type` column is **not** a label — it is IP protocol number.
- No timestamp, no IP, no port, no device, no flow-ID columns.
- Column names contain spaces and mixed case. Keep as-is or normalize consistently.
- 6 int columns, 33 float columns, 1 string (Label in merged only).

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

PCAP files exist alongside CSVs in `Attack traffic/` and `Normal traffic/*/` — they are the raw packet captures, not processed data. Ignore for CSV loaders.

### 3.2 Schema (all 26 CSV files — identical)

63 columns. Two label columns, no device identifier.

**Label columns:**

| # | Column | Type | Values |
|---|---|---|---|
| 61 | `Attack_label` | int64 | 0 = Normal, 1 = Attack |
| 62 | `Attack_type` | string | `Normal` or one of 14 attack type strings |

**14 Attack_type values:** `Backdoor`, `DDoS_HTTP`, `DDoS_ICMP`, `DDoS_TCP`, `DDoS_UDP`, `MITM`, `OS_Fingerprinting`, `Password`, `Port_Scanning`, `Ransomware`, `SQL_injection`, `Uploading`, `Vulnerability_scanner`, `XSS`.

**Feature columns (61):** Mix of numeric types. Key categories:

| Category | Columns | Examples |
|---|---|---|
| Network identity (mixed-type string/numeric) | `frame.time`, `ip.src_host`, `ip.dst_host` | IPs stored as hex strings or integers depending on file |
| ARP | `arp.dst.proto_ipv4`, `arp.opcode`, `arp.hw.size`, `arp.src.proto_ipv4` | |
| ICMP | `icmp.checksum`, `icmp.seq_le`, `icmp.transmit_timestamp`, `icmp.unused` | |
| HTTP | `http.file_data`, `http.content_length`, `http.request.uri.query`, `http.request.method`, `http.referer`, `http.request.full_uri`, `http.request.version`, `http.response`, `http.tls_port` | |
| TCP | `tcp.ack`, `tcp.ack_raw`, `tcp.checksum`, `tcp.connection.fin`, `tcp.connection.rst`, `tcp.connection.syn`, `tcp.connection.synack`, `tcp.dstport`, `tcp.flags`, `tcp.flags.ack`, `tcp.len`, `tcp.options`, `tcp.payload`, `tcp.seq`, `tcp.srcport` | |
| UDP | `udp.port`, `udp.stream`, `udp.time_delta` | |
| DNS | `dns.qry.name`, `dns.qry.name.len`, `dns.qry.qu`, `dns.qry.type`, `dns.retransmission`, `dns.retransmit_request`, `dns.retransmit_request_in` | |
| MQTT | `mqtt.conack.flags`, `mqtt.conflag.cleansess`, `mqtt.conflags`, `mqtt.hdrflags`, `mqtt.len`, `mqtt.msg_decoded_as`, `mqtt.msg`, `mqtt.msgtype`, `mqtt.proto_len`, `mqtt.protoname`, `mqtt.topic`, `mqtt.topic_len`, `mqtt.ver` | |
| Modbus | `mbtcp.len`, `mbtcp.trans_id`, `mbtcp.unit_id` | |

**Column dtype is inconsistent across files.** `frame.time` is `object` (string) in some files, `float64` in others. `ip.src_host` and `ip.dst_host` store IP addresses as hex strings (e.g., `0x0a000002`) or as `float64` values depending on the file. `tcp.checksum`, `tcp.flags`, `tcp.options`, `tcp.payload`, `mqtt.hdrflags`, `mqtt.msg`, `mqtt.protoname`, `mqtt.topic` also vary between `object` and numeric types. A typed loader must handle these with `low_memory=False` or explicit dtype mapping.

### 3.3 Row Counts

| File Category | Files | Row Range |
|---|---|---|
| Attack traffic | 14 | 1,002 – 3,201,627 |
| Normal traffic (per device) | 10 | 165,320 – 2,295,289 |
| DNN dataset | 1 | 2,219,202 |
| ML dataset | 1 | 157,801 |

Largest file: `DDoS_UDP_Flood_attack.csv` (3.2M rows). Smallest: `OS_Fingerprinting_attack.csv` (1,002 rows).

### 3.4 Key Facts for Loader Configuration

- Device identity is only in the file path (e.g., `Normal traffic/Flame_Sensor/`). No column carries device ID.
- Attack traffic files have no device identity at all — one file = one attack type, collector device unknown.
- DNN and ML datasets are pre-split, multi-class, shuffled variants. They share the same 63-column schema.
- `ip.src_host` and `ip.dst_host` are stored as hex strings, not dotted-decimal — need decoding if used as flow identifiers.
- Protocol-specific columns are sparse: ICMP columns are NaN/0 in TCP attacks, HTTP columns are NaN/0 in ICMP floods.
- All files schema-identical. No parsing anomalies found in sampled data.

---

## 4. N-BaIoT

### 4.1 Directory Structure

```
N-BaIoT/
├── N_BaIoT_dataset_description_v1.txt
├── demonstrate_structure.csv           (1-row example, 115 cols)
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

16 RAR files remain alongside extracted CSVs. They contain the original compressed data — loaders should use the extracted CSVs.

### 4.2 Schema (all 89 data CSVs — identical headers)

115 columns. No label column. No device identifier column. All numeric (mostly float64, some int64 per device).

**Benign/malicious separation is by FILE, not by column.** Benign rows live in `benign_traffic.csv`. Attack rows live in `gafgyt_attacks/*.csv` and `mirai_attacks/*.csv`. No file mixes benign and attack rows.

**Attack sub-type** (e.g., combo, junk, scan, tcp, udp, ack, syn, udpplain) encoded in filename.

**Botnet family** encoded in directory structure (`gafgyt_attacks/` vs `mirai_attacks/`).

### 4.3 Column Categories (115 total)

Columns are statistical features of network traffic extracted over time windows at 5 decay factors (L5, L3, L1, L0.1, L0.01):

| Prefix | Count per decay | Total | Description |
|---|---|---|---|
| `MI_dir_*` | weight, mean, variance (3) | 15 | Marginal distribution of packet directions |
| `H_*` | weight, mean, variance (3) | 15 | Host entropy |
| `HH_*` | weight, mean, std, magnitude, radius, covariance, pcc (7) | 35 | Host-to-host joint entropy statistics |
| `HH_jit_*` | weight, mean, variance (3) | 15 | Host-to-host jitter |
| `HpHp_*` | weight, mean, std, magnitude, radius, covariance, pcc (7) | 35 | Host-to-host (port-based) joint entropy statistics |

Total: 15 + 15 + 35 + 15 + 35 = 115.

### 4.4 Constant / All-Zero Columns

Varies by attack type. Benign traffic: 0 constant columns. Mirai attacks: 20–35 constant columns (mostly HH/HpHp covariance/pcc/weight/std/radius). Gafgyt attacks: 0–3 constant columns (only in udp/tcp/junk, not in combo/scan).

Constant columns are attack-type-specific, not device-specific. A loader should NOT drop columns globally — different attack sub-types have different informative columns.

### 4.5 Row Counts

| Category | Range |
|---|---|
| Benign per device | 13,114 – 175,241 |
| Gafgyt attack per file | 29,068 – 105,874 |
| Mirai attack per file | 61,852 – 237,665 |

### 4.6 Key Facts for Loader Configuration

- Device identity is only in the path (9 device names). Must be parsed from directory.
- Label construction: `(botnet_family, attack_sub_type)` for attacks, `BENIGN` for benign. Examples: `(gafgyt, combo)`, `(mirai, udpplain)`, `(mirai, udp)`. Note: both gafgyt and mirai have `scan` and `udp` — disambiguation requires the parent directory.
- All files have headers. All columns are numeric.
- No IP, timestamp, MAC, or flow-ID columns.
- `demonstrate_structure.csv` is documentation only, not data.
- 16 RAR archives are original compressed files — loaders use extracted CSVs.
- Column dtype varies per device/per-file (some columns are int64 in benign, float64 in attack). Load with consistent float64 casting.
- No missing values found in sampled data. No encoding issues.

---

## 5. Cross-Dataset Comparison

| Property | CIC_IOT_Dataset2023 | Edge-IIoTset | N-BaIoT |
|---|---|---|---|
| Feature columns | 39 | 61 | 115 |
| Label column | `Label` (merged only) | `Attack_label` + `Attack_type` | None (file-separated) |
| Label encoding | String (UPPERCASE) | int (0/1) + string | Path-derived |
| Device identity in data | No | No | No |
| Timestamp in data | No | `frame.time` (mixed type) | No |
| IP/port/flow ID | No | `ip.src_host`, `ip.dst_host`, port cols | No |
| Schema uniformity | 100% | 100% | 100% |
| No. classes (benign + attack) | 34 | 15 | 1 benign + 2×5 gafgyt + 2×5 mirai = 21 |
| Missing values | Rare (<0.01%) | None found | None found |
| Inf values | 1 occurrence | None found | None found |
| Constant columns | 3 (Telnet, SMTP, IRC) | Varies by protocol | 0–35 per attack type |

---

## 6. Loader Design Recommendations

1. **One loader per dataset** — schemas differ too much for a unified loader.
2. **Parse device/label from path** for CIC per-attack, N-BaIoT all files, and Edge-IIoTset normal traffic.
3. **Cast all numeric columns to float64** on load to handle mixed int/float across files.
4. **Handle `inf` explicitly** in CIC `Rate` column (replace with NaN or drop row).
5. **Do not drop constant columns globally** — their informativeness depends on attack type.
6. **Edge-IIoTset IP columns** (`ip.src_host`, `ip.dst_host`): hex-encoded strings, may need decoding if used as identifiers.
7. **N-BaIoT RAR files**: 16 archives still present alongside CSVs. Do not attempt to load them.
8. **Edge-IIoTset PCAP files**: 24 raw captures. Not data for CSV loaders.
