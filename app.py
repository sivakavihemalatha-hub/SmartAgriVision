from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime

import numpy as np
from PIL import Image
import tensorflow as tf

app = Flask(__name__)
app.secret_key = "secret_key"

# ================= PATH SETTINGS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "database.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= LOAD MODEL =================
# ================= LOAD MODEL =================
MODEL_PATH = os.path.join(BASE_DIR, "best_model.h5")

model = None  # IMPORTANT: prevents white page crash

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
    print("❌ Model loading failed:", str(e))
    model = None

class_names = ['Anthracnose', 'Black Pox', 'Black Rot', 'Healthy', 'Powdery Mildew']

# ================= INIT DB =================
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


# ================= SIGNUP (AUTO LOGIN FIX) =================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            return "Fill all fields"

        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            cur.execute(
                "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
                (email, password, "user")
            )

            conn.commit()
            conn.close()

            # ✅ AUTO LOGIN
            session["user_id"] = email
            session["role"] = "user"

            return redirect("/dashboard")

        except sqlite3.IntegrityError:
            return "Email already exists"

    return render_template("signup.html")


# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        error=session.pop("error", None),
        image=session.pop("image", None),
        prediction=session.pop("prediction", None),
        confidence=session.pop("confidence", None),
        prevention=session.pop("prevention", None)
    )


# ================= UPLOAD + PREDICT =================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "user_id" not in session:
            return redirect("/login")

        # ✅ CHECK FILE
        file = request.files.get("file")

        if not file or file.filename == "":
            session["error"] = "Please select an image"
            return redirect("/dashboard")

        # ✅ ENSURE FOLDER EXISTS (VERY IMPORTANT FOR RENDER)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

        # ✅ SAVE FILE
        filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + file.filename
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # ✅ IMAGE PROCESSING
        img = Image.open(filepath).convert("RGB")
        img = img.resize((224, 224))
        img = np.array(img) / 255.0
        img = np.expand_dims(img, axis=0)

        # ✅ MODEL PREDICTION
        preds = model.predict(img)
        preds = preds[0]

        idx = np.argmax(preds)
        prediction = class_names[idx]
        confidence = str(round(float(np.max(preds)) * 100, 2)) + "%"

        # ✅ PREVENTION
        prevention_dict = {
            "Anthracnose": "Remove infected parts and use fungicide.",
            "Black Pox": "Apply fungicide regularly.",
            "Black Rot": "Prune affected areas.",
            "Healthy": "No disease detected.",
            "Powdery Mildew": "Use sulfur spray."
        }

        prevention = prevention_dict.get(prediction, "No advice")

        db_image_path = "static/uploads/" + filename

        # ✅ DATABASE SAVE
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

        # ✅ STORE RESULTS IN SESSION
        session["image"] = db_image_path
        session["prediction"] = prediction
        session["confidence"] = confidence
        session["prevention"] = prevention

        return redirect("/dashboard")

    except Exception as e:
        session["error"] = str(e)
        return redirect("/dashboard")
# ================= HISTORY =================
@app.route("/history")
def history():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM history WHERE username=?", (session["user_id"],))
    rows = cur.fetchall()

    conn.close()

    return render_template("history.html", history=rows)


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


# ================= PROFILE =================
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    email = session["user_id"]
    username = email.split("@")[0]

    return render_template(
        "profile.html",
        username=username,
        email=email,
        profile_pic=session.get("profile_pic")
    )


# ================= PROFILE UPLOAD =================
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


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
