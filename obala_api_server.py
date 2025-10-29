from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from gradio_client import Client
import requests, json, secrets, hashlib

# --- CONFIG ---
GEMINI_API_KEY = "AIzaSyDpAmrLDJjDTKi7TD-IS3vqQlBAYVrUbv4"
MODEL_NAME = "gemini-2.0-flash"
TTS_MODEL = "Ghana-NLP/Southern-Ghana-TTS-Public"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///obala_users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- DATABASE MODEL ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    api_key = db.Column(db.String(64), unique=True)
    plan = db.Column(db.String(20), default="free")
    requests_used = db.Column(db.Integer, default=0)
    request_limit = db.Column(db.Integer, default=200)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def generate_key(self):
        self.api_key = secrets.token_hex(16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# --- AUTO CREATE DB ---
with app.app_context():
    db.create_all()
    print("✅ Database initialized or already exists.")


# --- INITIALIZE TTS CLIENT ---
tts_client = Client(TTS_MODEL)


# --- GEMINI REPLY FUNCTION ---
def gemini_reply(prompt):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 400},
        "system_instruction": {"parts": [{"text": "You are OBALA, an Akan Twi-speaking assistant developed by WAIT Technologies. Always respond in Akan Twi."}]}
    }

    res = requests.post(api_url, headers={"Content-Type": "application/json"}, data=json.dumps(payload))
    data = res.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return "Mepa wo kyɛw, mennim."


# --- ROUTES ---

@app.route("/")
def index():
    return jsonify({"message": "Welcome to OBALA API by WAIT Technologies."})


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    hashed_pw = generate_password_hash(password)
    new_user = User(full_name=full_name, email=email, password_hash=hashed_pw)
    new_user.generate_key()
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Signup successful", "api_key": new_user.api_key}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "api_key": user.api_key}), 200


@app.route("/obala_chat", methods=["POST"])
def obala_chat():
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"error": "API key required"}), 401

    user = User.query.filter_by(api_key=api_key).first()
    if not user:
        return jsonify({"error": "Invalid API key"}), 403
    if datetime.utcnow() > user.expires_at:
        return jsonify({"error": "API key expired"}), 403
    if user.requests_used >= user.request_limit:
        return jsonify({"error": "Usage limit reached. Upgrade plan."}), 429

    data = request.get_json()
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "Prompt required"}), 400

    twi_reply = gemini_reply(prompt)

    # Generate TTS audio
    try:
        audio_result = tts_client.predict(
            text=twi_reply,
            lang="Asante Twi",
            speaker="Male (Low)",
            api_name="/predict"
        )
        audio_path = audio_result if isinstance(audio_result, str) else None
    except Exception:
        audio_path = None

    # Update usage
    user.requests_used += 1
    db.session.commit()

    return jsonify({
        "response": twi_reply,
        "audio_path": audio_path,
        "usage": {
            "used": user.requests_used,
            "limit": user.request_limit,
            "plan": user.plan
        }
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
