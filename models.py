from datetime import datetime
from extensions import db

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(300))  # Normal product image
    product_type = db.Column(db.String(50))  # eyeglasses, sunglasses

    # New fields for AR Try-On
    vr_enabled = db.Column(db.Boolean, default=False)   # True if product supports try-on
    vr_image_url = db.Column(db.String(300))            # Transparent PNG for AR overlay


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    items = db.Column(db.Text)  # stored as JSON string
    total = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
