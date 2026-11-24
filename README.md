# AI Chatbot (Flask + Google Gemini)

An AI chat website with user accounts. By default it answers questions about AI security.
Upload a PDF and it answers from that document instead.

## Features

- **Chat with AI:** uses the Google Gemini API and remembers the conversation
- **Ask about a PDF:** upload a PDF and ask questions about what's in it
- **User accounts:** sign up, log in and log out
- **Saved chats:** save a conversation, open it again later, and download it as **PDF** or **JSON**
- **Admin panel:** manage users and saved chats, and see usage stats
- **Email alerts (optional):** a welcome email for new users, plus alerts to the admin

## Built with

Python · Flask · Google Gemini (`google-genai`) · SQLite · pypdf · ReportLab · Gunicorn

## Run it on your computer

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000

Create a `.env` file first:

```
SECRET_KEY=any-long-random-text
GEMINI_API_KEY=your-gemini-api-key
ADMIN_USERNAME=choose-an-admin-name
ADMIN_PASSWORD=choose-a-strong-password

# Optional, for email alerts (Gmail app password)
EMAIL_SENDER=you@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_ADMIN=you@gmail.com
```

## How it is organised

| File | What it does |
|---|---|
| `app.py` | All the pages and the chat logic |
| `database.py` | Users and saved chats in SQLite |
| `email_service.py` | Sends emails in the background (skipped if not set up) |
| `templates/` | Login, chat and admin pages |
