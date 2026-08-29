from flask import (
    Flask, render_template, request,
    jsonify, session, redirect, url_for, send_file
)
from google import genai
from google.genai import types
import os
import json
import io
import threading
from datetime import datetime
from pypdf import PdfReader
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from database import (
    init_db, create_user, get_user,
    save_chat_log, get_user_logs, get_log_by_id,
    delete_log, get_all_users, get_all_logs,
    delete_user, get_stats
)
from email_service import notify_new_user, notify_chat_saved, send_welcome_email

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set. Add it to your .env file.")

app = Flask(__name__)
app.secret_key = SECRET_KEY

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

DEFAULT_SYSTEM_PROMPT = """
You are an expert AI Security assistant based on the research paper
"Artificial Intelligence Security: Threats and Countermeasures" by Hu et al. (2021).

Topics you know deeply:
1. Data Collection Attacks: bias, fake data, sensor spoofing, data breach
2. Image Scaling Attacks and Decamouflage defense
3. Data Poisoning: availability attacks, backdoor attacks, clean label poisoning
4. Adversarial Examples: FGSM, BIM, JSMA, DeepFool, C&W, ZOO, MalGAN
5. Defenses: adversarial training, feature squeezing, defensive distillation
6. System Integration: model inversion, model extraction, differential privacy

Answer clearly and simply. Use bullet points for lists.
"""


def get_system_prompt():
    pdf_context = session.get("pdf_context", "")
    if pdf_context:
        return f"""You are an expert assistant. Answer based on this document:

--- DOCUMENT ---
{pdf_context}
--- END ---

Be clear and simple. Use bullet points."""
    return DEFAULT_SYSTEM_PROMPT


def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session or not session.get("is_admin"):
            return redirect(url_for("chat_page"))
        return f(*args, **kwargs)
    return decorated


def generate_pdf(title, messages, created_at):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("Title", parent=styles["Heading1"],
                                  fontSize=18, textColor=colors.HexColor("#667eea"), spaceAfter=6)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"],
                                 fontSize=9, textColor=colors.grey, spaceAfter=16)
    user_label = ParagraphStyle("UserLabel", parent=styles["Normal"],
                                 fontSize=8, textColor=colors.HexColor("#764ba2"),
                                 fontName="Helvetica-Bold", spaceAfter=2)
    bot_label = ParagraphStyle("BotLabel", parent=styles["Normal"],
                                fontSize=8, textColor=colors.HexColor("#2d8a4e"),
                                fontName="Helvetica-Bold", spaceAfter=2)
    user_msg_style = ParagraphStyle("UserMsg", parent=styles["Normal"],
                                     fontSize=10, backColor=colors.HexColor("#f0eeff"),
                                     spaceAfter=12, leftIndent=10, rightIndent=10, leading=14)
    bot_msg_style = ParagraphStyle("BotMsg", parent=styles["Normal"],
                                    fontSize=10, backColor=colors.HexColor("#f5f5f5"),
                                    spaceAfter=12, leftIndent=10, rightIndent=10, leading=14)

    story = []
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(f"Exported: {created_at[:16]}  |  AI Security Chatbot", meta_style))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=colors.HexColor("#667eea"), spaceAfter=14))

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "").replace("&", "&amp;").replace("\n", "<br/>")
        if role == "user":
            story.append(Paragraph("You", user_label))
            story.append(Paragraph(content, user_msg_style))
        else:
            story.append(Paragraph("AI Security Bot", bot_label))
            story.append(Paragraph(content, bot_msg_style))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=6))
    story.append(Paragraph("Generated by AI Security Chatbot",
                            ParagraphStyle("Footer", parent=styles["Normal"],
                                           fontSize=8, textColor=colors.grey)))
    doc.build(story)
    buffer.seek(0)
    return buffer


# ── Auth Routes ─────────────────────────────────────────────

@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("chat_page"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json()
        action = data.get("action")
        username = data.get("username", "").strip().lower()
        password = data.get("password", "").strip()

        if not username or not password:
            return jsonify({"error": "Username and password required"}), 400

        if action == "register":
            if len(username) < 3:
                return jsonify({"error": "Username must be at least 3 characters"}), 400
            if len(password) < 6:
                return jsonify({"error": "Password must be at least 6 characters"}), 400
            user_email = data.get("email", "").strip()
            hashed = generate_password_hash(password)
            if not create_user(username, hashed, user_email):
                return jsonify({"error": "Username already exists"}), 400
            session["username"] = username
            session["is_admin"] = False
            session["history"] = []
            threading.Thread(target=notify_new_user, args=(username,), daemon=True).start()
            if user_email:
                threading.Thread(target=send_welcome_email, args=(username, user_email), daemon=True).start()
            return jsonify({"success": True})

        elif action == "login":
            user = get_user(username)
            if not user:
                return jsonify({"error": "Username not found"}), 400
            if not check_password_hash(user["password"], password):
                return jsonify({"error": "Wrong password"}), 400
            session["username"] = username
            session["is_admin"] = bool(user["is_admin"])
            session["history"] = []
            return jsonify({"success": True, "is_admin": bool(user["is_admin"])})

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Chat Routes ─────────────────────────────────────────────

@app.route("/chat")
@login_required
def chat_page():
    return render_template("index.html",
                           username=session["username"],
                           is_admin=session.get("is_admin", False))


@app.route("/send", methods=["POST"])
@login_required
def send_message():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    if "history" not in session:
        session["history"] = []

    history = session["history"]
    history.append({"role": "user", "content": user_message})

    try:
        gemini_history = []
        for msg in history[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            ))
        response = gemini_client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=gemini_history + [types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            )],
            config=types.GenerateContentConfig(
                system_instruction=get_system_prompt(),
                max_output_tokens=1024
            )
        )
        assistant_message = response.text
        history.append({"role": "assistant", "content": assistant_message})
        session["history"] = history
        session.modified = True
        return jsonify({"response": assistant_message})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/clear", methods=["POST"])
@login_required
def clear_chat():
    session["history"] = []
    return jsonify({"status": "cleared"})


# ── PDF Routes ──────────────────────────────────────────────

@app.route("/upload-pdf", methods=["POST"])
@login_required
def upload_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["pdf"]
    if not file.filename.endswith(".pdf"):
        return jsonify({"error": "Only PDF files allowed"}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    try:
        reader = PdfReader(filepath)
        text = "".join(p.extract_text() + "\n" for p in reader.pages)
        session["pdf_context"] = text[:15000]
        session["pdf_name"] = filename
        session.modified = True
        return jsonify({"success": True, "filename": filename, "pages": len(reader.pages)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/remove-pdf", methods=["POST"])
@login_required
def remove_pdf():
    session.pop("pdf_context", None)
    session.pop("pdf_name", None)
    session.modified = True
    return jsonify({"status": "removed"})


# ── Chat Log Routes ─────────────────────────────────────────

@app.route("/save-log", methods=["POST"])
@login_required
def save_log():
    history = session.get("history", [])
    if not history:
        return jsonify({"error": "No messages to save"}), 400
    data = request.get_json() or {}
    title = data.get("title", f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    save_chat_log(session["username"], title, json.dumps(history))
    threading.Thread(target=notify_chat_saved,
                     args=(session["username"], title, len(history)),
                     daemon=True).start()
    return jsonify({"success": True})


@app.route("/my-logs")
@login_required
def my_logs():
    logs = get_user_logs(session["username"])
    return jsonify({"logs": logs})


@app.route("/load-log/<int:log_id>")
@login_required
def load_log(log_id):
    log = get_log_by_id(log_id, session["username"])
    if not log:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"messages": json.loads(log["messages"]), "title": log["title"]})


@app.route("/download-log/<int:log_id>")
@login_required
def download_log(log_id):
    fmt = request.args.get("format", "json")
    log = get_log_by_id(log_id, session["username"])
    if not log:
        return "Not found", 404
    messages = json.loads(log["messages"])
    if fmt == "pdf":
        buffer = generate_pdf(log["title"], messages, log["created_at"])
        return send_file(buffer, as_attachment=True,
                         download_name=f"chat_{log_id}.pdf",
                         mimetype="application/pdf")
    content = json.dumps(messages, indent=2)
    buffer = io.BytesIO(content.encode("utf-8"))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"chat_{log_id}.json",
                     mimetype="application/json")


@app.route("/delete-log/<int:log_id>", methods=["DELETE"])
@login_required
def delete_log_route(log_id):
    delete_log(log_id, session["username"])
    return jsonify({"success": True})


# ── Admin Routes ────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin.html", username=session["username"])


@app.route("/admin/stats")
@admin_required
def admin_stats():
    return jsonify(get_stats())


@app.route("/admin/users")
@admin_required
def admin_users():
    return jsonify({"users": get_all_users()})


@app.route("/admin/logs")
@admin_required
def admin_logs():
    return jsonify({"logs": get_all_logs()})


@app.route("/admin/delete-user/<username>", methods=["DELETE"])
@admin_required
def admin_delete_user(username):
    if username == "admin":
        return jsonify({"error": "Cannot delete admin"}), 400
    delete_user(username)
    return jsonify({"success": True})


@app.route("/admin/delete-log/<int:log_id>", methods=["DELETE"])
@admin_required
def admin_delete_log(log_id):
    delete_log(log_id)
    return jsonify({"success": True})


@app.route("/admin/download-log/<int:log_id>")
@admin_required
def admin_download_log(log_id):
    fmt = request.args.get("format", "json")
    log = get_log_by_id(log_id)
    if not log:
        return "Not found", 404
    messages = json.loads(log["messages"])
    if fmt == "pdf":
        buffer = generate_pdf(log["title"], messages, log["created_at"])
        return send_file(buffer, as_attachment=True,
                         download_name=f"chat_{log_id}.pdf",
                         mimetype="application/pdf")
    content = json.dumps(messages, indent=2)
    buffer = io.BytesIO(content.encode("utf-8"))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"chat_{log_id}.json",
                     mimetype="application/json")


init_db()

if __name__ == "__main__":
    app.run(debug=True)
