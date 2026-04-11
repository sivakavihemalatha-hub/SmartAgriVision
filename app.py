from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime

import numpy as np
from PIL import Image
import tflite_runtime.interpreter as tflite   # ✅ CHANGED

app = Flask(__name__)
app.secret_key = "secret_key"

# ================= PATH SETTINGS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "database.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ================= LOAD TFLITE MODEL =================
MODEL_PATH = os.path.join(BASE_DIR, "model.tflite")

interpreter = tflite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("✅ TFLite model loaded")

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
        prediction=None,
        confidence=None,
        prevention=None,
        image=None
    )

# ================= UPLOAD + PREDICT =================
@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "user_id" not in session:
            return redirect("/login")

        if "file" not in request.files:
            return redirect("/dashboard")

        file = request.files["file"]

        if file.filename == "":
            return redirect("/dashboard")

        # ✅ IMAGE PROCESS
        img = Image.open(file).convert("RGB")
        img = img.resize((224, 224))

        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0).astype("float32")

        # ✅ TFLITE PREDICTION
        interpreter.set_tensor(input_details[0]['index'], img_array)
        interpreter.invoke()
        preds = interpreter.get_tensor(output_details[0]['index'])

        idx = np.argmax(preds[0])
        prediction = class_names[idx]
        confidence = str(round(float(np.max(preds)) * 100, 2)) + "%"

        prevention_dict = {
            "Anthracnose": "Remove infected parts and use fungicide.",
            "Black Pox": "Apply fungicide regularly.",
            "Black Rot": "Prune affected areas.",
            "Healthy": "No disease detected.",
            "Powdery Mildew": "Use sulfur spray."
        }

        prevention = prevention_dict.get(prediction, "No advice")

        # ✅ SAVE IMAGE
        filename = datetime.now().strftime("%Y%m%d%H%M%S") + ".jpg"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        img.save(filepath)

        return render_template(
            "dashboard.html",
            image="static/uploads/" + filename,
            prediction=prediction,
            confidence=confidence,
            prevention=prevention
        )

    except Exception as e:
        return f"ERROR: {str(e)}"

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
