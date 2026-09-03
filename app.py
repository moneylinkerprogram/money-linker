from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import random
import smtplib
import string
import sqlite3
import datetime
from flask import Flask, flash, redirect, render_template, request, session
import requests
import psycopg2
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- UPLOAD FOLDER CONFIGURATION ---
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- DATABASE CONFIGURATION (Supabase / Postgres or Local SQLite) ---
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if DATABASE_URL:
        parsed_url = urlparse(DATABASE_URL)
        return psycopg2.connect(
            database=parsed_url.path[1:],
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            port=parsed_url.port
        )
    else:
        return sqlite3.connect("database.db")

# --- DATABASE SETUP ON STARTUP ---
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    if DATABASE_URL:
        # PostgreSQL Schema (Supabase) - Uses SERIAL instead of AUTOINCREMENT
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE,
                phone TEXT,
                password TEXT,
                referral_code TEXT,
                referred_by TEXT,
                balance REAL DEFAULT 0.0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id SERIAL PRIMARY KEY,
                title TEXT,
                video_type TEXT,
                video_source TEXT,
                duration TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_watched_videos (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                video_id INTEGER,
                watched_date TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deposit_requests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                mpesa_code TEXT,
                status TEXT DEFAULT 'Pending'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                phone TEXT,
                status TEXT DEFAULT 'Pending'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                email TEXT,
                phone TEXT,
                message TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # Local SQLite Schema - Uses AUTOINCREMENT
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                phone TEXT,
                password TEXT,
                referral_code TEXT,
                referred_by TEXT,
                balance REAL DEFAULT 0.0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                video_type TEXT,
                video_source TEXT,
                duration TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_watched_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_id INTEGER,
                watched_date TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deposit_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                mpesa_code TEXT,
                status TEXT DEFAULT 'Pending'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                phone TEXT,
                status TEXT DEFAULT 'Pending'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT,
                phone TEXT,
                message TEXT,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    conn.close()

init_db()














# --- EMAIL CONFIGURATION (SMTP for Support Reports) ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "kenmurimi127@gmail.com"
SENDER_PASSWORD = "xlsoarccekvebmph"

# --- BREVO HTTP API EMAIL FUNCTION (For Password Resets) ---
def send_email_to_user(to_email, reset_code):
  url = "https://api.brevo.com/v3/smtp/email"
  api_key = os.environ.get("BREVO_API_KEY")

  print(
      f"DEBUG: Attempting to send email to {to_email} via Brevo. API Key loaded:"
      f" {bool(api_key)}"
  )

  payload = {
      "sender": {
          "name": "Money Linker",
          "email": "moneylinkerprogram@gmail.com",
      },
      "to": [{"email": to_email}],
      "subject": "Money Linker Password Reset Code",
      "textContent": (
          f"Hello,\n\nYour password reset code is: {reset_code}\n\nEnter this"
          " code on the website to reset your password."
      ),
  }

  headers = {
      "accept": "application/json",
      "api-key": api_key,
      "content-type": "application/json",
  }

  try:
    response = requests.post(url, json=payload, headers=headers, timeout=5)
    print(
        f"DEBUG: Brevo response status code: {response.status_code}, body:"
        f" {response.text}"
    )
    if response.status_code == 201:
      return True
    else:
      return False
  except Exception as e:
    print(f"DEBUG: Exception during Brevo request: {e}")
    return False


def generate_unique_code():
  conn = get_db_connection()
  cursor = conn.cursor()
  while True:
    code = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    cursor.execute("SELECT * FROM users WHERE referral_code = ?", (code,))
    if not cursor.fetchone():
      conn.close()
      return code


# --- APP FILES ---
@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js")


@app.route("/")
def home():
  if "user" not in session:
    return redirect(url_for("login"))

  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM users WHERE email = ?", (session["user"],))
  user = cursor.fetchone()

  cursor.execute("SELECT * FROM videos ORDER BY id DESC")
  videos = cursor.fetchall()
  conn.close()

  return render_template("index.html", user=user, videos=videos)


# --- PROFILE ---


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? OR phone = ?", (session["user"], session["user"]))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return redirect(url_for("login"))

    user_id = user[0]
    user_email = user[1]
    user_phone = user[2]
    my_ref_code = user[4]

    if request.method == "POST":
        report_message = request.form.get("report_message")
        
        if report_message:
            cursor.execute("""
                INSERT INTO reports (user_id, email, phone, message) 
                VALUES (?, ?, ?, ?)
            """, (user_id, user_email, user_phone, report_message))
            conn.commit()
            flash("Your report has been sent to the admin successfully!", "success")
        
        conn.close()
        return redirect(url_for("profile"))

    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE referred_by = ?", (my_ref_code,)
    )
    ref_count = cursor.fetchone()[0]
    conn.close()

    return render_template("profile.html", user=user, ref_count=ref_count)






# --- ADMIN CREDENTIALS ---
ADMIN_EMAIL = "kenmurimi101@gmail.com"
ADMIN_PASSWORD = "Km286720.!2840"


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
  if request.method == "POST":
    email = request.form.get("email")
    password = request.form.get("password")

    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
      session["admin_logged"] = True
      return redirect(url_for("admin_dashboard"))
    else:
      flash("Invalid Admin Login Details", "danger")

  return render_template("admin_login.html")


@app.route("/admin/debug-referrals")
def debug_referrals():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, referral_code, referred_by, balance FROM users")
    all_users = cursor.fetchall()
    
    cursor.execute("SELECT id, user_id, amount, status FROM deposit_requests")
    all_deposits = cursor.fetchall()
    conn.close()

    output = "<h2>Users Table:</h2><table border='1'><tr><th>ID</th><th>Email</th><th>Referral Code</th><th>Referred By</th><th>Balance</th></tr>"
    for u in all_users:
        output += f"<tr><td>{u[0]}</td><td>{u[1]}</td><td>{u[2]}</td><td>{u[3]}</td><td>{u[4]}</td></tr>"
    output += "</table>"

    output += "<h2>Deposit Requests Table:</h2><table border='1'><tr><th>ID</th><th>User ID</th><th>Amount</th><th>Status</th></tr>"
    for d in all_deposits:
        output += f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td></tr>"
    output += "</table>"

    return output










@app.route("/admin/dashboard")
def admin_dashboard():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT COUNT(*) FROM users")
  user_count = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(*) FROM videos")
  video_count = cursor.fetchone()[0]
  conn.close()

  return render_template(
      "admin_dashboard.html", user_count=user_count, video_count=video_count
  )


@app.route("/admin/add-video", methods=["GET", "POST"])
def admin_add_video():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  if request.method == "POST":
    title = request.form.get("title")
    video_type = request.form.get("video_type")
    duration = request.form.get("duration")

    video_source_value = ""

    if video_type == "link":
      video_source_value = request.form.get("video_link")
    else:
      file = request.files.get("video_file")
      if file:
        filename = file.filename
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        video_source_value = filename

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO videos (title, video_type, video_source, duration) VALUES (?, ?, ?, ?)",
        (title, video_type, video_source_value, duration),
    )
    conn.commit()
    conn.close()

    flash("Video added successfully!", "success")
    return redirect(url_for("admin_videos"))

  return render_template("admin_add_video.html")


@app.route("/admin/videos", methods=["GET", "POST"])
def admin_videos():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = get_db_connection()
  cursor = conn.cursor()

  if request.method == "POST":
    title = request.form.get("title")
    duration = request.form.get("duration")
    upload_method = request.form.get("upload_method")

    video_source = ""

    if upload_method == "link":
      video_source = request.form.get("video_url")
    elif upload_method == "file":
      file = request.files.get("video_file")
      if file and file.filename != "":
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        video_source = filename

    cursor.execute(
        "INSERT INTO videos (title, video_type, video_source, duration) VALUES (?, ?, ?, ?)",
        (title, upload_method, video_source, duration),
    )
    conn.commit()
    conn.close()
    flash("Video added successfully!", "success")
    return redirect(url_for("admin_videos"))

  cursor.execute("SELECT * FROM videos ORDER BY id DESC")
  videos = cursor.fetchall()
  conn.close()
  return render_template("admin_videos.html", videos=videos)


@app.route("/admin/logout")
def admin_logout():
  session.pop("admin_logged", None)
  return redirect(url_for("admin_login"))


@app.route("/admin/videos/delete/<int:video_id>")
def delete_video(video_id):
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
  conn.commit()
  conn.close()
  flash("Video deleted successfully!", "success")
  return redirect(url_for("admin_videos"))


@app.route("/admin/users")
def admin_users():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM users ORDER BY id DESC")
  users = cursor.fetchall()
  conn.close()
  return render_template("admin_users.html", users=users)


@app.route("/admin/requests", methods=["GET", "POST"])
def admin_requests():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        req_id = request.form.get("request_id")
        req_type = request.form.get("req_type")
        action = request.form.get("action")
        verified_amount = request.form.get("verified_amount")

        if req_type == "deposit":
            if action == "delete":
                cursor.execute("DELETE FROM deposit_requests WHERE id = ?", (req_id,))
                conn.commit()
            elif action == "approve":
                try:
                    actual_amount = float(verified_amount)
                    cursor.execute("SELECT user_id, status FROM deposit_requests WHERE id = ?", (req_id,))
                    row = cursor.fetchone()
                    if row and row[1] != 'Approved':
                        user_id = row[0]
                        # 1. Add deposit amount to user's balance
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (actual_amount, user_id))
                        cursor.execute("UPDATE deposit_requests SET status = 'Approved', amount = ? WHERE id = ?", (actual_amount, req_id))
                        
                        # 2. Check how many approved deposits this user has had
                        cursor.execute("""
                            SELECT COUNT(*) FROM deposit_requests 
                            WHERE user_id = ? AND status = 'Approved'
                        """, (user_id,))
                        approved_count = cursor.fetchone()[0]

                        # 3. If this is their first approved deposit and >= 100 Ksh, reward the referrer!
                        if approved_count == 1 and actual_amount >= 100:
                            cursor.execute("SELECT referred_by FROM users WHERE id = ?", (user_id,))
                            ref_row = cursor.fetchone()

                            if ref_row and ref_row[0]:
                                referrer_code = ref_row[0].strip()
                                if referrer_code and referrer_code != "System":
                                    cursor.execute("""
                                        UPDATE users SET balance = balance + 40 
                                        WHERE TRIM(referral_code) = ?
                                    """, (referrer_code,))

                        conn.commit()
                except Exception as e:
                    print("Error approving deposit:", e)

        elif req_type == "withdrawal":
            if action == "delete":
                cursor.execute("DELETE FROM withdrawal_requests WHERE id = ?", (req_id,))
                conn.commit()
            elif action == "approve":
                try:
                    actual_amount = float(verified_amount)
                    cursor.execute("SELECT user_id, status FROM withdrawal_requests WHERE id = ?", (req_id,))
                    row = cursor.fetchone()
                    if row and row[1] != 'Approved':
                        user_id = row[0]
                        cursor.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (actual_amount, user_id))
                        cursor.execute("UPDATE withdrawal_requests SET status = 'Approved', amount = ? WHERE id = ?", (actual_amount, req_id))
                        conn.commit()
                except Exception as e:
                    print("Error approving withdrawal:", e)

    try:
        cursor.execute("""
            SELECT deposit_requests.id, users.email, users.phone, deposit_requests.amount, deposit_requests.mpesa_code, deposit_requests.status
            FROM deposit_requests
            JOIN users ON deposit_requests.user_id = users.id
            ORDER BY deposit_requests.id DESC
        """)
        requests_list = cursor.fetchall()
    except sqlite3.OperationalError:
        requests_list = []

    try:
        cursor.execute("""
            SELECT withdrawal_requests.id, users.email, users.phone, withdrawal_requests.amount, withdrawal_requests.phone, withdrawal_requests.status
            FROM withdrawal_requests
            JOIN users ON withdrawal_requests.user_id = users.id
            ORDER BY withdrawal_requests.id DESC
        """)
        withdrawals_list = cursor.fetchall()
    except sqlite3.OperationalError:
        withdrawals_list = []

    conn.close()
    return render_template("admin_requests.html", requests_list=requests_list, withdrawals_list=withdrawals_list)







@app.route("/admin/approve-deposit/<int:deposit_id>", methods=["POST"])
def approve_deposit(deposit_id):
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get deposit details
    cursor.execute("SELECT user_id, amount, status FROM deposit_requests WHERE id = ?", (deposit_id,))
    dep = cursor.fetchone()

    if not dep:
        conn.close()
        return redirect(url_for("admin_dashboard"))

    user_id, amount, status = dep[0], dep[1], dep[2]

    if status != "Approved":
        # 1. Mark deposit as approved
        cursor.execute("UPDATE deposit_requests SET status = 'Approved' WHERE id = ?", (deposit_id,))

        # 2. Add deposit amount to the user's balance
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))

        # 3. Check how many approved deposits this user has had
        cursor.execute("""
            SELECT COUNT(*) FROM deposit_requests 
            WHERE user_id = ? AND status = 'Approved'
        """, (user_id,))
        approved_count = cursor.fetchone()[0]

        # 4. If this is their first approved deposit and >= 100 Ksh
        if approved_count == 1 and amount >= 100:
            cursor.execute("SELECT referred_by FROM users WHERE id = ?", (user_id,))
            ref_row = cursor.fetchone()

            if ref_row and ref_row[0]:
                referrer_code = ref_row[0].strip()
                
                # Make sure we don't try to look up "System" as a referral code user
                if referrer_code and referrer_code != "System":
                    # Credit 40 Ksh to the referrer
                    cursor.execute("""
                        UPDATE users SET balance = balance + 40 
                        WHERE TRIM(referral_code) = ?
                    """, (referrer_code,))

        conn.commit()

    conn.close()
    return redirect(url_for("admin_dashboard"))










@app.route("/admin/reports")
def admin_reports():
    # Check if the admin is logged in using the correct session variable
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, phone, message, date FROM reports ORDER BY id DESC")
    reports = cursor.fetchall()
    conn.close()

    return render_template("admin_reports.html", reports=reports)










@app.route("/admin/wipe-all-videos")
def wipe_all_videos():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = get_db_connection()
  cursor = conn.cursor()
  cursor.execute("DELETE FROM videos")
  conn.commit()
  conn.close()

  flash("All sample videos wiped successfully!", "success")
  return redirect(url_for("admin_dashboard"))


# --- DEPOSIT & WITHDRAWAL ---
@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email = ? OR phone = ?",
        (session["user"], session["user"]),
    )
    user = cursor.fetchone()
    if not user:
        conn.close()
        return redirect(url_for("login"))
    
    user_id = user[0]
    success_msg = None

    if request.method == "POST":
        amount = request.form.get("amount")
        mpesa_code = request.form.get("mpesa_code")

        cursor.execute(
            "INSERT INTO deposit_requests (user_id, amount, mpesa_code, status) VALUES (?, ?, ?, 'Pending')",
            (user_id, amount, mpesa_code)
        )
        conn.commit()
        success_msg = "Deposit submitted successfully! Awaiting moderator verification."

    conn.close()
    return render_template("deposit.html", success_msg=success_msg)


@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if "user" not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, balance FROM users WHERE email = ? OR phone = ?",
        (session["user"], session["user"]),
    )
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return redirect(url_for('login'))
        
    user_id = user_row[0]
    user_balance = user_row[1]

    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            phone = request.form.get('phone')
            
            if amount < 200:
                conn.close()
                return render_template('withdraw.html', error_msg="Minimum withdrawal amount is 200 Ksh.", pending_request=None)
            
            if amount > user_balance:
                conn.close()
                return render_template('withdraw.html', error_msg="Insufficient account balance.", pending_request=None)
            
            cursor.execute("""
                INSERT INTO withdrawal_requests (user_id, amount, phone, status)
                VALUES (?, ?, ?, 'Pending')
            """, (user_id, amount, phone))
            conn.commit()
        except Exception as e:
            print("Withdrawal error:", e)

    cursor.execute("SELECT id, amount, phone FROM withdrawal_requests WHERE user_id = ? AND status = 'Pending'", (user_id,))
    pending_request = cursor.fetchone()
    
    conn.close()
    return render_template('withdraw.html', pending_request=pending_request)






@app.route('/cancel-withdrawal', methods=['POST'])
def cancel_withdrawal():
    if "user" not in session:
        return redirect(url_for('login'))
        
    req_id = request.form.get('req_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id FROM users WHERE email = ? OR phone = ?",
        (session["user"], session["user"]),
    )
    user_row = cursor.fetchone()
    if user_row:
        user_id = user_row[0]
        cursor.execute("DELETE FROM withdrawal_requests WHERE id = ? AND user_id = ? AND status = 'Pending'", (req_id, user_id))
        conn.commit()
        
    conn.close()
    return redirect(url_for('withdraw'))


@app.route("/account")
def account():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT balance FROM users WHERE email = ? OR phone = ?",
        (session["user"], session["user"]),
    )
    user = cursor.fetchone()
    conn.close()

    balance = user[0] if user else 0.0
    return render_template("account.html", balance=balance)


@app.route("/invest")
def invest():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT balance FROM users WHERE email = ? OR phone = ?",
        (session["user"], session["user"]),
    )
    user = cursor.fetchone()
    conn.close()

    balance = user[0] if user else 0.0
    return render_template("invest.html", balance=balance)


# --- LOGIN / SIGNUP ---
@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    action = request.form.get("action")

    if action == "signup":
      email = request.form.get("email")
      phone = request.form.get("phone")
      password = request.form.get("password")
      ref_code_input = request.form.get("referral_code")

      conn = get_db_connection()
      cursor = conn.cursor()
      cursor.execute("SELECT COUNT(*) FROM users")
      user_count = cursor.fetchone()[0]

      referred_by = None
      if user_count > 0:
        cursor.execute(
            "SELECT * FROM users WHERE referral_code = ?", (ref_code_input,)
        )
        referrer = cursor.fetchone()
        if not referrer:
          conn.close()
          flash("Invalid referral code! Must use an existing code.", "danger")
          return redirect(url_for("login"))
        referred_by = ref_code_input
      else:
        referred_by = "System"

      new_ref_code = "".join(
          random.choices(string.ascii_uppercase + string.digits, k=6)
      )

      try:
        cursor.execute(
            "INSERT INTO users (email, phone, password, referral_code, referred_by) VALUES (?, ?, ?, ?, ?)",
            (email, phone, password, new_ref_code, referred_by),
        )
        conn.commit()
        conn.close()
        flash("Account created successfully! Please sign in.", "success")
      except sqlite3.IntegrityError:
        conn.close()
        flash("Email or Phone number already registered.", "danger")

      return redirect(url_for("login"))

    elif action == "signin":
      identifier = request.form.get("identifier")
      password = request.form.get("password")

      conn = get_db_connection()
      cursor = conn.cursor()
      cursor.execute(
          "SELECT * FROM users WHERE (email = ? OR phone = ?) AND password = ?",
          (identifier, identifier, password),
      )
      user = cursor.fetchone()
      conn.close()

      if user:
        session["user"] = user[1]
        return redirect(url_for("home"))
      else:
        flash("Invalid credentials, please check your details.", "danger")
        return redirect(url_for("login"))

  return render_template("login.html")


# --- MY VIDEOS ---

@app.route("/my-videos")
def my_videos():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, balance FROM users WHERE email = ? OR phone = ?",
        (session["user"], session["user"]),
    )
    user = cursor.fetchone()
    if not user:
        conn.close()
        return redirect(url_for("login"))

    user_id = user[0]
    user_balance = user[1]

    # Check total approved deposits for this user
    cursor.execute("""
        SELECT SUM(amount) FROM deposit_requests 
        WHERE user_id = ? AND status = 'Approved'
    """, (user_id,))
    dep_row = cursor.fetchone()
    total_deposited = dep_row[0] if dep_row and dep_row[0] else 0.0

    # Determine if user needs to make the one-time 100 Ksh deposit
    needs_deposit = total_deposited < 100

    today_str = datetime.date.today().isoformat()

    cursor.execute("SELECT * FROM videos")
    all_videos = cursor.fetchall()

    if all_videos:
        seed_val = int(datetime.date.today().strftime("%Y%m%d")) + user_id
        random.seed(seed_val)
        daily_selection = random.sample(all_videos, min(len(all_videos), 4))
    else:
        daily_selection = []

    cursor.execute(
        "SELECT video_id FROM user_watched_videos WHERE user_id = ? AND watched_date = ?",
        (user_id, today_str),
    )
    watched_rows = cursor.fetchall()
    watched_video_ids = [row[0] for row in watched_rows]

    videos_with_status = []
    for v in daily_selection:
        v_id = v[0]
        is_watched = v_id in watched_video_ids
        videos_with_status.append(
            {
                "id": v_id,
                "title": v[1],
                "video_type": v[2],
                "video_source": v[3],
                "duration": v[4],
                "is_watched": is_watched,
            }
        )

    conn.close()
    return render_template(
        "my_videos.html", 
        videos=videos_with_status, 
        balance=user_balance,
        total_deposited=total_deposited,
        needs_deposit=needs_deposit
    )








@app.route("/complete-video/<int:video_id>", methods=["POST"])
def complete_video(video_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email = ? OR phone = ?",
            (session["user"], session["user"]),
        )
        user = cursor.fetchone()
        if not user:
            conn.close()
            return jsonify({"success": False, "message": "User not found"}), 404

        user_id = user[0]
        today_str = datetime.date.today().isoformat()

        cursor.execute(
            "SELECT * FROM user_watched_videos WHERE user_id = ? AND video_id = ? AND watched_date = ?",
            (user_id, video_id, today_str),
        )
        already_watched = cursor.fetchone()

        if not already_watched:
            cursor.execute(
                "INSERT INTO user_watched_videos (user_id, video_id, watched_date) VALUES (?, ?, ?)",
                (user_id, video_id, today_str),
            )
            cursor.execute(
                "UPDATE users SET balance = balance + 5.0 WHERE id = ?", (user_id,)
            )
            conn.commit()

            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            updated_user = cursor.fetchone()
            new_balance = updated_user[0] if updated_user else 0

            conn.close()
            return jsonify({"success": True, "message": "Earned 5 Ksh!", "new_balance": new_balance})

        conn.close()
        return jsonify(
            {"success": False, "message": "Reward already claimed for today"}
        )

    except Exception as e:
        print(f"Error in complete_video: {e}")
        return jsonify({"success": False, "message": "Server error occurred"}), 500


# --- FORGOT PASSWORD ---
@app.route("/forgot", methods=["GET", "POST"])
def forgot_password():
  if request.method == "GET":
    return redirect(url_for("login"))

  try:
    email = request.form.get("reset_email")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user:
      reset_code = "".join(random.choices(string.digits, k=4))
      session["reset_email"] = email
      session["reset_code"] = reset_code

      try:
        email_sent = send_email_to_user(email, reset_code)
      except Exception:
        email_sent = False

      if email_sent:
        flash(f"Reset code successfully sent to {email}.", "success")
      else:
        flash(f"Debug Reset Code (SMTP Restricted): {reset_code}", "warning")
        
      return render_template("login.html", show_reset_box=True)
    else:
      flash("Email not found in database.", "danger")
  except Exception as e:
    print(f"Forgot password error: {e}")
    flash("An error occurred processing your request.", "danger")

  return redirect(url_for("login"))


# --- RESET PASSWORD ---
@app.route("/reset-password", methods=["POST"])
def reset_password():
  entered_code = request.form.get("reset_code")
  new_password = request.form.get("new_password")

  if "reset_code" in session and entered_code == session.get("reset_code"):
    email = session.get("reset_email")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password = ? WHERE email = ?", (new_password, email)
    )
    conn.commit()
    conn.close()

    session.pop("reset_code", None)
    session.pop("reset_email", None)

    flash("Password successfully reset! Please sign in.", "success")
    return redirect(url_for("login"))
  else:
    flash("Invalid reset code. Please try again.", "danger")
    return render_template("login.html", show_reset_box=True)


# --- LOGOUT ---
@app.route("/logout")
def logout():
  session.pop("user", None)
  return redirect(url_for("login"))




if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
