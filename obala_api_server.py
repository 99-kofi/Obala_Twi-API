from flask import Flask, request, jsonify
from models import db, User
import requests, json, logging, os
from datetime import datetime
from gradio_client import Client

# Config
GEMINI_API_KEY = "AIzaSyDpAmrLDJjDTKi7TD-IS3vqQlBAYVrUbv4"
MODEL_NAME = "gemini-2.0-flash"
TTS_MODEL = "Ghana-NLP/Southern-Ghana-TTS-Public"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db.init_app(app)

# Initialize once
tts_client = Client(TTS_MODEL)

# Gemini Response Generator
def gemini_reply(history):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": history,
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 400},
        "system_instruction": {"parts": [{"text": "You are OBALA, an Akan Twi-speaking assistant developed by WAIT Technologies. Always respond in Akan Twi."}]}
    }
    res = requests.post(api_url, headers={"Content-Type": "application/json"}, data=json.dumps(payload))
    data = res.json()
    return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Mepa wo kyɛw, mennim")

@app.route("/signup", methods=["POST"])
def signup():
    from hashlib import sha256
    data = request.get_json()
    full_name, email, password = data.get("full_name"), data.get("email"), data.get("password")

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    user = User(full_name=full_name, email=email, password_hash=sha256(password.encode()).hexdigest())
    user.generate_key()
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Signup successful", "api_key": user.api_key}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email, password = data.get("email"), data.get("password")
    from hashlib import sha256
    user = User.query.filter_by(email=email).first()

    if not user or user.password_hash != sha256(password.encode()).hexdigest():
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "api_key": user.api_key}), 200

@app.route("/obala_chat", methods=["POST"])
def obala_chat():
    api_key = request.headers.get("X-API-Key")
    user = User.query.filter_by(api_key=api_key).first()

    if not user:
        return jsonify({"error": "Invalid or missing API key"}), 403
    if datetime.utcnow() > user.expires_at:
        return jsonify({"error": "API key expired"}), 403
    if user.requests_used >= user.request_limit:
        return jsonify({"error": "Usage limit reached. Upgrade your plan."}), 429

    data = request.get_json()
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    history = [{"role": "user", "parts": [{"text": prompt}]}]
    twi_reply = gemini_reply(history)

    try:
        audio_result = tts_client.predict(text=twi_reply, lang="Asante Twi", speaker="Male (Low)", api_name="/predict")
        audio_path = audio_result if isinstance(audio_result, str) else None
    except Exception:
        audio_path = None

    user.requests_used += 1
    db.session.commit()

    return jsonify({
        "response": twi_reply,
        "audio": audio_path,
        "usage": {"used": user.requests_used, "limit": user.request_limit, "plan": user.plan}
    })

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8000, debug=True)
