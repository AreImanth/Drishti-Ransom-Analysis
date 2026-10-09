# Deploying to the Ubuntu Server (Docker)

Target server: `100.84.56.125`
Deploy path: `/opt/bcssl-teqm/imanth`
Web UI port: `6767` → access at `http://100.84.56.125:6767`

---

## Step 1 — Copy files to the server

From your Windows machine (PowerShell), copy the whole `cybersecurity-labs`
folder to the server:

```powershell
scp -r "C:\Users\imant\Downloads\complete_report_file\cybersecurity-labs" imanth@100.84.56.125:/opt/bcssl-teqm/imanth/
```

Enter your SSH password when prompted.

## Step 2 — SSH into the server

```powershell
ssh imanth@100.84.56.125
```

Then go to the deploy folder:

```bash
cd /opt/bcssl-teqm/imanth/cybersecurity-labs
ls -la
```

You should see `docker-compose.yml`, `DEPLOY.md`, and
`ransomware-behavior-lab/`.

## Step 3 — Build and start (runs continuously)

```bash
docker compose up -d --build
```

The `restart: unless-stopped` policy keeps the container running across
reboots. Check status with:

```bash
docker compose ps
docker compose logs -f ransomware-lab
```

## Step 4 — Open the web UI (from any machine on the same LAN)

```
http://100.84.56.125:6767
```

Health check endpoint:

```
http://100.84.56.125:6767/health
```

## Step 5 — First run on the server

1. The container auto-creates 200 victim files in a Docker volume on first start.
2. Open the web UI → click **Start Attack** → confirm.
   Snapshot 1 (baseline) and Snapshot 2 (post-attack) are taken automatically,
   and the comparison is auto-generated — no Regshot needed.
3. Click **Build Report** → the report opens automatically in a new tab.

> **Note:** On a Windows VM you can still take manual Regshot snapshots and
> paste the comparison via *Advanced → paste a Regshot comparison manually*.
> On the server this is unnecessary — the auto-generated comparison covers it.

---

## Useful commands

| Task | Command |
|------|---------|
| View live logs | `docker compose logs -f ransomware-lab` |
| Restart | `docker compose restart ransomware-lab` |
| Stop | `docker compose stop` |
| Stop + remove | `docker compose down` |
| Rebuild after code changes | `docker compose up -d --build` |
| Shell into container | `docker exec -it ransomware-lab /bin/bash` |
| Check victim files | `docker exec ransomware-lab ls /data/victim \| head` |

## Firewall (if the page doesn't load)

On the Ubuntu server, allow the port:

```bash
sudo ufw allow 6767/tcp
sudo ufw reload
```

## Data persistence

Victim files live in the `ransomware-victim` Docker volume, and
`reports/`, `logs/`, `runs/`, `evidence/` are bind-mounted to the host folder,
so all results survive container rebuilds.
