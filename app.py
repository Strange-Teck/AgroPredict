import os
import base64
import requests
from datetime import datetime
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- 1. CLOUD-SAFE DATABASE CONFIG ---
# Vercel is a READ-ONLY environment. 
# We MUST use :memory: if VERCEL is detected to prevent 500 errors.
if os.environ.get('VERCEL') == '1':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agropredict.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class ScanRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100))
    result = db.Column(db.String(100))
    date = db.Column(db.DateTime, default=datetime.utcnow)

# Function to create tables only when needed (Safer for Vercel)
def setup_database():
    with app.app_context():
        db.create_all()

# --- 2. THE LOGIC ---
def analyze_leaf_with_cloud_ai(image_file):
    api_key = os.environ.get('PLANT_ID_API_KEY')
    if not api_key:
        return "Error: API Key not configured in Vercel."

    try:
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('ascii')
        
        payload = {
            "images": [image_base64],
            "latitude": 4.15, "longitude": 9.24,
            "similar_images": True
        }
        headers = {"Api-Key": api_key, "Content-Type": "application/json"}
        
        response = requests.post("https://plant.id/api/v3/health_assessment", json=payload, headers=headers)
        data = response.json()

        if data.get('result') and data['result']['disease']:
            suggestion = data['result']['disease']['suggestions'][0]
            name = suggestion['name']
            return f"Diagnosis: {name}"
        
        return "Diagnosis: Healthy Crop"
    except Exception as e:
        return f"Cloud Error: {str(e)}"

# --- 3. ROUTES ---
@app.route('/')
def home():
    setup_database() # Ensure DB is ready
    try:
        recent_scans = ScanRecord.query.order_by(ScanRecord.date.desc()).limit(5).all()
    except:
        recent_scans = []
        
    return render_template('index.html', 
        name="MBAKWA TECKSON ANKA",
        matricule="CT23A089",
        locations="Muea, Bomaka, Lysoka, Tole, Bokwango, Bikoko",
        processes=[
            {"id": "3.1", "title": "Fundamentals", "detail": "Decomposition & OOP."},
            {"id": "3.2", "title": "Management", "detail": "Iterative Lifecycle."},
            {"id": "3.3", "title": "Practical", "detail": "Defensive Programming."},
            {"id": "3.4", "title": "Technologies", "detail": "Cloud AI & Data Mining."},
            {"id": "3.5", "title": "DevOps", "detail": "Vercel & Git Evolution."}
        ],
        recent_scans=recent_scans
    )

@app.route('/analyze', methods=['POST'])
def analyze():
    action_type = request.form.get('action_type')
    
    if action_type == 'disease':
        file = request.files.get('file')
        if not file: return "Error: No file"
        
        res = analyze_leaf_with_cloud_ai(file)
        
        # Defensive Database Write
        try:
            new_record = ScanRecord(filename=file.filename, result=res)
            db.session.add(new_record)
            db.session.commit()
        except:
            db.session.rollback() # Prevent hanging connections
            
        return render_template('index.html', prediction=res, recent_scans=[], 
                               name="MBAKWA TECKSON ANKA", matricule="CT23A089",
                               locations="Muea, Bomaka, Lysoka, Tole, Bokwango, Bikoko",
                               processes=[])

    elif action_type == 'yield':
        rainfall = request.form.get('rainfall', 400)
        res = f"Forecast: {round(float(rainfall)*0.05, 2)} bags predicted."
        return render_template('index.html', prediction=res, recent_scans=[], 
                               name="MBAKWA TECKSON ANKA", matricule="CT23A089",
                               locations="Muea, Bomaka, Lysoka, Tole, Bokwango, Bikoko",
                               processes=[])

# FOR VERCEL
app = app