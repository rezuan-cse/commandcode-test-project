# Deploying the demo

This guide covers getting the demo onto a public URL so the client can click
through it and send back their observations.

---

## Read this first: Vercel and Netlify cannot host this app on their own

This matters, so it is worth two minutes.

Vercel and Netlify are built for **static sites and short-lived functions**. This
application is neither. It needs:

1. **A running Python process.** The API is FastAPI with eleven feature modules,
   SQLAlchemy, and 56 tests. Netlify has no Python runtime at all, so the API
   cannot live there. Vercel does run Python, but only as short-lived functions.

2. **A place to write data that is still there next time.** The demo stores its
   books in SQLite and lets visitors post purchases, production runs, and sales.
   Those posts must still be visible on the next screen.

On both platforms the filesystem is **read-only except for a temporary
directory**, and that temporary directory is per-instance and wiped between cold
starts. If you deploy the API to Vercel as-is, this is what your client would
see:

> They post a sale. The screen says "Posted SALE-002, balanced". They go to the
> Dashboard. The sale is not there.

That would damage the demo far more than a slower load time would. So the
recommendation below keeps the API somewhere that can actually hold data, and
puts the interface on Vercel or Netlify if you want that URL.

---

## The three options

| | Option A | Option B | Option C |
|---|---|---|---|
| **Where** | Render (one service) | Vercel/Netlify + Render | Render + Neon Postgres |
| **Public URLs** | One | Two | One |
| **Interface on Vercel/Netlify?** | No | **Yes** | No |
| **Data survives a restart?** | No — re-seeds | No — re-seeds | **Yes** |
| **Setup effort** | ~10 minutes | ~20 minutes | ~25 minutes |
| **Good for** | One guided sitting | A Vercel/Netlify URL | Leaving a link with the client |

**Recommendation: Option C** if you are leaving the link with the client to
explore on their own. With Options A and B the data resets whenever the instance
sleeps, so anything they post disappears after about 15 minutes of inactivity —
which reads as a bug even though it is not one. Option A is fine for a single
guided session where you keep clicking.

---

## Option A — Render, single URL

The repository is already configured for this. `render.yaml` is a Render
blueprint and the `Dockerfile` builds the interface and the API into one image.

### Steps

1. Push this repository to GitHub (or GitLab).
2. Sign in at <https://render.com> and choose **New → Blueprint**.
3. Connect the repository. Render reads `render.yaml` and shows the plan.
4. Apply it. The first build takes a few minutes.
5. Render gives you a URL like `https://rpci-demo.onrender.com`.

That URL serves the interface and the API together. Nothing else to configure —
the workbook is inside the image and the database seeds itself on first boot.

### What to expect on the free plan

- **The first visit is slow.** Free instances sleep after about 15 minutes of
  inactivity and take 30–60 seconds to wake. Open the link yourself a minute
  before the client sees it, so their first impression is not a spinner.
- **Posted data resets when the instance restarts.** There is no persistent disk
  on the free plan, so the SQLite file is recreated from the workbook each time.
  Every restart therefore opens on the client's real figures.
- **Nobody can permanently break the demo**, and each visitor gets a clean set of
  books. Visitors can also press **Reset demo data** on the Dashboard.

**If you need the data to stay put, use Option C below instead.**

If you need posted data to survive permanently, add a disk to the Render service
(a paid plan) and keep `RPCI_DATABASE_URL` pointing at its mount path.

---

## Option B — Interface on Vercel or Netlify, API on Render

Use this when the shareable link must be a Vercel or Netlify address. The
interface becomes a fast static site; the API stays where it can hold data.

```
Client's browser  →  Vercel / Netlify  (the interface)
                            ↓  fetch
                     Render (the API and database)
```

The interface already supports this. `frontend/src/shared/api.ts` reads the API
address from `VITE_API_BASE`, and cross-origin requests are permitted by the
backend's CORS setting.

### Step 1 — Deploy the API to Render

Follow Option A. Render will also try to serve the interface; that is harmless.
Note the URL it gives you, for example `https://rpci-demo.onrender.com`. The
API's base address is that URL plus `/api`.

### Step 2 — Deploy the interface to Vercel

1. Sign in at <https://vercel.com> and choose **Add New → Project**.
2. Import the repository.
3. Set **Root Directory** to `frontend`.
   Vercel reads `frontend/vercel.json` for the build settings.
4. Under **Environment Variables**, add:

   | Name | Value |
   |---|---|
   | `VITE_API_BASE` | `https://rpci-demo.onrender.com/api` |

   Replace the host with your own Render URL. Keep the `/api` at the end.

5. Deploy. Vercel gives you a URL like `https://rpci-erp-demo.vercel.app`.

### Step 2 (alternative) — Deploy the interface to Netlify

1. Sign in at <https://netlify.com> and choose **Add new site → Import an
   existing project**.
2. Import the repository.
3. Set **Base directory** to `frontend`.
   Netlify reads `frontend/netlify.toml` for the build settings.
4. Under **Site configuration → Environment variables**, add the same
   `VITE_API_BASE` value as above.
5. Deploy.

### Step 3 — Check it

Open the Vercel or Netlify URL. The Dashboard should show net profit 1,600 and a
balance sheet of 801,600.

If every panel shows a red error instead, the interface cannot reach the API.
Check that `VITE_API_BASE` ends in `/api` and that the Render service is awake —
open the Render URL directly first.

---

## Option C — Render with a hosted Postgres (recommended for a shared link)

Use this when you are handing the client a URL to explore on their own. It keeps
one public URL, and **posted data survives a restart**, so nothing the client
enters vanishes while they are thinking.

Only the database changes. The API stays on Render exactly as in Option A; the
books simply live in a managed Postgres instead of a file inside the container.

```
Client's browser  →  Render (interface + API)
                          ↓
                     Neon Postgres (the books)
```

### Step 1 — Create a free Postgres database

1. Sign in at <https://neon.tech> and create a project.
2. Choose the region closest to your Render service — both are usually
   `us-east` or `eu-central`. Keeping them on the same continent matters more
   than it sounds; the API talks to the database on every request.
3. Copy the **connection string**. It looks like:

   ```
   postgresql://neondb_owner:AbC123@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

   Use the **direct** string, not the one with `-pooler` in the host. A single
   long-running container keeps its own small connection pool, so pgbouncer in
   front of it only adds a layer that prepared statements can trip over.

### Step 2 — Point Render at it

1. Open your Render service → **Environment**.
2. Set `RPCI_DATABASE_URL` to the connection string you copied. Paste it
   unchanged — the application rewrites `postgresql://` to use the installed
   driver, so no `+psycopg` suffix is needed.
3. Save. Render redeploys.

### Step 3 — First boot

Nothing else to do. On first start the application creates its tables and
imports the client's workbook. Later starts detect the data already there and
leave it alone, so restarts no longer reset anything.

**Verify it worked:** post a purchase, then wait twenty minutes, then reload the
page. If the purchase is still there, persistence is working. Under Option A it
would have gone.

### Clearing the data

Because data now persists, the **Reset demo data** button on the Dashboard is how
you return to the pristine workbook state. It empties the tables and re-imports;
it takes well under a second.

### Free tier notes

- Neon's free tier includes 0.5 GB of storage, which is far more than this demo
  will ever use.
- Neon's compute scales to zero when idle. The first request after a quiet spell
  may take a moment longer, but the data is untouched.
- If you later delete the Neon project, the demo will create a fresh empty
  database on the next boot and re-seed from the workbook. Nothing is lost that
  cannot be re-imported.

### Where Postgres differs from SQLite

Two changes were needed, both already made:

1. A Postgres driver (`psycopg`) is in `backend/requirements.txt`.
2. The demo reset deletes rows instead of dropping tables. `DROP TABLE` needs an
   exclusive lock, so on Postgres it blocks behind any session holding a read
   lock — with a running application that means it hangs. Row deletion takes only
   a row lock and is compatible with readers.

The whole test suite runs against both engines:

```bash
cd backend
.venv/bin/python -m pytest tests -q                                   # SQLite
RPCI_TEST_DATABASE_URL=postgresql+psycopg://user:pass@host/db \
  .venv/bin/python -m pytest tests -q                                 # Postgres
```

---

## Keeping the Render instance awake

Options A and C both run on Render, whose free tier puts a web service to sleep
after about 15 minutes without traffic. The next visitor then waits 30–60 seconds
while it starts again. The data is safe either way — this is only about the first
impression.

`.github/workflows/keep-alive.yml` requests `/healthz` every 10 minutes so the
instance never reaches that idle threshold. It needs no account and no
configuration; it starts running as soon as the repository has the file.

You can test it immediately from the **Actions** tab → *Keep the demo awake* →
**Run workflow**.

### What it will not do

Worth knowing, because it is easy to assume this is a guarantee:

- **GitHub's scheduler is best effort.** Scheduled runs are queued on shared
  runners and often start several minutes late. If a slot slips by more than
  about 5 minutes, the instance can still sleep.
- **It stops after 60 days without a push.** GitHub disables scheduled workflows
  in quiet repositories. Any commit re-enables them.
- **On a private repository it uses Actions minutes.** Every 10 minutes is
  roughly 1,080 minutes a month against the 2,000 free ones. Public repositories
  are unlimited.

If you want a firmer guarantee, a dedicated uptime monitor does the same job on
a fixed schedule and alerts you when the service is down — UptimeRobot and
cron-job.org both have free tiers. The workflow above is the option that needs no
third-party account.

If the demo moves to another host, change `DEMO_HEALTH_URL` in the workflow.

---

## Environment variables

Set these on whichever host runs the API.

| Variable | Default | Purpose |
|---|---|---|
| `RPCI_DATABASE_URL` | `sqlite:///<repo>/rpci_demo.db` | Where the books live |
| `RPCI_JWT_SECRET` | *(random per process)* | Session signing key. **Set this** |
| `RPCI_ACCESS_TOKEN_MINUTES` | `720` | How long a sign-in lasts |
| `RPCI_AUTO_SEED` | `true` | Seed from the workbook on first boot |
| `RPCI_SEED_FROM_EXCEL_PATH` | `<repo>/RPCI Accounts.xlsx` | Workbook to import |
| `RPCI_DEMO_PASSWORD` | `rpci` | Password for the seeded demo accounts |
| `RPCI_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `RPCI_ALLOW_DEMO_RESET` | `true` | Allow an Admin to restore the workbook state |

### Set RPCI_JWT_SECRET

Without it a random key is generated each time the process starts, which means
every restart signs everybody out — including every redeploy. There is no
guessable default in the source, so leaving it unset is safe, just annoying.

`render.yaml` asks Render to generate one and keep it. If you are configuring the
service by hand, generate your own:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Changing it later invalidates every existing session, which is also how you
would force everyone to sign in again.

### About RPCI_CORS_ORIGINS

It defaults to `*`, which is fine here because the session travels in an
`Authorization` header rather than a cookie — so a wide-open origin list does not
let another site act as the user. Once you know your Vercel or Netlify URL you
can narrow it anyway:

```
RPCI_CORS_ORIGINS=https://rpci-erp-demo.vercel.app
```

For the same reason `allow_credentials` is off in the CORS middleware: nothing
authenticates by cookie, so leaving it on would only widen the surface.

---

## Schema changes on a deployed database

Worth knowing if you keep iterating, because it caused a real outage.

`create_all()` creates tables that do not exist, but it **never alters one**. So
adding a column to a model is invisible to a database that already holds data,
and the app then fails at request time with a missing-column error. That is
exactly what happened when the password and 2FA columns were introduced.

`sync_schema()` in `backend/app/core/db.py` closes that gap. It runs at startup
and adds missing tables and columns. It is **additive only**: no drops, renames,
type changes, or backfills. A NOT NULL column with no server default cannot be
added to a table with rows, so it raises and says so rather than inventing data.

Watch the deploy log for `[schema] added …` lines to see what it did.

### It now refuses to start on the things it cannot fix

Rather than let a change it cannot express pass in silence, it checks for two
kinds of drift at startup:

- **A type mismatch stops the service.** If a model declares a wider
  `Numeric(18,4)` than the database holds, running on would truncate amounts
  quietly. A service that refuses to start is the better failure. The message
  names the column and both types.
- **A column no model claims is reported, not fatal.** That usually means a
  rename went wrong — the new column was added empty while the old one kept the
  data — so it is worth knowing, but not a reason to be down.

```
[schema] warning: accounts.old_name exists in the database but no model claims
it. Left untouched; probably a leftover from a rename.
```

**This is a stopgap, not a migration framework.** The specification calls for
Alembic, and that is the right answer once the schema needs something this
cannot express — dropping a column, changing a type, or backfilling. It is
deliberately not done yet: the remaining phases mostly add tables and columns,
which this handles, so the ceremony is deferred until it earns its keep.

---

## Collecting the client's feedback

A few things that make the demo easier to evaluate.

**Give them a short guided list rather than a bare link.** The
[README](README.md) has a ten-step walkthrough, and
[USER_MANUAL.md](USER_MANUAL.md) explains each screen in plain language. Sending
the manual alongside the link means they can read at their own pace.

**Point them at the integrity panel first.** It is the strongest part of the
demo: it finds a real 474,100 discrepancy in their own workbook. See section 9 of
the user manual.

**Tell them about the reset button.** It is on the Dashboard. They can post
whatever they like without worrying about breaking anything.

**Ask them to send observations against the screen names.** The screens are
Dashboard, Chart of Accounts, Journal Entries, Inventory & BOM, Purchase Entry,
Production Entry, Sales Entry, Trial Balance, General Ledger, Balance Sheet,
Roles & Access, and Configuration. Screen names make feedback much easier to act
on than "the report page".

**Two questions already open in the specification**, worth asking while they are
in front of it:

1. Should Store/Production staff be able to record purchases? At the moment they
   can record production but not buying materials, because the permission table
   groups purchases with sales.
2. What are the real VAT and payroll rules? The Configuration screen currently
   shows placeholders marked *pending client*.

---

## What I need from you to actually deploy

I cannot deploy from here — there are no Vercel, Netlify, or Render credentials
on this machine, and no command-line tools installed for them.

Either:

- **Do Option A yourself.** It is four steps and needs no code changes. Tell me
  if anything fails and I will fix it.
- **Give me access and I will do it.** A Render API key, or a Vercel token, added
  to the environment. Say the word and I will walk through creating them.
- **Tell me to install the CLI.** `npm i -g vercel` then `vercel login` gives an
  interactive login, which needs you at the keyboard for the browser step.

Whichever you choose, the repository is ready. `render.yaml`,
`frontend/vercel.json`, and `frontend/netlify.toml` are committed, the interface
reads its API address from the environment, and the reset endpoint is tested.
