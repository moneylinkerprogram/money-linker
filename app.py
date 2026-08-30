from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import random
import smtplib
import string
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- UPLOAD FOLDER CONFIGURATION ---
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"









SMTP_PORT = 587
SENDER_EMAIL = "kenmurimi127@gmail.com"
SENDER_PASSWORD = "xlsoarccekvebmph"  # App password with spaces removed


def send_email_to_user(recipient_email, reset_code):
  try:
    print(f"DEBUG: Sending reset code {reset_code} to {recipient_email}")

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg["Subject"] = "Money Linker - Password Reset Code"

    body = (
        f"Hello,\n\nYour password reset code is: {reset_code}\n\nIf you did"
        " not request this, please ignore this email.\n\nBest regards,\nMoney"
        " Linker Team"
    )
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
    server.quit()
    print("DEBUG: Email sent successfully!")
    return True
  except Exception as e:
    print(f"Error sending email: {e}")
    return False






#ken database

import random
import string
import sqlite3


def init_db():
  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()

  # Users table (with balance tracking for earnings)
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

  # Videos table for Admin Panel (supports both links and uploaded files)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            video_type TEXT,
            video_source TEXT,
            duration TEXT
        )
    """)

  # Track watched videos per user daily (limit 4 videos/day)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_watched_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            video_id INTEGER,
            watched_date TEXT
        )
    """)

  # Deposit requests table for admin verification
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS deposit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            mpesa_code TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

  # Withdrawal requests table for Tuesday/Friday payouts
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS withdrawal_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            phone TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)

  conn.commit()
  conn.close()













# Initialize the database tables on startup
init_db()


def generate_unique_code():



  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  while True:
    code = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    cursor.execute("SELECT * FROM users WHERE referral_code = ?", (code,))
    if not cursor.fetchone():
      conn.close()
      return code






    # install as an app files

@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js")






@app.route("/")
def home():
  if "user" not in session:
    return redirect(url_for("login"))

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM users WHERE email = ?", (session["user"],))
  user = cursor.fetchone()

  cursor.execute("SELECT * FROM videos ORDER BY id DESC")
  videos = cursor.fetchall()
  conn.close()

  return render_template("index.html", user=user, videos=videos)



            #PROFILE


@app.route("/profile", methods=["GET", "POST"])
def profile():
  if "user" not in session:
    return redirect(url_for("login"))

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM users WHERE email = ?", (session["user"],))
  user = cursor.fetchone()

  if not user:
    conn.close()
    return redirect(url_for("login"))

  my_ref_code = user[4]

  # Count how many people used this user's referral code
  cursor.execute(
      "SELECT COUNT(*) FROM users WHERE referred_by = ?", (my_ref_code,)
  )
  ref_count = cursor.fetchone()[0]
  conn.close()

  if request.method == "POST":
    report_message = request.form.get("report_message")
    user_email = user[1]
    user_phone = user[2]

    try:
      msg = MIMEMultipart()
      msg["From"] = SENDER_EMAIL
      msg["To"] = "kenmurimi127@gmail.com"
      msg["Subject"] = f"Money Linker Support Report from {user_email}"

      body = (
          f"New Report Received:\n\nUser Email: {user_email}\nPhone:"
          f" {user_phone}\n\nReport Details:\n{report_message}"
      )
      msg.attach(MIMEText(body, "plain"))

      server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
      server.starttls()
      server.login(SENDER_EMAIL, SENDER_PASSWORD)
      server.sendmail(SENDER_EMAIL, "kenmurimi127@gmail.com", msg.as_string())
      server.quit()
      flash("Your report has been sent successfully!", "success")
    except Exception as e:
      flash(f"Failed to send report: {e}", "danger")

    return redirect(url_for("profile"))

  return render_template("profile.html", user=user, ref_count=ref_count)




# Simple Admin Protection (Change credentials as needed)



             #ADMIN



# Separate Admin Credentials
ADMIN_EMAIL = "kenmurimi127@gmail.com"
ADMIN_PASSWORD = "Kenny123"


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


@app.route("/admin/dashboard")
def admin_dashboard():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute("SELECT COUNT(*) FROM users")
  user_count = cursor.fetchone()[0]

  cursor.execute("SELECT COUNT(*) FROM videos")
  video_count = cursor.fetchone()[0]
  conn.close()

  return render_template(
      "admin_dashboard.html", user_count=user_count, video_count=video_count
  )




import os

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/admin/add-video", methods=["GET", "POST"])
def admin_add_video():
  # Check if admin is logged in
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  if request.method == "POST":
    title = request.form.get("title")
    video_type = request.form.get(
        "video_type"
    )  # e.g., 'file' or 'link' (if you have options)
    duration = request.form.get("duration")

    video_source_value = ""

    if video_type == "link":
      # If it's an external link (like YouTube)
      video_source_value = request.form.get("video_link")
    else:
      # --- PUT YOUR FILE UPLOAD CODE HERE ---
      file = request.files.get("video_file")
      if file:
        filename = file.filename
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        video_source_value = filename  # Save the filename to use in database

    # Save everything into your database
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO videos (title, video_type, video_source, duration) VALUES"
        " (?, ?, ?, ?)",
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

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()

  if request.method == "POST":
    title = request.form.get("title")
    duration = request.form.get("duration")
    upload_method = request.form.get("upload_method")  # 'link' or 'file'

    video_source = ""

    if upload_method == "link":
      video_source = request.form.get("video_url")
    elif upload_method == "file":
      file = request.files.get("video_file")
      if file and file.filename != "":
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        video_source = filename  # Store just the filename

    cursor.execute(
        "INSERT INTO videos (title, video_type, video_source, duration) VALUES"
        " (?, ?, ?, ?)",
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
  # Use the independent admin session check
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
  conn.commit()
  conn.close()
  flash("Video deleted successfully!", "success")
  return redirect(url_for("admin_videos"))


# --- ADD THESE MISSING ADMIN MANAGEMENT ROUTES ---

            #admin user dashboard
@app.route("/admin/users")
def admin_users():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM users ORDER BY id DESC")
  users = cursor.fetchall()
  conn.close()
  return render_template("admin_users.html", users=users)



       #REQUEST


@app.route("/admin/requests", methods=["GET", "POST"])
def admin_requests():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":
        req_id = request.form.get("request_id")
        req_type = request.form.get("req_type")  # 'deposit' or 'withdrawal'
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
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (actual_amount, user_id))
                        cursor.execute("UPDATE deposit_requests SET status = 'Approved', amount = ? WHERE id = ?", (actual_amount, req_id))
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
                        # Deduct balance from user when admin confirms the payout
                        cursor.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (actual_amount, user_id))
                        cursor.execute("UPDATE withdrawal_requests SET status = 'Approved', amount = ? WHERE id = ?", (actual_amount, req_id))
                        conn.commit()
                except Exception as e:
                    print("Error approving withdrawal:", e)

    # Fetch Deposit Requests safely
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

    # Fetch Withdrawal Requests safely
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











             #adminb  approve deposit
@app.route("/admin/approve-deposit/<int:request_id>", methods=["POST"])
def approve_deposit(request_id):
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # 1. Get the deposit request details (user_id and amount)
    cursor.execute("SELECT user_id, amount, status FROM deposit_requests WHERE id = ?", (request_id,))
    dep = cursor.fetchone()

    if dep and dep[2] == 'Pending':
        user_id = dep[0]
        amount = dep[1]

        # 2. Add amount to user's balance
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))

        # 3. Update deposit request status to Approved
        cursor.execute("UPDATE deposit_requests SET status = 'Approved' WHERE id = ?", (request_id,))
        
        conn.commit()

    conn.close()
    return redirect(url_for("admin_requests"))






                #REPORYS

@app.route("/admin/reports")
def admin_reports():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  try:
    cursor.execute("SELECT * FROM reports ORDER BY id DESC")
    reports = cursor.fetchall()
  except sqlite3.OperationalError:
    reports = []
  conn.close()
  return render_template("admin_reports.html", reports=reports)




@app.route("/admin/wipe-all-videos")
def wipe_all_videos():
  if not session.get("admin_logged"):
    return redirect(url_for("admin_login"))

  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM videos")
  conn.commit()
  conn.close()

  flash("All sample videos wiped successfully!", "success")
  return redirect(url_for("admin_dashboard"))


         #DEPOSIT

@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Automatically create the deposit_requests table if it doesn't exist yet
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deposit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            mpesa_code TEXT,
            status TEXT
        )
    """)
    conn.commit()

    # Get user id
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

        # Save deposit request to the tracking table
        cursor.execute(
            "INSERT INTO deposit_requests (user_id, amount, mpesa_code, status) VALUES (?, ?, ?, 'Pending')",
            (user_id, amount, mpesa_code)
        )
        conn.commit()
        success_msg = "Deposit submitted successfully! Awaiting moderator verification."

    conn.close()
    return render_template("deposit.html", success_msg=success_msg)


                  #withraw

                  #withraw
 
@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if "user" not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get user id and balance using session["user"] (matches login logic)
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
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get user_id safely from session
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








            #ACCOUNT

@app.route("/account")
def account():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT balance FROM users WHERE email = ? OR phone = ?",
        (session["user"], session["user"]),
    )
    user = cursor.fetchone()
    conn.close()

    balance = user[0] if user else 0.0
    return render_template("account.html", balance=balance)






# inv3st and grow 

@app.route("/invest")
def invest():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT balance FROM users WHERE email = ? OR phone = ?",
        (session["user"], session["user"]),
    )
    user = cursor.fetchone()
    conn.close()

    balance = user[0] if user else 0.0
    return render_template("invest.html", balance=balance)






#login


@app.route("/login", methods=["GET", "POST"])
def login():
  if request.method == "POST":
    action = request.form.get("action")

    # --- SIGN UP LOGIC ---
    if action == "signup":
      email = request.form.get("email")
      phone = request.form.get("phone")
      password = request.form.get("password")
      ref_code_input = request.form.get("referral_code")

      conn = sqlite3.connect("database.db")
      cursor = conn.cursor()

      # Check how many users exist in the database
      cursor.execute("SELECT COUNT(*) FROM users")
      user_count = cursor.fetchone()[0]

      referred_by = None

      if user_count > 0:
        # If users already exist, require a valid referral code
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
        # Very first user needs no code
        referred_by = "System"

      import random
      import string

      new_ref_code = "".join(
          random.choices(string.ascii_uppercase + string.digits, k=6)
      )

      try:
        cursor.execute(
            "INSERT INTO users (email, phone, password, referral_code,"
            " referred_by) VALUES (?, ?, ?, ?, ?)",
            (email, phone, password, new_ref_code, referred_by),
        )
        conn.commit()
        conn.close()
        flash("Account created successfully! Please sign in.", "success")
      except sqlite3.IntegrityError:
        conn.close()
        flash("Email or Phone number already registered.", "danger")

      return redirect(url_for("login"))

    # --- SIGN IN LOGIC ---
    elif action == "signin":
      identifier = request.form.get("identifier")
      password = request.form.get("password")

      conn = sqlite3.connect("database.db")
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




         #MY VIDEOS(IKO IN USER)


import datetime
import random

@app.route("/my-videos")
def my_videos():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get current user ID and balance
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

    today_str = datetime.date.today().isoformat()

    # 1. Get all videos from database
    cursor.execute("SELECT * FROM videos")
    all_videos = cursor.fetchall()

    if all_videos:
        seed_val = int(datetime.date.today().strftime("%Y%m%d")) + user_id
        random.seed(seed_val)
        daily_selection = random.sample(all_videos, min(len(all_videos), 4))
    else:
        daily_selection = []

    # 2. Check watched status
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
        total_deposited=total_deposited  # <-- Add this line
    )










      # COMPLETION OF VIDEIS

import datetime
import sqlite3
from flask import jsonify, session

@app.route("/complete-video/<int:video_id>", methods=["POST"])
def complete_video(video_id):
    if "user" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    try:
        conn = sqlite3.connect("database.db")
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

        # Check if already watched today for reward
        cursor.execute(
            "SELECT * FROM user_watched_videos WHERE user_id = ? AND video_id = ? AND watched_date = ?",
            (user_id, video_id, today_str),
        )
        already_watched = cursor.fetchone()

        if not already_watched:
            # Mark as watched for earnings today
            cursor.execute(
                "INSERT INTO user_watched_videos (user_id, video_id, watched_date) VALUES (?, ?, ?)",
                (user_id, video_id, today_str),
            )
            # Add 5 Ksh reward
            cursor.execute(
                "UPDATE users SET balance = balance + 5.0 WHERE id = ?", (user_id,)
            )
            conn.commit()

            # Get the newly updated balance to send back to frontend
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





          #FORGET PASSWORD


@app.route("/forgot", methods=["POST"])
def forgot_password():
  email = request.form.get("reset_email")
  conn = sqlite3.connect("database.db")
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
  user = cursor.fetchone()
  conn.close()

  if user:
    # Generate 4-digit code
    reset_code = "".join(random.choices(string.digits, k=4))
    session["reset_email"] = email
    session["reset_code"] = reset_code

    # Send real email to user's Gmail
    email_sent = send_email_to_user(email, reset_code)

    if email_sent:
      flash(
          f"Reset code successfully sent to {email}. Check your inbox!",
          "success",
      )
      return render_template("login.html", show_reset_box=True)
    else:
      flash("Failed to send email. Check your SMTP configurations.", "danger")
  else:
    flash("Email not found in database.", "danger")

  return redirect(url_for("login"))



              #RESET PASSWORD

@app.route("/reset-password", methods=["POST"])
def reset_password():
  entered_code = request.form.get("reset_code")
  new_password = request.form.get("new_password")

  if "reset_code" in session and entered_code == session.get("reset_code"):
    email = session.get("reset_email")
    conn = sqlite3.connect("database.db")
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
         

               #LOGOUT

@app.route("/logout")
def logout():
  session.pop("user", None)
  return redirect(url_for("login"))


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000, debug=True)
