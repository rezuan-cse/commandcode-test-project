# Deploying on your own VPS

For the internal deployment: one Ubuntu 24.04 server, Postgres on the same box,
Caddy for TLS. This is the setup that suits a handful of employees better than any
free public host — no cold start, no deploy queue, real cron, and the database never
touches the internet.

Sized for: 4 cores, 8 GB RAM, 80 GB NVMe. That is comfortably more than this
system needs; the headroom is yours for OS updates, logs and dumps.

---

## 1. What runs

| Container | Purpose | Reachable from |
|---|---|---|
| `caddy` | TLS + reverse proxy | the internet, on 80/443 only |
| `app` | FastAPI + the built SPA | localhost only (`127.0.0.1:8000`) |
| `db` | PostgreSQL 17 | **nothing** — compose network only |

There is no published database port. That is deliberate: the only way in is through
the application, which enforces the permissions.

---

## 2. First-time setup

```bash
# On the server, as a sudo user.
sudo apt update && sudo apt install -y git
git clone <your-repo-url> /opt/rpci && cd /opt/rpci
git checkout production

# Docker Engine + compose plugin (Ubuntu's docker.io is too old for compose v2).
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"   # log out and back in for this to take effect
```

### Configure it

```bash
cp deploy/.env.production.example .env.production
chmod 600 .env.production
```

Fill in `.env.production`:

- **`SITE_ADDRESS`** — the domain you will point at this box.
- **`POSTGRES_PASSWORD`** — `openssl rand -base64 24`
- **`RPCI_JWT_SECRET`** — `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`

### Point DNS

An `A` record for the domain at the server's public IP. **Ports 80 and 443 must both
be open** — Let's Encrypt's challenge arrives on 80:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# Do NOT open 5432. Nothing outside the box needs it.
```

---

## 3. The one code change to make first

`Dockerfile` line 36 sets a **SQLite fallback**:

```
ENV RPCI_DATABASE_URL="sqlite:////data/rpci_demo.db"
```

`docker-compose.prod.yml` overrides it with the Postgres URL, so on this deployment
the fallback never applies. But leaving it in means a *later* misconfiguration —
someone runs the image without compose, or a variable goes missing — silently boots
on a throwaway SQLite file, and the books appear empty rather than the app failing.

**Make the database URL required in production.** That turns a silent data-loss into
a loud startup error. It is a small change to `config.py`, and I would do it before
the client's real figures go in.

---

## 4. Start it

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f docker-compose.prod.yml ps        # all three should be healthy
docker compose -f docker-compose.prod.yml logs -f app | head -40
```

The app log prints which database it is using on boot:

```
[db] using postgresql database rpci on db (not pooled)
```

Caddy fetches the certificate on first request. Visit the site; the sign-in screen
should appear over HTTPS.

### The first administrator

`RPCI_SEED_DEMO_USERS=false` means a fresh database has **no accounts at all**, so
nothing can sign in yet. Make one:

```bash
docker compose -f docker-compose.prod.yml exec app \
  python /app/scripts/create_user.py --email you@example.com \
  --name "Your Name" --role admin
```

The path is **absolute on purpose**. `exec` starts in the image's working directory,
`/app/backend`, and `scripts/` lives at `/app/scripts` — so a relative
`python scripts/create_user.py` fails with "No such file or directory". Either the
absolute path above, or `-w /app` to change the directory, works.

It prints a strong password once. Every later account is better made from
**Roles & Access**, where the role and per-user grants are set together.

Then, in **Configuration → Company details**, paste the client's **BIN**
(`002016027-0208`) and **TIN** (`155979113247`) and save. The seeded defaults are
used only for a database that does not have those rows yet.

---

## 5. Backups — do this before real data goes in

```bash
sudo apt install -y cron     # usually already present
cd /opt/rpci
./deploy/backup.sh           # run once by hand to prove it works
```

Then nightly, from `crontab -e`:

```cron
15 2 * * *  cd /opt/rpci && ./deploy/backup.sh >> /var/log/rpci-backup.log 2>&1
```

**Keep the output off this machine.** A backup beside the database is lost with the
database — the server's own disk failing takes both. Mount a second volume, or sync:

```cron
45 2 * * *  rclone sync /opt/rpci/backups remote:rpci-backups
```

**Restore one, once, now** — a backup that has never been restored is a guess:

```bash
docker compose -f docker-compose.prod.yml stop app
./deploy/restore.sh backups/rpci-YYYYMMDD-HHMM.dump --yes
docker compose -f docker-compose.prod.yml start app
```

Then sign in and check the Dashboard: **trial-balance difference must read 0.0000**.

`deploy/backup.sh` keeps the last 30 archives. `scripts/backup_db.py` also still
works if you install `postgresql-client` on the host — but the container-based
script needs nothing extra, which is why the cron uses it.

---

## 6. Updating

```bash
cd /opt/rpci
git pull                      # or: git fetch && git checkout production && git pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Downtime is the restart, a few seconds. Schema changes are additive and applied at
boot; the app adds tables and nullable columns and never drops anything.

**Take a backup before every update.** It is two seconds and it is the difference
between a bad deploy and a lost quarter.

---

## 7. Operating notes

- **Logs:** `docker compose -f docker-compose.prod.yml logs -f app`
- **Restart:** `docker compose -f docker-compose.prod.yml restart app`
- **Shell in the app:** `docker compose -f docker-compose.prod.yml exec app sh`
- **Database shell:** `docker compose -f docker-compose.prod.yml exec db psql -U rpci -d rpci`
- **Disk:** the NVMe holds the OS, images, dumps and the database. `df -h` and
  `docker system prune -af` occasionally; dumps are pruned automatically.
- **Reboot:** all three containers are `restart: unless-stopped`, so the stack comes
  back on its own. Nothing needs starting by hand.
- **Machine time:** containers run UTC and the app converts to +06:00 for display,
  so the host's timezone does not affect the books.

## 8. If you do not want it on the public internet

Two options, both better than a public URL for payroll and financials:

**Cloudflare Tunnel** — no open ports, no public IP needed. Add a `cloudflared`
container and point it at `app:8000`; set `SITE_ADDRESS` to the tunnel hostname and
drop the `caddy` service entirely.

**Tailscale or WireGuard** — staff join a private network and reach the box
directly. Simplest is Tailscale on the host with Caddy serving on the tailnet
address; no certificate challenge needed.

For an internal tool used by a group of employees, either is a genuine improvement
over exposing it: the only people who can reach the login screen are the people who
are meant to.
