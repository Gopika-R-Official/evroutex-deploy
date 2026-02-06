from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from sklearn.cluster import KMeans
import pandas as pd
import numpy as np
from datetime import datetime
import traceback
app.secret_key = 'evroutex-super-secret-key-2026-change-in-prod'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour


app = Flask(__name__)
app.secret_key = 'ev_routex_secret_2026'

DATA_FILE = 'data.json'

# FIXED: Safe data loading with auto-init
def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            init_data = {
                "admins": [{"username": "admin", "password": "admin@123"}],
                "drivers": [],
                "deliveries": [],
                "assignments": {}
            }
            save_data(init_data)
            return init_data
        
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except:
        # Auto-reset corrupted data
        print("Resetting corrupted data.json")
        init_data = {
            "admins": [{"username": "admin", "password": "admin@123"}],
            "drivers": [],
            "deliveries": [],
            "assignments": {}
        }
        save_data(init_data)
        return init_data

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Save error: {e}")

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        user_type = request.form.get('user_type')
        login_id = request.form.get('login_id', '').upper().strip()
        password = request.form.get('password', '')
        
        print(f"LOGIN DEBUG: action={action}, type={user_type}, id={login_id}")  # DEBUG
        
        data = load_data()
        
        if action == 'login':
            # ADMIN LOGIN
            if user_type == 'admin' and login_id == 'ADMIN' and password == 'admin@123':
                session['user_id'] = 'admin'
                session['user_type'] = 'admin'
                print("ADMIN LOGIN SUCCESS")  # DEBUG
                return redirect(url_for('admin_dashboard'))
            
            # DRIVER LOGIN - CHECK VEHICLE NUMBER
            for driver in data['drivers']:
                if driver.get('vehicle_no', '').upper() == login_id:
                    session['user_id'] = driver['vehicle_no']
                    session['user_type'] = 'driver'
                    session['vehicle_no'] = driver['vehicle_no']
                    print(f"DRIVER LOGIN SUCCESS: {driver['vehicle_no']}")  # DEBUG
                    return redirect(url_for('driver_route', vehicle_no=driver['vehicle_no']))
            
            return render_template('login.html', error="❌ Vehicle number not found!")
        
        elif action == 'register':
            # NEW DRIVER REGISTRATION
            new_driver = {
                'vehicle_no': request.form.get('vehicle_no', '').upper(),
                'company': request.form.get('company'),
                'model': request.form.get('model'),
                'range': int(request.form.get('range', 0))
            }
            
            data['drivers'].append(new_driver)
            save_data(data)
            
            # AUTO LOGIN
            session['user_id'] = new_driver['vehicle_no']
            session['user_type'] = 'driver'
            session['vehicle_no'] = new_driver['vehicle_no']
            
            print(f"NEW DRIVER REGISTERED: {new_driver}")  # DEBUG
            return redirect(url_for('driver_route', vehicle_no=new_driver['vehicle_no']))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
@app.route('/debug')
def debug():
    data = load_data()
    return f"""
    <h1>DEBUG INFO</h1>
    <p>Drivers registered: {len(data['drivers'])}</p>
    <pre>{json.dumps(data['drivers'][:2], indent=2)}</pre>  <!-- First 2 drivers -->
    <p>Session: {dict(session)}</p>
    """
    

# Admin routes
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    data = load_data()
    return render_template('admin_dashboard.html', drivers=len(data['drivers']))




@app.route('/admin/assign', methods=['GET', 'POST'])
def admin_assign():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    data = load_data()
    
    if request.method == 'POST':
        try:
            file = request.files['csv_file']
            if file:
                df = pd.read_csv(file)
                coords = df[['latitude', 'longitude']].values
                if len(data['drivers']) > 0:
                    kmeans = KMeans(n_clusters=min(len(data['drivers']), len(coords)), random_state=42, n_init=10)
                    clusters = kmeans.fit_predict(coords)
                    
                    for i, driver in enumerate(data['drivers']):
                        driver_orders = df[clusters == i].to_dict('records')
                        data['assignments'][driver['vehicle_no']] = driver_orders
                    save_data(data)
                    return render_template('admin_assign.html', success='Orders assigned successfully!', drivers=data['drivers'])
        except Exception as e:
            return render_template('admin_assign.html', error=str(e), drivers=data['drivers'])
    
    return render_template('admin_assign.html', drivers=data['drivers'])

# Driver routes
@app.route('/driver/dashboard')
def driver_dashboard():
    if session.get('user_type') != 'driver':
        return redirect(url_for('login'))
    data = load_data()
    vehicle_no = session['user_id']
    orders = data['assignments'].get(vehicle_no, [])
    return render_template('driver_dashboard.html', orders=orders, vehicle_no=vehicle_no)

# Add this to your app.py (replace driver_route route)

@app.route('/driver/route/<vehicle_no>', methods=['GET', 'POST'])
def driver_route(vehicle_no):
    if session.get('user_type') != 'driver' or session['user_id'] != vehicle_no:
        return redirect(url_for('login'))
    
    data = load_data()
    orders = data['assignments'].get(vehicle_no, [])
    
    if request.method == 'POST':
        # Save vehicle stats
        session['vehicle_stats'] = {
            'temp': float(request.form['temp']),
            'load': float(request.form['load']),
            'battery': float(request.form['battery'])
        }
        print(f"✅ Vehicle stats saved: {session['vehicle_stats']}")
    
    stats = session.get('vehicle_stats', {})
    return render_template('driver_route.html', orders=orders, vehicle_no=vehicle_no, stats=stats)

if __name__ == '__main__':
    os.makedirs('static/uploads', exist_ok=True)
    print("🚀 EV ROUTEX Starting... Admin: admin/admin@123")
    app.run(debug=True, host='127.0.0.1', port=5000)
