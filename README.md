# AH-EYECARE 👓

A complete web platform for an **eyeglasses and sunglasses store** with:

- ✅ Virtual try-on using webcam and FaceMesh
- ✅ Admin dashboard with product, message & order management
- ✅ Background removal for VR frames (powered by remove.bg API)
- ✅ Online ordering and checkout
- ✅ SQLite database integration
- ✅ Clean, responsive design with Tailwind CSS

---

## 🚀 Features

| Function                    | Description                                                 |
|----------------------------|-------------------------------------------------------------|
| 👨‍💼 Admin Panel           | Add/delete products, view orders and contact messages       |
| 🧠 Virtual Try-On          | Live webcam try-on with face-tracked frames                 |
| 🌐 Product Pages           | Customers can view and order eyeglasses/sunglasses          |
| 🧾 Checkout System         | Basic cart and checkout flow with order saving              |
| 📸 Background Removal       | Optional automatic background removal on uploaded frames    |

---

## ⚙️ Tech Stack

- Python 3 + Flask
- SQLite
- Jinja2 Templates
- TailwindCSS
- JavaScript (FaceMesh + webcam integration)
- remove.bg API

---

## 🔧 Setup Instructions

```bash
# Clone the repo
git clone https://github.com/errorfo/ah-eyecare.git
cd ah-eyecare

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

