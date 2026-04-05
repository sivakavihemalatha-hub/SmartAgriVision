from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime

# 🔥 MODEL IMPORTS
import numpy as np
from PIL import Image
import tensorflow as tf

app = Flask(__name__)
app.secret_key = "secret_key"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 🔥 LOAD MODEL (FIXED - LAZY LOADING)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "best_model.h5")

model = None

def load_model_once():
    global model
    if model is None:
        model = tf.keras.models.load_model(MODEL_PATH, compile=False)

class_names = ['Anthracnose', 'Black Pox', 'Black Rot', 'Healthy', 'Powdery Mildew']


# ---------------- INIT DATABASE ----------------
def init_db():
    conn = sqlite3.connect("database.db")
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

    # 🔥 ADMIN INSERT
    cur.execute("SELECT * FROM users WHERE email=?", ("admin@gmail.com",))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (email, password, role)
            VALUES (?, ?, ?)
        """, ("admin@gmail.com", "admin@123", "admin"))

    conn.commit()
    conn.close()


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("SELECT email, role FROM users WHERE email=? AND password=?",
                    (email, password))
        user = cur.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[1]

            return redirect("/dashboard")

        return "Invalid credentials"

    return render_template("login.html")


# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users (email, password, role)
            VALUES (?, ?, ?)
        """, (email, password, "user"))

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html")


# ---------------- UPLOAD & PREDICT ----------------
@app.route("/upload", methods=["POST"])
def upload():
    if "user_id" not in session:
        return redirect("/login")

    file = request.files["file"]

    if file.filename == "":
        return redirect("/dashboard")

    filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + file.filename
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # 🔥 MODEL PREDICTION
    load_model_once()   # ✅ FIX ADDED

    img = Image.open(filepath).convert("RGB")
    img = img.resize((224,224))
    img = np.array(img) / 255.0
    img = np.expand_dims(img, axis=0)

    preds = model.predict(img)[0]
    idx = np.argmax(preds)

    prediction = class_names[idx]
    confidence = str(round(float(np.max(preds))*100, 2)) + "%"

    prevention_dict = {
        "Anthracnose": "Remove infected parts and use fungicide.",
        "Black Pox": "Apply fungicide regularly.",
        "Black Rot": "Prune affected areas.",
        "Healthy": "No disease detected.",
        "Powdery Mildew": "Use sulfur spray."
    }

    prevention = prevention_dict[prediction]

    # 🔥 SAVE HISTORY
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO history (username, image, prediction, confidence, date)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        filepath,
        prediction,
        confidence,
        str(datetime.now())
    ))

    conn.commit()
    conn.close()

    return render_template(
        "dashboard.html",
        image=filepath,
        prediction=prediction,
        confidence=confidence,
        prevention=prevention
    )


# ---------------- USER HISTORY ----------------
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM history WHERE username=?", (session["user_id"],))
    rows = cur.fetchall()

    conn.close()

    return render_template("history.html", history=rows)


# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect("/login")

    if session["role"] != "admin":
        return redirect("/dashboard")

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM history")
    rows = cur.fetchall()

    conn.close()

    return render_template("all_history.html", data=rows)


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    if "user_id" not in session:
        return redirect("/login")

    if session["role"] != "admin":
        return redirect("/dashboard")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM history WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")


# ---------------- PROFILE ----------------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "profile.html",
        username=session["user_id"],
        email=session["user_id"],
        profile_pic=session.get("profile_pic")
    )


@app.route("/upload_profile", methods=["POST"])
def upload_profile():
    if "user_id" not in session:
        return redirect("/login")

    file = request.files["photo"]

    if file.filename == "":
        return redirect("/profile")

    filename = "profile_" + session["user_id"] + ".jpg"
    filepath = os.path.join("static/uploads", filename)
    file.save(filepath)

    session["profile_pic"] = filepath

    return redirect("/profile")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
