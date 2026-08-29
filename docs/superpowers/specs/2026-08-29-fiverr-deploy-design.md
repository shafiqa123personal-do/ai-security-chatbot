# Fiverr Live Demo Deploy — Design

## Purpose

Turn `ai-security-chatbot` into a live, publicly clickable demo to link
from a Fiverr gig, so buyers can register and try the chatbot
themselves rather than watching a recording. Requires closing two
security gaps before the app is safe to expose publicly, then
deploying it to a free hosting tier.

## Security hardening (code changes)

**1. Remove the hardcoded default admin account**

`database.py`'s `init_db()` currently seeds `admin` / `admin123`
unconditionally on every startup. This is a public, guessable
credential — anyone could log in as admin and see every saved chat
log, or delete users.

Change: read `ADMIN_USERNAME` and `ADMIN_PASSWORD` from the
environment. Only seed an admin account if both are set (non-empty).
If either is missing, skip seeding — no default admin account exists
at all until explicitly configured. This mirrors how `GEMINI_API_KEY`
is already read.

**2. Remove the hardcoded `SECRET_KEY` fallback**

`app.py` line 32 currently falls back to the string
`"ai_security_key_2024"` if `SECRET_KEY` isn't set in the environment.
A predictable secret key lets an attacker forge session cookies (e.g.
impersonate the admin session).

Change: read `SECRET_KEY` from the environment with no fallback. If
it's missing at startup, raise a clear error immediately (fail fast)
rather than silently running with a known-insecure key.

**3. No other code changes.** `.env` is already gitignored
(confirmed), so real secrets never reach the GitHub repo. Public
self-registration stays open — that's the point of a live demo.

## Testing

Manual pass, run twice (before touching security code, and again
after, to confirm the hardening didn't break normal use):

- Register a new user, log in
- Send a chat message, confirm a Gemini response comes back
- Upload a PDF, confirm the bot answers from its content, remove the PDF
- Save a chat log, download it as JSON and as PDF
- Log in as the (now env-configured) admin, view stats/users/logs,
  delete a test log

After the hardening change specifically: confirm the app refuses to
start if `SECRET_KEY` is unset, and confirm no admin account is seeded
if `ADMIN_USERNAME`/`ADMIN_PASSWORD` are unset.

## GitHub

New repository under the user's existing GitHub account
(`shafiqa123personal-do`). Public vs. private is the user's call at
push time — not decided here. Push everything except what's already
gitignored (`.env`, `chatbot.db`, `uploads/`, `__pycache__/`).

## Deploy to Render

- User creates a free Render account (walked through interactively,
  not automatable from here).
- Connect the GitHub repo as a new Web Service.
- Render auto-detects the existing `Procfile` (`web: gunicorn
  app:app`) — no new deploy config needed.
- Set environment variables in Render's dashboard: `GEMINI_API_KEY`,
  `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and optionally
  `EMAIL_SENDER` / `EMAIL_PASSWORD` / `EMAIL_ADMIN` if email
  notifications should be live (app already no-ops safely if these are
  unset).
- Deploy; Render assigns a public `*.onrender.com` URL.

## Post-deploy smoke test

On the live URL: register a fresh throwaway account, send a chat
message, confirm a response, log in as admin with the configured
credentials, confirm the dashboard loads.

## Accepted risks (explicitly out of scope)

- **Cold starts:** Render's free tier spins the service down after 15
  minutes of inactivity; the next visit takes ~30-50s to wake up. Fine
  for a portfolio link.
- **Non-durable disk:** SQLite (`chatbot.db`) may reset on redeploy.
  Acceptable for a demo; not building a hosted database for this.
- **Cost abuse:** no custom rate limiting is being added. Chat is
  already gated behind login (self-registration required), and
  Gemini's own free-tier rate limits are the backstop against a
  stranger running up API costs.

## Out of scope

- Custom domain
- Persistent/hosted database
- Rate limiting beyond what Gemini's free tier already enforces
- CI/CD beyond Render's auto-deploy-on-push
