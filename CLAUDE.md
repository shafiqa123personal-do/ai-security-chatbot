# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Install dependencies: `pip install -r requirements.txt`
- Run the dev server: `python app.py` (Flask debug mode, http://localhost:5000)
- Run the way it's deployed: `gunicorn app:app` (per `Procfile`, Heroku-style deployment)

No test suite, linter, or build step exists in this repository.

### Required environment variables (`.env`, gitignored)

- `SECRET_KEY` — Flask session signing key
- `GEMINI_API_KEY` — Google Gemini API key (`google-genai` client)
- `EMAIL_SENDER` / `EMAIL_PASSWORD` — Gmail SMTP credentials used to send notification emails
- `EMAIL_ADMIN` — address that receives new-user/chat-saved admin notifications

`email_service.py` silently no-ops if `EMAIL_SENDER`/`EMAIL_PASSWORD`/the recipient address are unset, so the app runs fine without email configured.

## Architecture

Single-file Flask monolith: all routes live in `app.py`, with three supporting modules.

- `database.py` — raw `sqlite3` access (no ORM) against `chatbot.db`. `init_db()` creates the `users` and `chat_logs` tables and is called unconditionally at module import time in `app.py` (not inside `if __name__ == "__main__":`), so it also runs under `gunicorn`. It also seeds a default `admin` / `admin123` account if one doesn't already exist.
- `email_service.py` — fire-and-forget Gmail SMTP notifications (new user registered, chat saved, welcome email). `app.py` dispatches these on background daemon threads (`threading.Thread(..., daemon=True)`) so sending never blocks the request.
- `templates/` (`login.html`, `index.html`, `admin.html`) + `static/style.css` — server-rendered pages, no frontend framework or build step.

Auth and session state:
- Session-cookie auth only (no server-side session store) — `session["username"]`, `session["is_admin"]`, `session["history"]` (chat messages), `session["pdf_context"]` (uploaded-PDF text).
- Two decorators gate routes: `login_required` (any logged-in user) and `admin_required` (`session["is_admin"]`), the latter guarding the `/admin/*` routes (user management, log management, stats).
- Chat history lives only in the session until a user explicitly calls `/save-log`, which persists it to the `chat_logs` table; nothing is auto-saved.

Chat flow:
- `/send` builds the Gemini request from `session["history"]`, using model `gemini-2.0-flash-lite` via `google-genai`.
- `get_system_prompt()` switches between a fixed AI-security-expert system prompt (`DEFAULT_SYSTEM_PROMPT`) and an "answer from this document" prompt once a PDF has been uploaded via `/upload-pdf` (text extracted with `pypdf`, truncated to 15,000 chars, kept in `session["pdf_context"]` — not persisted beyond the uploaded file itself).
- Saved chat logs can be exported as JSON or as a generated PDF (`generate_pdf()`, built with `reportlab`) via `/download-log/<id>` and the admin equivalent `/admin/download-log/<id>`.

This directory is not a git repository, so there's no commit history to consult for context.
