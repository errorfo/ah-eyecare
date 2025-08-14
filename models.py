from datetime import datetime
from extensions import db
from datetime import datetime

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
    image_url = db.Column(db.String(300))  # Main image
    image_urls = db.Column(db.Text)  # JSON list for extra images
    product_type = db.Column(db.String(50))  # eyeglasses, sunglasses
    available = db.Column(db.Boolean, default=True)
    lens_extra_price = db.Column(db.Float, default=0.0)

    # VR Try-On support
    vr_enabled = db.Column(db.Boolean, default=False)
    vr_image_url = db.Column(db.String(300))  # Transparent PNG
class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    image_url = db.Column(db.String(300), nullable=False)

    product = db.relationship('Product', backref=db.backref('gallery_images', lazy=True))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    items = db.Column(db.Text)  # stored as JSON string
    total = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    sender = db.Column(db.String(50), nullable=False)
    message_text = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
