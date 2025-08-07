from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from extensions import db
from models import Admin, ContactMessage, Product, Order
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, SelectField, FileField
from wtforms.validators import DataRequired
import os
import json
from datetime import timedelta
from datetime import datetime
# Optional: only import if remove.bg key is used
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

db.init_app(app)

with app.app_context():
    db.create_all()
    if not Admin.query.first():
        admin = Admin(username='admin', password=generate_password_hash('admin123'))
        db.session.add(admin)
        db.session.commit()


# ---------- ROUTES ----------
from datetime import datetime

@app.route('/')
def index():
    products = Product.query.all()
    latest_products = Product.query.order_by(Product.id.desc()).limit(4).all()
    return render_template('index.html', products=products, latest_products=latest_products, now=datetime.now())
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form['username']).first()
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

    return render_template('dashboard.html', products=products, messages=messages, orders=orders, form=form, delete_form=delete_form, total_sales=total_sales)

@app.route('/add_product', methods=['POST'])
def add_product():
    if not session.get('admin'):
        return redirect(url_for('login'))

    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price')
    product_type = request.form.get('product_type')
    image_file = request.files.get('image')
    image_url = None

    if image_file:
        filename = secure_filename(image_file.filename)
        filename_no_ext = os.path.splitext(filename)[0]
        original_ext = os.path.splitext(filename)[1].lower()
        original_path = os.path.join('static', 'pics', filename)
        output_path = os.path.join('static', 'pics', filename_no_ext + '.png')

        os.makedirs(os.path.dirname(original_path), exist_ok=True)
        image_file.save(original_path)

        if REMOVE_BG_ENABLED:
            try:
                rmbg = RemoveBg("728Defd6BTLYiEAo6JdyE6JG", "error.log")
                rmbg.remove_background_from_img_file(original_path)
                image_url = '/' + output_path.replace('\\', '/')
            except Exception as e:
                print("Remove.bg failed:", e)
                flash("Frame uploaded, but background could not be removed.", "warning")
                image_url = '/' + original_path.replace('\\', '/')
        else:
            image_url = '/' + original_path.replace('\\', '/')

    try:
        price = float(price)
        if name and description and price >= 0 and product_type in ['eyeglasses', 'sunglasses'] and image_url:
            new_product = Product(
                name=name,
                description=description,
                price=price,
                image_url=image_url,
                product_type=product_type
            )
            db.session.add(new_product)
            db.session.commit()
            flash('Product added successfully!', 'success')
        else:
            flash('Invalid product data.', 'danger')
    except (ValueError, TypeError):
        flash('Price must be a number.', 'danger')

    return redirect(url_for('dashboard'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product_route(product_id):   # ✅ Renamed
    if not session.get('admin'):
        return redirect(url_for('login'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        db.session.add(ContactMessage(name=name, email=email, message=message))
        db.session.commit()
        flash('Message sent successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('contact.html')

@app.route('/tryon')
def tryon():
    pics_dir = os.path.join('static', 'pics')
    frame_files = [f for f in os.listdir(pics_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    frames = [{'name': os.path.splitext(f)[0], 'image_url': f'/static/pics/{f}'} for f in frame_files]
    return render_template('tryon.html', frames=frames)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    # Find similar products: same type, exclude current product, limit 4
    similar_products = Product.query.filter(
        Product.product_type == product.product_type,
        Product.id != product.id
    ).order_by(Product.id.desc()).limit(4).all()
    return render_template('product_detail.html', product=product, similar_products=similar_products)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = get_cart()
    products = []
    total = 0

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

        items = json.dumps(products)
        order = Order(name=name, email=email, phone=phone, address=address, items=items, total=total)
        db.session.add(order)
        db.session.commit()
        session['cart'] = {}
        return render_template('checkout.html', products=[], total=0, order_success=True)

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
from flask import render_template

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html")

@app.route("/store-locator")
def store_locator():
    return render_template("store_locator.html")

@app.route("/buying-guide")
def buying_guide():
    return render_template("buying-guide.html")

@app.route("/suggestions")
def suggestions():
    return render_template("suggestions.html")

@app.route("/hiring")
def hiring():
    return render_template("hiring.html")

@app.route("/refer")
def refer():
    return render_template("refer.html")

@app.route("/faqs")
def faqs():
    return render_template("faqs.html")

@app.route("/facebook")
def facebook_redirect():
    return redirect("https://facebook.com/YourProfileName")  # Replace with your real Facebook profile URL

@app.route('/search_products')
def search_products():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'products': []})
    products = Product.query.filter(Product.name.ilike(f'%{query}%')).limit(10).all()
    result = [
        {'id': p.id, 'name': p.name, 'price': p.price, 'image_url': p.image_url}
        for p in products
    ]
    return jsonify({'products': result})

def get_cart():
    return session.get('cart', {})

# ---------- Forms ----------
class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    image = FileField('Product Image', validators=[DataRequired()])
    product_type = SelectField('Product Type', choices=[('eyeglasses', 'Eyeglasses'), ('sunglasses', 'Sunglasses')], validators=[DataRequired()])
    submit = SubmitField('Add')

class DeleteForm(FlaskForm):
    submit = SubmitField('Delete')

# ---------- Run ----------
if __name__ == '__main__':
    app.run(debug=True)
