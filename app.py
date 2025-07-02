from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from io import BytesIO
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ─── Database Setup ──────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FOLDER = os.path.join(BASE_DIR, 'database')
os.makedirs(DB_FOLDER, exist_ok=True)
DB_PATH = os.path.join(DB_FOLDER, 'users.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ─── Models ──────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class HealthLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    calories = db.Column(db.Integer)
    water = db.Column(db.Float)
    sleep = db.Column(db.Float)
    user = db.relationship('User', backref=db.backref('logs', lazy=True))

# ─── One‑time table creation (runs on import) ────────────────────────────────
with app.app_context():
    db.create_all()

# ─── LoginManager loader ─────────────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash("Please fill all fields.", "error")
            return redirect(url_for('signup'))
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return redirect(url_for('signup'))
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f"Welcome, {user.username}!", "success")
            return redirect(url_for('dashboard'))
        flash("Invalid credentials.", "error")
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        try:
            calories = int(request.form.get('calories', 0))
            water = float(request.form.get('water', 0))
            sleep = float(request.form.get('sleep', 0))

            log = HealthLog(user_id=current_user.id, calories=calories, water=water, sleep=sleep)
            db.session.add(log)
            db.session.commit()
            flash("Health log added!", "success")
        except ValueError:
            flash("Invalid input in form.", "error")
        return redirect(url_for('dashboard'))

    logs = HealthLog.query.filter_by(user_id=current_user.id).order_by(HealthLog.date.desc()).all()
    return render_template('dashboard.html', logs=logs, username=current_user.username)

@app.route('/bmi', methods=['POST'])
@login_required
def bmi():
    try:
        height = float(request.form['height']) / 100
        weight = float(request.form['weight'])
        bmi = round(weight / (height ** 2), 2)
        category = ("Underweight" if bmi < 18.5 else
                    "Normal"      if bmi < 25   else
                    "Overweight"  if bmi < 30   else
                    "Obese")
        return jsonify({'bmi': bmi, 'category': category})
    except:
        return jsonify({'error': 'Invalid input'}), 400

@app.route('/export_pdf')
@login_required
def export_pdf():
    logs = HealthLog.query.filter_by(user_id=current_user.id).order_by(HealthLog.date.desc()).all()
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 800, f"Health Logs for {current_user.username}")

    y = 770
    for log in logs:
        entry = f"{log.date} | Calories: {log.calories}, Water: {log.water}L, Sleep: {log.sleep}h"
        p.drawString(80, y, entry)
        y -= 20
        if y < 50:
            p.showPage()
            y = 800

    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name='health_logs.pdf',
                     mimetype='application/pdf')

@app.route('/get_health_data')
@login_required
def get_health_data():
    logs = HealthLog.query.filter_by(user_id=current_user.id).order_by(HealthLog.date.asc()).all()
    serialized_logs = [{
        'date': log.date.strftime('%Y-%m-%d'),
        'calories': log.calories,
        'water': log.water,
        'sleep': log.sleep
    } for log in logs]
    return jsonify(serialized_logs)

# ─── Local dev entry‑point ───────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
