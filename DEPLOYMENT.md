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
| **Where** | Render (one service) | Vercel/Netlify + Render | Vercel + Neon Postgres |
| **Public URLs** | One | Two | Two |
| **Interface on Vercel/Netlify?** | No | **Yes** | **Yes** |
| **API on Vercel?** | No | No | **Yes** |
| **Data survives a restart?** | No (re-seeds) | No (re-seeds) | **Yes** |
| **Code changes needed** | None | None | Postgres + serverless rework |
| **Setup effort** | ~10 minutes | ~20 minutes | A few hours |

**Recommendation: Option A** if you just need a working link to show them, or
**Option B** if the URL needs to be a Vercel or Netlify one specifically.

---

## Option A — Render, single URL (recommended)

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
  on the free plan. Every restart re-seeds from the client's workbook, so the
  demo always opens on their real figures.
- **This is mostly a feature.** Nobody can permanently break the demo, and each
  visitor gets a clean set of books. Visitors can also press **Reset demo data**
  on the Dashboard.

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

## Option C — Everything on Vercel, with a hosted Postgres

This is the only way to have the *whole* application on Vercel. It works, but it
is real work and it changes the architecture.

The idea is to replace SQLite with a hosted Postgres (Neon has a free tier), so
the data lives outside the function instead of on a filesystem that disappears.

What it requires:

1. A Neon account and a free Postgres database.
2. `psycopg[binary]` added to `backend/requirements.txt`.
3. `RPCI_DATABASE_URL` changed to the Neon connection string.
4. Connection handling adjusted for serverless — each invocation is a new
   process, so a normal pool exhausts Postgres connections. Neon's pooled
   connection string plus a small pool size, or a driver like `pg8000` with
   `NullPool`.
5. The API exposed as a Vercel Python function (`api/index.py` with a
   `vercel.json` rewrite), rather than a long-running server.
6. The schema and seed run once against Postgres, not on every cold start.

The code is already portable in the ways that matter — money is `Decimal` with
`Numeric` columns, the database URL is environment-driven, and there are no
SQLite-specific queries or views. So this is a configuration and plumbing job
rather than a rewrite, but it is not a ten-minute job either.

**Ask for this option only if keeping the whole thing on Vercel genuinely
matters.** Option B gets you a Vercel URL with none of the risk.

---

## Environment variables

Set these on whichever host runs the API.

| Variable | Default | Purpose |
|---|---|---|
| `RPCI_DATABASE_URL` | `sqlite:///<repo>/rpci_demo.db` | Where the database lives |
| `RPCI_AUTO_SEED` | `true` | Seed from the workbook on first boot |
| `RPCI_SEED_FROM_EXCEL_PATH` | `<repo>/RPCI Accounts.xlsx` | Workbook to import |
| `RPCI_CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `RPCI_ALLOW_DEMO_RESET` | `true` | Show and allow the reset button |

`RPCI_CORS_ORIGINS` is `*` because the demo uses no cookies — the acting role
travels in a request header. Once you know your Vercel or Netlify URL you can
narrow it, for example:

```
RPCI_CORS_ORIGINS=https://rpci-erp-demo.vercel.app
```

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
