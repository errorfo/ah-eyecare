import os
import uuid
import json
from datetime import timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room, leave_room
from extensions import db
from models import Admin, ContactMessage, Product, Order, ChatMessage, ProductImage
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, SelectField, FileField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileAllowed, FileRequired, MultipleFileField

gallery_images = MultipleFileField("Extra Images", validators=[FileAllowed(["jpg", "png", "jpeg"], "Images only!")])

try:
    from removebg import RemoveBg
    REMOVE_BG_ENABLED = True
except ImportError:
    REMOVE_BG_ENABLED = False

app = Flask(__name__)
app.secret_key = 'secure_client_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=30)

# ✅ Initialize DB with app
db.init_app(app)

# ✅ SocketIO setup
socketio = SocketIO(app, cors_allowed_origins="*")
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'prescriptions')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ✅ Create tables & default admin inside app context
with app.app_context():
    db.create_all()
    if not Admin.query.first():
        admin = Admin(username='aheyecare786', password=generate_password_hash('AHeyecare786@'))
        db.session.add(admin)
        db.session.commit()

# ================= ROUTES =================

@app.route('/')
def index():
    products = Product.query.all()
    latest_products = Product.query.order_by(Product.id.desc()).limit(4).all()
    return render_template('index.html', products=products, latest_products=latest_products, now=datetime.now())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form['username'].lower()).first()
        if admin and check_password_hash(admin.password, request.form['password']):
            session['admin'] = True
            session.permanent = bool(request.form.get('remember'))
            return redirect(url_for('dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))
import json

@app.route('/dashboard')
def dashboard():
    if not session.get('admin'):
        return redirect(url_for('login'))

    form = ProductForm()
    delete_form = DeleteForm()
    products = Product.query.all()
    messages = ContactMessage.query.all()
    orders = Order.query.order_by(Order.timestamp.desc()).all()
    total_sales = sum(order.total for order in orders)
    lens_extra_price = FloatField('Lens Extra Price', default=0.0)

    for order in orders:
        try:
            order.items_list = json.loads(order.items)
        except:
            order.items_list = []

        # Check if order has lens power info:
        order.lens_power_info = None
        for item in order.items_list:
            if 'Lenses (Power:' in item.get('name', ''):
                order.lens_power_info = item['name']
                break

    # ✅ Parse product image URLs into a list so template can use product.image_list
    for p in products:
        try:
            p.image_list = json.loads(p.image_urls) if getattr(p, "image_urls", None) else []
        except:
            p.image_list = []

    return render_template(
        'dashboard'.html,
        products=products,
        messages=messages,
        orders=orders,
        form=form,
        delete_form=delete_form,
        total_sales=total_sales
    )

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route("/add_product", methods=["POST"])
def add_product():
    name = request.form.get("name")
    description = request.form.get("description")
    price = float(request.form.get("price", 0))
    product_type = request.form.get("product_type")
    vr_enabled = True if request.form.get("vr_enabled") else False
    lens_extra_price = float(request.form.get("lens_extra_price", 0))

    # Main Image
    main_image_file = request.files.get("image")
    main_image_url = None
    if main_image_file and main_image_file.filename:
        filename = secure_filename(main_image_file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        main_image_file.save(path)
        main_image_url = f"/static/uploads/{filename}"

    # Extra Images
    extra_images_files = request.files.getlist("extra_images")
    extra_image_urls = []
    for img in extra_images_files:
        if img and img.filename:
            filename = secure_filename(img.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            img.save(path)
            extra_image_urls.append(f"/static/uploads/{filename}")

    # VR Image
    vr_image_url = None
    vr_image_file = request.files.get("vr_image")
    if vr_image_file and vr_image_file.filename:
        filename = secure_filename(vr_image_file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        vr_image_file.save(path)
        vr_image_url = f"/static/uploads/{filename}"

    # Save Product
    product = Product(
    name=name,
    description=description,
    price=price,
    product_type=product_type,
    image_url=main_image_url,
    image_urls=json.dumps(extra_image_urls) if extra_image_urls else None,
    vr_enabled=vr_enabled,
    vr_image_url=vr_image_url,
    lens_extra_price=lens_extra_price)

    db.session.add(product)
    db.session.commit()

    flash("Product added successfully", "success")
    return redirect(url_for("dashboard"))

# ==============================
# Virtual Try-On Route
# ==============================
@app.route("/tryon")
def tryon():
    products = Product.query.filter_by(vr_enabled=True).all()

    frames = []
    for p in products:
        frames.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'vr_image_url': p.vr_image_url,
            'available': bool(p.id and p.price and p.price > 0)  # ✅ FIXED
        })

    default_frames = [
    {
        'id': None,
        'name': 'Default Frame 1',
        'price': '',
        'vr_image_url': url_for('static', filename='pics/glasses_PNG54292.png'),
        'available': False
    },
    {
        'id': None,
        'name': 'Default Frame 2',
        'price': '',
        'vr_image_url': url_for('static', filename='pics/WhatsApp_Image_2025-08-13_at_16.55.45_6b7a4549-removebg-preview (1).png'),
        'available': False
    },
    {
        'id': None,
        'name': 'Default Frame 3',
        'price': '',
        'vr_image_url': url_for('static', filename='pics/WhatsApp_Image_2025-08-13_at_16.55.45_6b7a4549-removebg-preview (2).png'),
        'available': False
    },
    {
        'id': None,
        'name': 'Default Frame 4',
        'price': '',
        'vr_image_url': url_for('static', filename='pics/WhatsApp_Image_2025-08-13_at_16.55.45_6b7a4549-removebg-preview.png'),
        'available': False
    },
    {
        'id': None,
        'name': 'Default Frame 5',
        'price': '',
        'vr_image_url': url_for('static', filename='pics/WhatsApp_Image_2025-08-13_at_16.55.47_a81edec6-removebg-preview.png'),
        'available': False
    },
    {
        'id': None,
        'name': 'Default Frame 6',
        'price': '',
        'vr_image_url': url_for('static', filename='pics/WhatsApp_Image_2025-08-13_at_16.55.47_cf1d2488-removebg-preview.png'),
        'available': False
    },
    {
        'id': None,
        'name': 'Default Frame 7',
        'price': '',
        'vr_image_url': url_for('static', filename='pics/WhatsApp_Image_2025-08-13_at_16.55.48_d7ebfc38-removebg-preview.png'),
        'available': False
    }
]


    frames += default_frames
    return render_template("tryon.html", frames=frames)



@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not message:
            flash('All fields are required.', 'danger')
            return redirect(url_for('contact'))

        try:
            new_message = ContactMessage(name=name, email=email, message=message)
            db.session.add(new_message)
            db.session.commit()
            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            print(f"Error saving contact message: {e}")
            flash('Something went wrong. Please try again later.', 'danger')
            return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)

    # ✅ Parse extra image URLs into a list so template can loop without |fromjson
    try:
        product.image_list = json.loads(product.image_urls) if getattr(product, "image_urls", None) else []
    except:
        product.image_list = []

    similar_products = Product.query.filter(
        Product.product_type == product.product_type,
        Product.id != product.id
    ).order_by(Product.id.desc()).limit(4).all()

    return render_template(
        'product_detail.html',
        product=product,
        similar_products=similar_products
    )

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = get_cart()
    products = []
    total = 0

    # Prepare products list and base total
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            products.append({'id': product.id, 'name': product.name, 'price': product.price, 'qty': qty})
            total += product.price * qty

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        order_type = request.form.get('order_type')  # "normal" or "with_lenses"
        lens_power = request.form.get('lens_power', '').strip()

        # Validate required fields
        if not (name and email and phone and address):
            flash("Please fill all required fields.", "danger")
            return render_template('checkout.html', products=products, total=total)

        lens_price = 0
        if order_type == "with_lenses":
            if not lens_power:
                flash("Please enter your lens power if you choose lenses with power.", "danger")
                return render_template('checkout.html', products=products, total=total)
            lens_price = 1000  # extra charge for power lenses
            total += lens_price

        # Add lens item to order summary if applicable
        items = products.copy()
        if lens_price > 0:
            items.append({'name': f'Lenses (Power: {lens_power})', 'price': lens_price, 'qty': 1})

        # Save order
        order = Order(
            name=name,
            email=email,
            phone=phone,
            address=address,
            items=json.dumps(items),
            total=total,
            timestamp=datetime.utcnow()
        )
        db.session.add(order)
        db.session.commit()

        session['cart'] = {}  # clear cart after order
        return render_template('checkout.html', products=[], total=0, order_success=True)

    # GET request, render checkout form
    return render_template('checkout.html', products=products, total=total)


@app.route('/cart')
def cart():
    cart = get_cart()
    products = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            products.append({'id': product.id, 'name': product.name, 'price': product.price, 'qty': qty})
            total += product.price * qty
    return render_template('cart.html', products=products, total=total)

@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = get_cart()
    cart.pop(str(product_id), None)
    session['cart'] = cart
    return jsonify({'success': True, 'cart': cart})

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    cart = get_cart()
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    cart_count = sum(cart.values())
    return jsonify({'success': True, 'cart': cart, 'cart_count': cart_count})

@app.route('/terms')
def terms():
    return render_template("terms.html")

@app.route('/privacy')
def privacy():
    return render_template("privacy.html")

@app.route('/disclaimer')
def disclaimer():
    return render_template("disclaimer.html")

@app.route('/store-locator')
def store_locator():
    return render_template("store_locator.html")

@app.route('/buying-guide')
def buying_guide():
    return render_template("buying-guide.html")

@app.route('/suggestions')
def suggestions():
    return render_template("suggestions.html")

@app.route('/hiring')
def hiring():
    return render_template("hiring.html")

@app.route('/refer')
def refer():
    return render_template("refer.html")

@app.route('/faqs')
def faqs():
    return render_template("faqs.html")

@app.route("/facebook")
def facebook_redirect():
    return redirect("https://facebook.com/YourProfileName")

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/search_products')
def search_products():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'products': []})
    products = Product.query.filter(Product.name.ilike(f'%{query}%')).limit(10).all()
    result = [{'id': p.id, 'name': p.name, 'price': p.price, 'image_url': p.image_url} for p in products]
    return jsonify({'products': result})

def get_cart():
    return session.get('cart', {})

# ---------- Forms ----------
class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    image = FileField('Main Product Image', validators=[DataRequired()])
    product_type = SelectField('Product Type', choices=[('eyeglasses', 'Eyeglasses'), ('sunglasses', 'Sunglasses')], validators=[DataRequired()])
    vr_enabled = SelectField('Enable VR Try-On?', choices=[('yes', 'Yes'), ('no', 'No')], default='no')
    vr_image = FileField('VR Image (Transparent PNG)')
    power_lens_extra_cost = FloatField('Power Lens Extra Cost', default=0.0)
    extra_images = MultipleFileField('Additional Product Images')
    video = FileField('Product Video (short)')
    submit = SubmitField('Add')

class DeleteForm(FlaskForm):
    submit = SubmitField('Delete')

# ---------- Run ----------
# ===========================
# LIVE CHAT + PRESCRIPTION UPLOAD
# ===========================

from flask import send_from_directory
from werkzeug.utils import secure_filename

# Chat route for user
@app.route('/chat')
def chat():
    return render_template('chat.html')

# Upload prescription inside chat
@app.route('/upload_prescription', methods=['POST'])
def upload_prescription():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400
    
    filename = secure_filename(file.filename)
    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    # Save message in DB as "file type"
    chat_msg = ChatMessage(
    username='User', 
    message_text=f'📄 Prescription uploaded: {filename}',
    file_url=save_path  # changed here
)

    db.session.add(chat_msg)
    db.session.commit()

    emit_data = {
        'username': 'User',
        'message': f'📄 Prescription uploaded: <a href="/prescriptions/{filename}" target="_blank">{filename}</a>'
    }
    socketio.emit('chat_message', emit_data, broadcast=True)

    return jsonify({'success': True, 'filename': filename})

# Serve uploaded prescriptions
@app.route('/prescriptions/<filename>')
def prescriptions(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# SocketIO events
@socketio.on('join')
def handle_join(data):
    join_room('main')
    emit('chat_message', {'username': 'System', 'message': f"{data['username']} joined the chat"}, room='main')

@socketio.on('leave')
def handle_leave(data):
    leave_room('main')
    emit('chat_message', {'username': 'System', 'message': f"{data['username']} left the chat"}, room='main')

@socketio.on('chat_message')
def handle_chat_message(data):
    chat_msg = ChatMessage(
        sender=data['username'],
        message_text=data['message'],
        session_id='main'
    )
    db.session.add(chat_msg)
    db.session.commit()

    emit('chat_message', data, broadcast=True)


# Auto-delete chat history when admin closes chat
@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    ChatMessage.query.delete()
    db.session.commit()
    return jsonify({'success': True})

# Admin chat routes
@app.route('/admin/chat')
def admin_chat():
    """Admin chat interface"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    messages = ChatMessage.query.order_by(ChatMessage.timestamp.desc()).all()
    return render_template('admin_chat.html', messages=messages)

@app.route('/admin/send_message', methods=['POST'])
def admin_send_message():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({'error': 'Message required'}), 400

    try:
        chat_msg = ChatMessage(
    sender='Admin',
    message_text=data['message'],
    session_id='admin_chat',
    timestamp=datetime.utcnow()
)

        db.session.add(chat_msg)
        db.session.commit()

        # Emit to all connected clients with event name 'admin_message'
        socketio.emit('admin_message', {
            'sender': 'Admin',
            'message': data['message'],
            'timestamp': chat_msg.timestamp.isoformat()
        }, broadcast=True)

        return jsonify({'success': True, 'message': 'Message sent'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# SocketIO events for admin
@socketio.on('admin_join')
def handle_admin_join(data):
    """Handle admin joining chat"""
    if not session.get('admin'):
        return
    
    join_room('admin_chat')
    emit('admin_status', {'status': 'online', 'admin': True}, room='admin_chat')

@socketio.on('admin_message')
def handle_admin_message(data):
    if not session.get('admin'):
        return

    try:
        chat_msg = ChatMessage(
            sender='Admin',
            message_text=data['message'],
            session_id='admin_chat',
            timestamp=datetime.utcnow()
        )
        db.session.add(chat_msg)
        db.session.commit()

        socketio.emit('admin_message', {
            'sender': 'Admin',
            'message': data['message'],
            'timestamp': chat_msg.timestamp.isoformat()
        }, broadcast=True)

    except Exception as e:
        emit('error', {'message': str(e)}, room=request.sid)

# ===========================
# CHAT API ENDPOINTS
# ===========================

@app.route('/chat/messages')
def get_chat_messages():
    try:
        messages = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
        result = []
        for msg in messages:
            result.append({
                'id': msg.id,
                'sender': msg.sender,
                'message': msg.message_text or '',
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else '',
                'file_url': msg.file_url  # note the name change here
            })
        return jsonify({'messages': result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/send_message', methods=['POST'])
def send_message():
    """Send a new chat message"""
    try:
        data = request.get_json()
        if not data or not data.get('message'):
            return jsonify({'error': 'Message is required'}), 400
        
        chat_msg = ChatMessage(
            sender=data.get('username', 'Anonymous'),
            message_text=data['message'],
            session_id=data.get('session_id', 'default'),
            timestamp=datetime.utcnow()
        )
        db.session.add(chat_msg)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': {
                'id': chat_msg.id,
                'sender': chat_msg.sender,
                'message': chat_msg.message_text,
                'timestamp': chat_msg.timestamp.isoformat()
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===========================
# FAVICON ROUTE
# ===========================
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# ===========================
# CHANGE RUN METHOD
# ===========================
if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
