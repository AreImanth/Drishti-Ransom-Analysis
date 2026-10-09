# Ransomware Behavior Lab

A hands-on cybersecurity lab built as a personal learning project.
It simulates ransomware behavior on a controlled set of benign files, detects
the attack in real time, and produces a forensic analysis report — all through
a click-based web UI.

---

## Quick Start

Full setup and usage instructions live in the lab README:

**[ransomware-behavior-lab/README.md](./ransomware-behavior-lab/README.md)**

TL;DR:

```bash
pip install -r ransomware-behavior-lab/requirements.txt
pip install -r ransomware-behavior-lab/webui/requirements.txt
python ransomware-behavior-lab/webui/app.py
# open http://localhost:6767
```

Or deploy with Docker (continuous service, LAN-accessible) — see
**[DEPLOY.md](./DEPLOY.md)**.

---

## General Prerequisites

- **Python 3.10+** installed
- **Git** for cloning
- **Docker** (only for the server deployment)

---

## Safety Notice

This lab is designed for **educational purposes only**. Run it only in
isolated lab environments. The simulator touches only the configured victim
folder, uses no network, and its transform is fully reversible.

---

## License

Provided under the MIT License for educational use.
