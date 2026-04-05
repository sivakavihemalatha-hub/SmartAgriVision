from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime

import numpy as np
from PIL import Image
import tensorflow as tf

app = Flask(__name__)
app.secret_key = "secret_key"

# ---------------- PATH FIX ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MODEL_PATH = os.path.join(BASE_DIR, "best_model.h5")

# ---------------- LOAD MODEL (FIXED ONLY HERE) ----------------
model = None

try:
    model = tf.keras.models.load_model(
        MODEL_PATH,
        compile=False,
        custom_objects={
            "Dense": lambda **kwargs: tf.keras.layers.Dense(
                **{k: v for k, v in kwargs.items() if k != "quantization_config"}
            )
        }
    )
    print("✅ Model loaded successfully")

except Exception as e:
    print("❌ Model loading failed:", e)
    model = None


# ---------------- CLASS LABELS ----------------
class_names = ['Anthracnose', 'Black Pox', 'Black Rot', 'Healthy', 'Powdery Mildew']


# ---------------- DATABASE INIT ----------------
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
            session["username"] = user[0]
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

    if model is None:
        return "Model not loaded"

    # IMAGE PROCESS
    img = Image.open(filepath).convert("RGB")
    img = img.resize((224, 224))
    img = np.array(img) / 255.0
    img = np.expand_dims(img, axis=0)

    img_tensor = tf.convert_to_tensor(img)
    preds = model(img_tensor, training=False).numpy()[0]

    idx = np.argmax(preds)

    prediction = class_names[idx]
    confidence = str(round(float(np.max(preds)) * 100, 2)) + "%"

    prevention_dict = {
        "Anthracnose": "Remove infected parts and use fungicide.",
        "Black Pox": "Apply fungicide regularly.",
        "Black Rot": "Prune affected areas.",
        "Healthy": "No disease detected.",
        "Powdery Mildew": "Use sulfur spray."
    }

    prevention = prevention_dict[prediction]

    db_image_path = "static/uploads/" + filename

    conn = sqlite3.connect("database.db")
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

    
    # session update
    session["image"] = db_image_path
    session["prediction"] = prediction
    session["confidence"] = confidence
    session["prevention"] = prevention

    # redirect
    return redirect("/dashboard")


# ---------------- HISTORY ----------------
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
        username=session["username"],
        email=session["user_id"],
        profile_pic=session.get("profile_pic")
    )


# ---------------- UPLOAD PROFILE ----------------
@app.route("/upload_profile", methods=["POST"])
def upload_profile():
    if "user_id" not in session:
        return redirect("/login")

    file = request.files["photo"]

    if file.filename == "":
        return redirect("/profile")

    filename = "profile_" + session["user_id"] + ".jpg"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    session["profile_pic"] = "static/uploads/" + filename

    return redirect("/profile")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- RUN ----------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
