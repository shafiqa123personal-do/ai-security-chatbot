# Fiverr Live Demo Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the two hardcoded security gaps in `ai-security-chatbot`, verify it still works, then deploy it to Render as a live public URL for a Fiverr gig.

**Architecture:** No structural changes — same Flask + SQLite + Gemini app. Two secrets that were hardcoded (default admin credentials, Flask secret key) move to environment variables, required at startup with no insecure fallback. Deployment uses Render's existing `Procfile` (`web: gunicorn app:app`), unchanged.

**Tech Stack:** Flask, SQLite (`sqlite3`), `google-genai`, Render (hosting), GitHub (source), Render's REST API for env var configuration.

**Spec:** `docs/superpowers/specs/2026-08-29-fiverr-deploy-design.md`

## Global Constraints

- No default/guessable admin account may ever be seeded — only when `ADMIN_USERNAME` and `ADMIN_PASSWORD` are both set (spec: "Remove the hardcoded default admin account").
- `SECRET_KEY` has no fallback value — the app must fail fast at startup if it's unset (spec: "Remove the hardcoded `SECRET_KEY` fallback").
- `.env` stays gitignored; no secret value is ever written into a committed file or into this plan.
- Render's free tier (Hobby) is used — no paid plan, no custom domain, no added rate limiting (spec: "Accepted risks").

---

## Task 1: Remove hardcoded secrets from the code

**Files:**
- Modify: `database.py` (imports + `init_db()`)
- Modify: `app.py:29-37`

**Interfaces:**
- Produces: `init_db()` now reads `ADMIN_USERNAME`/`ADMIN_PASSWORD` from the environment instead of hardcoding `admin`/`admin123`. `app.secret_key` now comes from a required `SECRET_KEY` env var with no fallback. Later tasks (local testing, Render env var config) depend on these exact variable names.

- [ ] **Step 1: Add `import os` to `database.py`**

Current top of file:
```python
import sqlite3
from datetime import datetime
```

Change to:
```python
import os
import sqlite3
from datetime import datetime
```

- [ ] **Step 2: Replace the hardcoded admin seed in `database.py`'s `init_db()`**

Current (lines 38-46):
```python
    from werkzeug.security import generate_password_hash
    try:
        conn.execute(
            "INSERT INTO users (username, password, email, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "", 1, datetime.now().isoformat())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
```

Replace with:
```python
    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_username and admin_password:
        from werkzeug.security import generate_password_hash
        try:
            conn.execute(
                "INSERT INTO users (username, password, email, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
                (admin_username, generate_password_hash(admin_password), "", 1, datetime.now().isoformat())
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
```

- [ ] **Step 3: Replace the hardcoded `SECRET_KEY` fallback in `app.py`**

Current (lines 29-32):
```python
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ai_security_key_2024")
```

Replace with:
```python
load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set. Add it to your .env file.")

app = Flask(__name__)
app.secret_key = SECRET_KEY
```

- [ ] **Step 4: Add the new required variables to the local `.env`**

`.env` already has `SECRET_KEY` and `GEMINI_API_KEY` set. Add two new lines (pick any username/password you'll remember — this becomes your real admin login):

```
ADMIN_USERNAME=<choose a username>
ADMIN_PASSWORD=<choose a password>
```

- [ ] **Step 5: Commit**

```bash
git add database.py app.py
git commit -m "Require admin credentials and secret key from environment, remove hardcoded defaults"
```

---

## Task 2: Local regression test

**Files:** none (verification only)

- [ ] **Step 1: Delete the local test database so `init_db()` re-seeds cleanly**

The existing `chatbot.db` still has the old hardcoded `admin`/`admin123` row from before Task 1 (inserting a new admin doesn't remove it). Delete it so the next startup reflects the new env-var-driven behavior:

```bash
rm chatbot.db
```

- [ ] **Step 2: Verify fail-fast when `SECRET_KEY` is missing**

Temporarily rename `.env`:
```bash
mv .env .env.bak
```
Run: `python app.py`
Expected: crashes immediately with `RuntimeError: SECRET_KEY is not set. Add it to your .env file.`

Restore it:
```bash
mv .env.bak .env
```

- [ ] **Step 3: Verify no admin account is seeded without `ADMIN_USERNAME`/`ADMIN_PASSWORD`**

Temporarily comment out or remove the `ADMIN_USERNAME`/`ADMIN_PASSWORD` lines from `.env`, delete `chatbot.db` again, then run `python app.py` and try logging in at `http://127.0.0.1:5000/login` with `admin` / `admin123`.
Expected: "Username not found" — the old default no longer exists.

Stop the server, restore the `ADMIN_USERNAME`/`ADMIN_PASSWORD` lines in `.env`, delete `chatbot.db` again so it re-seeds with the real values.

- [ ] **Step 4: Full manual regression pass**

Run: `python app.py`, open `http://127.0.0.1:5000`, and confirm:
- Register a new user, log in
- Send a chat message, confirm a Gemini response comes back
- Upload a PDF, confirm the bot answers from its content, remove the PDF
- Save a chat log, download it as JSON and as PDF
- Log out, log back in as the admin username/password from `.env`
- Admin dashboard loads: stats, users list, logs list
- Delete the test log created above

Stop the server (Ctrl+C) when done.

---

## Task 3: Push to GitHub

**Files:** none (repo operation)

- [ ] **Step 1: Confirm visibility with the user**

Ask whether the new GitHub repo should be public (doubles as a code-quality showcase) or private, per the spec — this wasn't decided in advance.

- [ ] **Step 2: Create and push the repo**

```bash
gh repo create ai-security-chatbot --source=. --remote=origin --push --public
```
(swap `--public` for `--private` per the user's answer in Step 1)

- [ ] **Step 3: Verify**

Run: `gh repo view --web` and confirm the code is visible on GitHub, and that `.env`, `chatbot.db`, and `uploads/` are **not** present in the repo (they're gitignored).

---

## Task 4: Create the Render Web Service

**Files:** none (Render dashboard)

**Interfaces:**
- Produces: a Render service with an ID of the form `srv-xxxxxxxxxxxx`, visible in the dashboard URL once created. Task 5 consumes this ID.

- [ ] **Step 1: Guide the user through the dashboard wizard**

In the Render dashboard: click **New** (top right) → **Web Service**. Select the `ai-security-chatbot` GitHub repo (if it's not listed, Render will prompt to grant it access to the repo — approve that). Render should auto-detect the `Procfile` and offer Python as the runtime.

- Name: `ai-security-chatbot` (or the user's preference)
- Plan: **Free**
- Leave the environment variables section empty for now — Task 5 sets them via API

Click **Create Web Service**. The first build/deploy will likely fail or crash-loop (missing `SECRET_KEY`/`GEMINI_API_KEY`) — that's expected and fixed in Task 5.

- [ ] **Step 2: Get the service ID**

Once created, the browser URL looks like `https://dashboard.render.com/web/srv-xxxxxxxxxxxx`. Ask the user to copy the `srv-...` part, or read it directly from a screenshot they share.

---

## Task 5: Configure environment variables and deploy

**Files:** none (Render API calls, run from the local machine)

**Interfaces:**
- Consumes: the Render API key at `C:\Users\Ayzal\AppData\Local\Temp\claude\C--Users-Ayzal\aa927830-7af5-4662-810a-a3bebf76b1d0\scratchpad\render_api_key.txt`, the local `.env` file (Task 1) for `GEMINI_API_KEY`/`SECRET_KEY`/`ADMIN_USERNAME`/`ADMIN_PASSWORD`, and the service ID from Task 4.

- [ ] **Step 1: Set the environment variables via Render's API**

Run (replace `<SERVICE_ID>` with the ID from Task 4 Step 2; run from the `ai-security-chatbot` directory so `.env` resolves):

```bash
python3 - <<'PYEOF'
import json
import urllib.request

SERVICE_ID = "<SERVICE_ID>"
API_KEY_PATH = r"C:\Users\Ayzal\AppData\Local\Temp\claude\C--Users-Ayzal\aa927830-7af5-4662-810a-a3bebf76b1d0\scratchpad\render_api_key.txt"

def load_env(path=".env"):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

env = load_env()
api_key = open(API_KEY_PATH).read().strip()

env_vars = [
    {"key": "GEMINI_API_KEY", "value": env["GEMINI_API_KEY"]},
    {"key": "SECRET_KEY", "value": env["SECRET_KEY"]},
    {"key": "ADMIN_USERNAME", "value": env["ADMIN_USERNAME"]},
    {"key": "ADMIN_PASSWORD", "value": env["ADMIN_PASSWORD"]},
]

req = urllib.request.Request(
    f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars",
    data=json.dumps(env_vars).encode(),
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
    method="PUT",
)
with urllib.request.urlopen(req) as resp:
    print("env-vars update status:", resp.status)
PYEOF
```

Expected: `env-vars update status: 200`

- [ ] **Step 2: Trigger a fresh deploy**

```bash
python3 - <<'PYEOF'
import json
import urllib.request

SERVICE_ID = "<SERVICE_ID>"
API_KEY_PATH = r"C:\Users\Ayzal\AppData\Local\Temp\claude\C--Users-Ayzal\aa927830-7af5-4662-810a-a3bebf76b1d0\scratchpad\render_api_key.txt"

api_key = open(API_KEY_PATH).read().strip()

req = urllib.request.Request(
    f"https://api.render.com/v1/services/{SERVICE_ID}/deploys",
    data=b"{}",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    },
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    print("deploy trigger status:", resp.status)
PYEOF
```

Expected: `deploy trigger status: 201`

- [ ] **Step 3: Watch the deploy**

Tell the user to open the service's **Logs** tab in the Render dashboard and watch for `Booting worker` (gunicorn started successfully) rather than a crash/traceback.

---

## Task 6: Post-deploy smoke test

**Files:** none (verification only)

- [ ] **Step 1: Get the public URL**

From the Render dashboard, copy the service's URL (top of the service page, looks like `https://ai-security-chatbot-xxxx.onrender.com`).

- [ ] **Step 2: Full smoke test on the live URL**

Visit the URL (first load may take 30-50s if the service was asleep). Confirm:
- Register a fresh throwaway account, log in
- Send a chat message, confirm a real Gemini response
- Log in as the admin account (the `ADMIN_USERNAME`/`ADMIN_PASSWORD` from `.env`/Render env vars) and confirm the dashboard loads

- [ ] **Step 3: Report the live URL back to the user**

This is the link to use in the Fiverr gig.
