import os
import base64
import requests
import random
from datetime import datetime
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# =========================================================
# 1. THE BRAIN: CLOUD AI CONFIGURATION (Process 3.4)
# =========================================================
# PASTE YOUR KEY FROM PLANT.ID INSIDE THE QUOTES BELOW
PLANT_ID_API_KEY = "znfD82TQAmoihGwfGD3M74rRoYFlKJ9EIAGDbM9VEPwEwjmAhD" 
PLANT_ID_URL = "https://plant.id/api/v3/health_assessment"

# =========================================================
# 2. DATABASE CONFIGURATION (Process 3.1)
# =========================================================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agropredict.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

if os.environ.get('VERCEL'):
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

with app.app_context():
    db.create_all()

# =========================================================
# 3. THE ENGINE: REAL IMAGE ANALYSIS (Unit 3.4.1)
# =========================================================
def analyze_leaf_with_cloud_ai(image_file):
    # --- Localisation Map (Unit 3.4.8) ---
    LOCAL_NAMES = {
        # --- Cocoa Diseases ---
        "Phytophthora": "Black Pod Rot (Cocoa)",
        "Moniliophthora": "Frosty Pod Rot",
        "Vascular streak": "Vascular Streak Dieback",
        
        # --- Plantain & Banana ---
        "Mycosphaerella": "Black Sigatoka (Plantain)",
        "Pseudocercospora": "Black Sigatoka (Plantain)",
        "Banana bunchy top": "Banana Bunchy Top Disease",
        "Fusarium oxysporum": "Panama Disease (Wilt)",
        "Ralstonia": "Moko Disease (Bacterial Wilt)",
        
        # --- Maize (Corn) ---
        "Puccinia": "Maize Rust (Corn)",
        "Ustilago": "Common Smut",
        "Maize streak": "Maize Streak Virus",
        "Cercospora zeae": "Gray Leaf Spot (Maize)",
        
        # --- Cassava & Tubers ---
        "Cassava mosaic": "Cassava Mosaic Disease",
        "Xanthomonas": "Bacterial Blight",
        "Phytophthora infestans": "Late Blight (Potato/Tomato)",
        
        # --- Coffee ---
        "Hemileia": "Coffee Leaf Rust",
        "Colletotrichum": "Coffee Berry Disease",
        
        # --- General ---
        "Healthy": "Healthy Crop (Verified)"
    }


    try:
        image_bytes = image_file.read()
        image_base64 = base64.b64encode(image_bytes).decode('ascii')
        payload = {"images": [image_base64], "latitude": 4.15, "longitude": 9.24}
        headers = {"Api-Key": PLANT_ID_API_KEY, "Content-Type": "application/json"}
        
        response = requests.post(PLANT_ID_URL, json=payload, headers=headers)
        data = response.json()

        # 1. Verification Gate (Unit 1.4.1)
        if not data.get('result') or not data['result']['is_plant']['binary']:
            return "System Status: Image not recognized as a crop leaf."

        # 2. Check Health
        is_healthy = data['result']['is_healthy']['binary']
        if is_healthy and data['result']['is_healthy']['probability'] > 0.6:
            return "Diagnosis: Healthy Crop (Verified)"

        # 3. Identify Disease with Tuned Threshold (Unit 3.8.7)
        if data['result']['disease'] and data['result']['disease']['suggestions']:
            suggestion = data['result']['disease']['suggestions'][0]
            sci_name = suggestion['name']
            prob_score = suggestion['probability'] * 100 

            # TUNING: Set to 20% to allow real-world Cocoa/Maize photos to pass
            if prob_score < 20:
                return "Diagnosis: Symptoms unclear. Please take a closer photo."

            # ABSTRACTION: Match Scientific -> Local
            final_name = "Requires Attention"
            for key, local_val in LOCAL_NAMES.items():
                if key.lower() in sci_name.lower():
                    final_name = local_val
                    break
            
            # If we didn't find it in our dictionary, show the Scientific name
            if final_name == "Requires Attention":
                final_name = f"Issue detected: {sci_name}"

            return f"Diagnosis: {final_name}"

        return "Diagnosis: Healthy Crop"

    except Exception as e:
        return "Connection Error: Check Muea network signal."
# =========================================================
# 4. SITE DATA & ROUTES
# =========================================================
def get_site_metadata():
    return {
        "name": "MBAKWA TECKSON ANKA",
        "matricule": "CT23A089",
        "locations": "Muea, Bomaka, Lysoka, Tole, Bokwango, Bikoko",
        "highlights": [
            {"area": "Cloud AI Integration", "desc": "Using RESTful API to perform real-time CNN inference on leaf pixels."},
            {"area": "Database Persistence", "desc": "SQLite stores all farmer diagnostic history for Buea farms."},
            {"area": "Complexity Management", "desc": "Calculated V(G)=3 for the decision logic (Unit 1)."},
            {"area": "Defensive Construction", "desc": "API exception handling prevents system failure during network drops."}
        ],
        "math": {"edges": 8, "nodes": 7, "decisions": 2, "result": 3}
    }

@app.route('/')
def home():
    recent_scans = ScanRecord.query.order_by(ScanRecord.date.desc()).limit(5).all()
    return render_template('index.html', recent_scans=recent_scans, **get_site_metadata())

@app.route('/analyze', methods=['POST'])
def analyze():
    action_type = request.form.get('action_type')
    context = get_site_metadata()
    
    if action_type == 'disease':
        file = request.files.get('file')
        if not file or file.filename == '':
            return render_template('index.html', error="Error: No image selected.", **context)

        # CALL THE REAL CLOUD AI
        ai_result = analyze_leaf_with_cloud_ai(file)

        # SAVE TO THE DATABASE (Persistence)
        new_record = ScanRecord(filename=file.filename, result=ai_result)
        db.session.add(new_record)
        db.session.commit()
        
        recent_scans = ScanRecord.query.order_by(ScanRecord.date.desc()).limit(5).all()
        return render_template('index.html', prediction=ai_result, recent_scans=recent_scans, **context)

    elif action_type == 'yield':
        rainfall = request.form.get('rainfall', 0)
        # Yield Regression formula from Process 3.4
        bags = (float(rainfall) * 0.048) + 3.2 # Simplified Regression Model
        result = f"Yield Forecast: ~{round(bags, 2)} Bags/Hectare based on Data Mining."
        recent_scans = ScanRecord.query.order_by(ScanRecord.date.desc()).limit(5).all()
        return render_template('index.html', prediction=result, recent_scans=recent_scans, **context)

if __name__ == '__main__':
    app.run(debug=True,)