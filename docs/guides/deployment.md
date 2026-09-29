# Deployment and configuration

## Deploying to a public URL

**See [DEPLOYMENT.md](../../DEPLOYMENT.md)** for the full guide, including why Vercel
and Netlify cannot host the API by themselves and which option to pick.

The short version: `render.yaml` is a Render blueprint. Point Render at the
repository, apply the blueprint, and it builds the Docker image and serves the
demo over HTTPS on a single URL. No other configuration is needed — the workbook
is baked into the image and the database seeds itself on first boot.

To put the *interface* on Vercel or Netlify instead, deploy the API to Render and
set `VITE_API_BASE` on the static host. `frontend/vercel.json` and
`frontend/netlify.toml` are already in place.

For a public URL, prefer a hosted Postgres (Neon free tier) so posted data
survives the host sleeping. See the SQLite-or-Postgres section below.

## Configuration

Copy `.env.example` to `.env`, or set the variables directly:

| Variable | Default | Purpose |
|---|---|---|
| `RPCI_DATABASE_URL` | `sqlite:///./rpci_demo.db` | Where the books live — SQLite or Postgres |
| `RPCI_JWT_SECRET` | *(random per process)* | Session signing key. Set it on any deployment |
| `RPCI_ACCESS_TOKEN_MINUTES` | `720` | How long a session lasts |
| `RPCI_DEMO_PASSWORD` | `rpci` | Password for the seeded demo accounts |
| `RPCI_SEED_MODE` | `fresh` | `fresh` (starter chart of accounts), `workbook`, or `none` |
| `RPCI_SEED_FROM_EXCEL_PATH` | `../RPCI Accounts.xlsx` | Workbook to import |
| `RPCI_CORS_ORIGINS` | `*` | Origins allowed to call the API |
| `RPCI_ALLOW_DATA_RESET` | `true` | Allow an Admin to start the books over |

If `RPCI_JWT_SECRET` is unset, a random key is generated at process start. That
keeps local development frictionless and means there is no guessable default in
the source, but it signs everyone out whenever the service restarts. Generate a
real one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### SQLite or Postgres

SQLite is the default: one file, no setup. It is fine locally and for a demo held
in a single sitting.

**On a host with no persistent disk, SQLite loses everything on a restart.** A
free Render instance sleeps after ~15 minutes; when it wakes, the container's
filesystem is recreated, so the SQLite file is gone and startup seeds the starting
state again. Every boot logs which database is in use, so this is easy to spot:

```
[db] using sqlite file /data/rpci_demo.db                      <- data will be lost
[db] using postgresql database books on ep-….neon.tech          <- persistent
```

For a link you leave with the client, point `RPCI_DATABASE_URL` at a Postgres
database so nothing they enter disappears when the host sleeps:

```bash
RPCI_DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

Paste a hosted URL unchanged — the application rewrites `postgres://` and
`postgresql://` to the installed `psycopg` driver, so no `+psycopg` suffix is
needed. Either Neon host works: the **direct** host is simplest, and a **pooled**
(`-pooler`) host is supported because the app disables prepared statements for
Postgres. Tables are created and seeded on first boot, and left alone afterwards.
See [DEPLOYMENT.md](../../DEPLOYMENT.md), option C, and its *"All my data reset to
zero"* section.

The suite runs against either engine:

```bash
cd backend
.venv/bin/python -m pytest tests -q                      # SQLite
RPCI_TEST_DATABASE_URL=postgresql+psycopg://user:pass@host/db \
  .venv/bin/python -m pytest tests -q                    # Postgres
```

Reset from the interface (Administration → Data), by deleting the database file,
or with `backend/.venv/bin/python scripts/seed_from_excel.py --rebuild`.
