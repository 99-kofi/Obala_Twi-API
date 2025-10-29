from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import secrets, hashlib

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(128))
    api_key = db.Column(db.String(64), unique=True)
    plan = db.Column(db.String(20), default="free")  # free / pro / enterprise
    requests_used = db.Column(db.Integer, default=0)
    request_limit = db.Column(db.Integer, default=100)  # monthly limit
    expires_at = db.Column(db.DateTime, default=datetime.utcnow() + timedelta(days=30))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def generate_key(self):
        self.api_key = secrets.token_hex(24)

    def verify_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
