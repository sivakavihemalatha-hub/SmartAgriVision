from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import os
from datetime import datetime
import numpy as np
import tensorflow as tf
from PIL import Image
from threading import Thread
from pyngrok import ngrok

# ================= APP =================
app = Flask(__name__)
app.secret_key = "secret_key"

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= CLASS NAMES =================
class_names = [
    "Anthracnose",
    "Black Pox",
    "Black Rot",
    "Healthy",
    "Powdery Mildew"
]

# ================= MODEL LOAD =================
MODEL_PATH = "/content/drive/MyDrive/best_model.keras"
model = tf.keras.models.load_model(MODEL_PATH, compile=False)
print("Model loaded successfully")

# ================= DB INIT =================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            image TEXT,
            prediction TEXT,
            confidence TEXT,
            date TEXT
        )
    """)

    # default admin
    cur.execute("SELECT * FROM users WHERE email=?", ("admin@gmail.com",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
            ("admin@gmail.com", "admin@123", "admin")
        )

    conn.commit()
    conn.close()

init_db()

# ================= HOME =================
@app.route("/")
def home():
    return render_template("home.html")

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("SELECT email, role FROM users WHERE email=? AND password=?", (email, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[1]
            return redirect("/dashboard")

        return "Invalid credentials"

    return render_template("login.html")

# ================= SIGNUP =================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # prevent duplicate users
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        if cur.fetchone():
            conn.close()
            return "User already exists"

        cur.execute(
            "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
            (email, password, "user")
        )

        conn.commit()
        conn.close()

        # ✅ AUTO LOGIN FIX
        session["user_id"] = email
        session["role"] = "user"
        return redirect("/dashboard")

    return render_template("signup.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ✅ GET ONLY CURRENT USER LAST RESULT
    cur.execute("""
        SELECT image, prediction, confidence
        FROM history
        WHERE username=?
        ORDER BY id DESC
        LIMIT 1
    """, (session["user_id"],))

    last = cur.fetchone()
    conn.close()

    if last:
        image, prediction, confidence = last
    else:
        image = prediction = confidence = None

    # ✅ PREVENTION FIX (IMPORTANT PART)
    prevention_dict = {
        "Anthracnose": "Remove infected parts and use fungicide.",
        "Black Pox": "Apply fungicide regularly.",
        "Black Rot": "Prune affected areas.",
        "Healthy": "No disease detected.",
        "Powdery Mildew": "Use sulfur spray."
    }

    prevention = None
    if prediction:
        prevention = prevention_dict.get(prediction)

    return render_template(
        "dashboard.html",
        image=image,
        prediction=prediction,
        confidence=confidence,
        prevention=prevention
    )
# ================= UPLOAD + PREDICT =================
@app.route("/upload", methods=["POST"])
def upload():
    if "user_id" not in session:
        return redirect("/login")

    file = request.files.get("file")
    if not file or file.filename == "":
        return redirect("/dashboard")

    filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + file.filename
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    db_image_path = "static/uploads/" + filename

    from tensorflow.keras.applications.efficientnet import preprocess_input

    img = Image.open(filepath).resize((224, 224))
    img = np.array(img)
    img = preprocess_input(img)
    img = np.expand_dims(img, axis=0)

    pred = model.predict(img)
    class_index = np.argmax(pred)

    prediction = class_names[class_index]
    confidence = str(round(np.max(pred) * 100, 2)) + "%"

    prevention_dict = {
        "Anthracnose": "Remove infected parts and use fungicide.",
        "Black Pox": "Apply fungicide regularly.",
        "Black Rot": "Prune affected areas.",
        "Healthy": "No disease detected.",
        "Powdery Mildew": "Use sulfur spray."
    }

    prevention = prevention_dict[prediction]

    # ================= SAVE HISTORY =================
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO history (username, image, prediction, confidence, date)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        db_image_path,
        prediction,
        confidence,
        str(datetime.now())
    ))

    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ================= HISTORY =================
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM history WHERE username=? ORDER BY id DESC", (session["user_id"],))
    rows = cur.fetchall()

    conn.close()
    return render_template("history.html", history=rows)

# ================= PROFILE =================
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    email = session["user_id"]

    return render_template(
        "profile.html",
        username=email.split("@")[0],
        email=email,
        profile_pic=session.get("profile_pic")
    )

# ================= PROFILE UPLOAD =================
@app.route("/upload_profile", methods=["POST"])
def upload_profile():
    if "user_id" not in session:
        return redirect("/profile")

    file = request.files.get("photo")
    if not file or file.filename == "":
        return redirect("/profile")

    filename = "profile_" + session["user_id"] + ".jpg"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    session["profile_pic"] = "static/uploads/" + filename

    return redirect("/profile")

# ================= ADMIN =================
@app.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return redirect("/dashboard")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM history")
    rows = cur.fetchall()

    conn.close()
    return render_template("all_history.html", data=rows)

# ================= DELETE =================
@app.route("/delete/<int:id>")
def delete(id):
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return redirect("/dashboard")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM history WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ================= RUN + NGROK =================
ngrok.set_auth_token("3BfLgmilyOsnuhNXkHjRRzM3Br9_3ZxaFi6HXtDfELzCDbgnS")

public_url = ngrok.connect(5000)
print("🔥 OPEN THIS:", public_url)

def run():
    app.run(host="0.0.0.0", port=5000)

Thread(target=run).start()
