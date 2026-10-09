# Ransomware Behavior Analysis Lab

A self-contained, reversible ransomware simulation and detection lab. It demonstrates
the full attack–detection–forensics lifecycle in a safe, isolated environment.

---

## What It Does

This lab simulates ransomware behavior on a controlled set of benign files, detects
the attack in real time using a multi-signal behavioral detector, and produces a
forensic analysis report. Everything runs locally with no network access, no
persistence, and no real encryption — the "encryption" is a reversible XOR transform.

**Key capabilities:**

- Simulates ransomware file encryption (reversible XOR-0x41)
- Real-time behavioral detection using filesystem monitoring
- Multi-gate detection: velocity + entropy + burst analysis
- Forensic baseline collection and before/after comparison
- Automated HTML report generation with timeline and evidence explorer
- False-positive testing to validate detection accuracy

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| OS | Windows 10/11 |
| Python | 3.10+ (with "Add python.exe to PATH" enabled) |
| Dependencies | `watchdog>=3.0`, `psutil>=5.9`, `matplotlib>=3.5` |
| Optional | Regshot (x64 Unicode) — only for manual Windows-VM snapshots; the server auto-generates the comparison |

---

## How to Deploy

1. **Install Python dependencies:**
   ```powershell
   cd ransomware-behavior-lab
   pip install -r requirements.txt
   ```

2. **Edit the configuration** (if needed):
   - `lab_config.json` — change `project_root` and `lab_root` to match your setup
   - `simulator/config.json` — keep `lab_root` and `simulation_id` in sync

   > **Linux / server:** only `lab_root` (the victim folder) matters — e.g.
   > `/data/victim` or `/opt/labs/victim`. You can set it without editing
   > files via the `LAB_ROOT` environment variable (this is what Docker does).
   > The Desktop ransom-note copy is skipped automatically on headless systems.
   > The committed JSONs carry Windows defaults; the Docker entrypoint rewrites
   > both files to the container path on every start.

3. **Build the victim dataset:**
   ```powershell
   python simulator\generate_test_data.py
   ```
   This creates 200 synthetic files across 6 category folders.

---

## How to Run

### Option A: Web UI (Recommended for demos)

The web UI provides a guided, click-based workflow — perfect for explaining the lab to students.

1. **Install Flask:**
   ```powershell
   pip install -r webui\requirements.txt
   ```

2. **Start the web UI:**
   ```powershell
   python webui\app.py
   ```

3. **Open** `http://localhost:6767` in your browser

4. **Follow the on-screen steps:**
   - Click **Start Attack** → Snapshot 1 (baseline) is taken automatically → detector + simulator run → Snapshot 2 is taken automatically → comparison is auto-generated (no Regshot needed)
   - Click **Build Report** → report opens automatically in a new tab

The web UI handles the entire workflow: baseline → detector → simulator → post-attack → analysis → report.

> **Running on a server?** See [DEPLOY.md](../DEPLOY.md) for Docker deployment
> (continuous service on port 6767, LAN-accessible).

---

### Option B: Command Line

#### Quick Run (single window)

```powershell
python run_attack.py
```

This executes the full pipeline:
1. Collects a forensic baseline
2. Starts the behavior detector
3. Runs the ransomware simulator
4. Stops the detector and collects post-attack evidence
5. Bundles all artifacts into `runs/<timestamp>/`

#### Split Mode (two windows, best for demos)

```powershell
# Window 1
python run_attack.py --baseline-only

# Window 2 (after detector starts)
python simulator\ransomware_simulator.py

# Back in Window 1: press Enter when done
```

#### Generate the Report

On the server, the snapshot comparison is auto-generated — just run:

```powershell
python analysis\build_comparison.py
python build_report.py
```

On a Windows VM with manual Regshot snapshots, pass the comparison file explicitly:

```powershell
python build_report.py --comparison "D:\path\to\comparison.txt"
```

#### False-Positive Test

```powershell
python analysis\false_positive_test.py
```

#### Reset the Lab

```powershell
python reset_lab.py              # wipe + regenerate victim files
python reset_lab.py --no-refill  # wipe only
```

---

## How to View Results

After running the lab, check these locations:

| Location | Contents |
|----------|----------|
| `reports/report_*.html` | Self-contained HTML report (open in browser) |
| `reports/analysis_summary.json` | Before/after file comparison summary |
| `reports/0*.png` | Graphs (file counts, entropy distribution, file type impact) |
| `logs/simulation_*.json` | Per-file simulation events |
| `logs/ransomware_alert_*.json` | Detector alert with gate details |
| `runs/<timestamp>/` | Bundled artifacts for each run |
| `evidence/baseline/` | Pre-attack file snapshots |
| `evidence/post/` | Post-attack file snapshots |

The HTML report includes:
- Executive summary with time-to-detection
- Execution timeline (simulator + detector fused)
- Before/after file comparison
- Entropy distribution analysis
- Snapshot comparison (auto-generated on the server; Regshot paste accepted)
- Full evidence explorer with search and filtering

---

## Detection Logic

The detector uses three gates:

| Gate | Signal | Threshold |
|------|--------|-----------|
| 1 | File event velocity | ≥ 50 events in 5 seconds |
| 2 | High-entropy files | ≥ 5 of last 10 files above 7.2 bits/byte |
| 3 | Rename/delete burst | ≥ 20 renames AND ≥ 10 deletes |

An alert fires when **Gate 1 AND (Gate 2 OR Gate 3)** is satisfied.

---

## Safety

- **No network** — the simulator makes zero network connections
- **No persistence** — no registry keys, no scheduled tasks
- **No real encryption** — XOR-0x41 is reversible with `bytes(b ^ 0x41)`
- **Scoped target** — only touches the configured lab directory
- **Abort guards** — refuses to run on drive roots or system directories

---

## Project Structure

```
ransomware-behavior-lab/
├── lab_config.json              # Central configuration
├── lab_paths.py                 # Single source of truth for paths
├── run_attack.py                # Phase 1 orchestrator
├── reset_lab.py                 # Reset utility
├── build_report.py              # Report generator
├── report_data.py               # Report data layer
├── report_style.css             # Report styling
├── requirements.txt             # Python dependencies
├── webui/                       # Flask web UI (click-based workflow)
│   ├── app.py                   # Flask application
│   ├── requirements.txt         # Flask dependency
│   ├── templates/
│   │   └── index.html           # Main UI page
│   └── static/
│       └── style.css            # UI styling
├── simulator/                   # Ransomware simulator
├── detector/                    # Behavior detector
├── analysis/                    # Analysis scripts
├── docs/                        # Documentation
├── assets/
│   └── logo.png                 # Company logo (top-left in web UI + report)
├── evidence/                    # Forensic evidence (generated)
├── logs/                        # Logs (generated)
├── reports/                     # Reports (generated)
└── runs/                        # Run bundles (generated)
```
