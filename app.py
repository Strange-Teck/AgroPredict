import os
import base64
import requests
from datetime import datetime
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- 1. CLOUD-SAFE DATABASE CONFIG (Process 3.1) ---
# Vercel is stateless. History clears on refresh because we use :memory: 
# This is a 'Serverless Constraint' you should mention to your lecturer.
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

# Ensure DB is created inside the memory context
with app.app_context():
    db.create_all()

# --- 2. LOCALISATION MAP (Unit 3.4.8: Buea Common Names) ---
LOCAL_NAMES = {
    "Phytophthora": "Black Pod Rot (Cocoa)",
    "Mycosphaerella": "Black Sigatoka (Plantain)",
    "Puccinia": "Maize Rust (Corn)",
    "Cercospora": "Leaf Spot",
    "Hemiptera": "Pest Attack (Insects)",
    "Healthy": "Healthy and Strong"
}

# --- 3. THE ENGINE ---
def analyze_leaf_with_cloud_ai(image_file):
    # --- 1. LOCALISATION MAP (Unit 3.4.8) ---
    LOCAL_NAMES = {
        "Phytophthora": "Black Pod Rot (Cocoa)",
        "Mycosphaerella": "Black Sigatoka (Plantain)",
        "Puccinia": "Maize Rust (Corn)",
        "Cercospora": "Leaf Spot",
        "Xanthomonas": "Bacterial Blight"
    }

    # --- 2. NONSENSE FILTER (Engineering Quality Gate) ---
    # These results are "trash" for farmers. We will map them to 'Healthy'.
    TRASH_RESULTS = ["mechanical damage", "environmental", "herbicide", "sunburn", "abiotic"]

    try:
        api_key = os.environ.get('PLANT_ID_API_KEY')
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('ascii')
        
        payload = {"images": [image_base64], "latitude": 4.15, "longitude": 9.24}
        headers = {"Api-Key": api_key, "Content-Type": "application/json"}
        
        response = requests.post("https://plant.id/api/v3/health_assessment", json=payload, headers=headers)
        data = response.json()

        # --- STEP 1: IS IT A PLANT? (Defensive Guard) ---
        if not data.get('result') or not data['result']['is_plant']['binary']:
            return "System Status: Object not recognized as a crop leaf."

        # --- STEP 2: CHECK HEALTH FIRST (Abstraction) ---
        # If the health probability is high, we ignore ALL disease suggestions.
        is_healthy_binary = data['result']['is_healthy']['binary']
        health_score = data['result']['is_healthy']['probability']

        if is_healthy_binary or health_score > 0.5:
            return "Diagnosis: Healthy Crop (No disease detected)"

        # --- STEP 3: SMART DISEASE FILTERING ---
        if data['result']['disease'] and data['result']['disease']['suggestions']:
            suggestion = data['result']['disease']['suggestions'][0]
            sci_name = suggestion['name'].lower()
            prob = suggestion['probability']

            # A: If the AI is not sure (< 25%), don't guess.
            if prob < 0.25:
                return "Diagnosis: Healthy (Minor natural variations detected)"

            # B: If the AI suggests "Mechanical Damage" or "Sunburn", tell the farmer it's Healthy.
            if any(trash in sci_name for trash in TRASH_RESULTS):
                return "Diagnosis: Healthy (Physical wear, no biological disease)"

            # C: Real Disease Matching
            for key, val in LOCAL_NAMES.items():
                if key.lower() in sci_name:
                    return f"Diagnosis: {val}"

            # D: Fallback for unmapped but high-confidence diseases
            return f"Diagnosis: Potential {sci_name.title()} detected."
        
        return "Diagnosis: Healthy Crop"

    except Exception as e:
        return "System Error: Connection to Cloud AI timed out."

# --- 4. DATA HELPER ---
def get_site_context():
    """Returns the proposal data (Unit 3: Reuse)"""
    # Important: Re-query the database every time to update history
    try:
        history = ScanRecord.query.order_by(ScanRecord.date.desc()).limit(5).all()
    except:
        history = []
        
    return {
        "name": "MBAKWA TECKSON ANKA",
        "matricule": "CT23A089",
        "locations": "Muea, Bomaka, Lysoka, Tole, Bokwango, Bikoko",
        "processes": [
            {"id": "3.1", "title": "Fundamentals", "detail": "Decomposition into AI/DB layers."},
            {"id": "3.2", "title": "Management", "detail": "McCabe V(G)=3 Complexity."},
            {"id": "3.3", "title": "Practical", "detail": "Defensive Logic & Info Hiding."},
            {"id": "3.4", "title": "Technologies", "detail": "Cloud AI & Regression math."},
            {"id": "3.5", "title": "DevOps", "detail": "Vercel & Git Evolution."}
        ],
        "recent_scans": history
    }

# --- 5. ROUTES ---
@app.route('/')
def home():
    return render_template('index.html', **get_site_context())

@app.route('/analyze', methods=['POST'])
def analyze():
    action_type = request.form.get('action_type')
    
    if action_type == 'disease':
        file = request.files.get('file')
        if not file: return render_template('index.html', error="No file selected", **get_site_context())
        
        res = analyze_leaf_with_cloud_ai(file)
        
        # PERSISTENCE (Unit 3.1)
        try:
            new_record = ScanRecord(filename=file.filename, result=res)
            db.session.add(new_record)
            db.session.commit()
        except:
            db.session.rollback()

        return render_template('index.html', prediction=res, **get_site_context())

    elif action_type == 'yield':
        rainfall = request.form.get('rainfall', 400)
        res = f"Forecast: {round(float(rainfall)*0.05 + 2.5, 2)} bags predicted per hectare."
        return render_template('index.html', prediction=res, **get_site_context())

# Vercel entry point
app = app