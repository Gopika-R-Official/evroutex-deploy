from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from sklearn.cluster import KMeans
import pandas as pd
import numpy as np
from datetime import datetime
import traceback

app = Flask(__name__)
app.secret_key = 'ev_routex_super_secret_2026_prod'

DATA_FILE = 'data.json'

# HELPER FUNCTION
def normalize_vehicle_no(vehicle_no):
    """Normalize vehicle number to uppercase without spaces"""
    return vehicle_no.upper().strip() if vehicle_no else None

# Safe data loading with auto-init
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

# DEBUG ROUTE - Shows all registered drivers
@app.route('/debug')
def debug():
    try:
        data = load_data()
        drivers = data.get('drivers', [])
        assignments = data.get('assignments', {})
        return f"""
        <div style="font-family: Arial; max-width: 800px; margin: 2rem auto; padding: 2rem;">
        <h1 style="color: #10b981;">🚀 EV ROUTEX DEBUG - PRODUCTION READY</h1>
        <h2>✅ LIVE ON RENDER</h2>
        
        <h3>Drivers Registered ({len(drivers)}):</h3>
        <pre style="background:#f8f9fa;padding:1.5rem;border-radius:12px;overflow:auto;max-height:300px;font-size:13px;border:1px solid #e5e7eb;">
{json.dumps(drivers, indent=2)}
        </pre>
        
        <h3>📦 Assignments:</h3>
        <pre style="background:#f0f9ff;padding:1rem;border-radius:8px;font-size:12px;">
{json.dumps({k: len(v) for k,v in assignments.items()}, indent=2)}
        </pre>
        
        <h3>🔑 Current Session:</h3>
        <pre style="background:#fef3c7;padding:1rem;border-radius:8px;font-size:12px;">
{json.dumps(dict(session), indent=2)}
        </pre>
        
        <div style="margin-top: 2rem;">
            <a href="/login" style="padding:1rem 2rem;background:#10b981;color:white;text-decoration:none;border-radius:12px;font-weight:600;">← Login</a>
            <a href="/admin/dashboard" style="padding:1rem 2rem;background:#3b82f6;color:white;text-decoration:none;border-radius:12px;font-weight:600;margin-left:1rem;">Admin</a>
        </div>
        </div>
        """
    except Exception as e:
        return f"<h1 style='color:red;'>❌ ERROR: {str(e)}</h1>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        user_type = request.form.get('user_type')
        login_id = normalize_vehicle_no(request.form.get('login_id'))
        password = request.form.get('password', '')
        
        print(f"LOGIN DEBUG: action={action}, type={user_type}, id={login_id}")
        
        data = load_data()
        
        if action == 'login':
            # ADMIN LOGIN
            if user_type == 'admin' and login_id in ['ADMIN', 'ADMIN@123', 'admin', 'ADMIN123'] and password == 'admin@123':
                session['user_id'] = 'admin'
                session['user_type'] = 'admin'
                print("✅ ADMIN LOGIN SUCCESS")
                return redirect(url_for('admin_dashboard'))
            
            # DRIVER LOGIN - Works for ALL registered vehicles
            for driver in data['drivers']:
                if normalize_vehicle_no(driver.get('vehicle_no')) == login_id:
                    session['user_id'] = driver['vehicle_no']
                    session['user_type'] = 'driver'
                    session['vehicle_no'] = driver['vehicle_no']
                    print(f"✅ DRIVER LOGIN SUCCESS: {driver['vehicle_no']}")
                    return redirect(url_for('driver_route', vehicle_no=driver['vehicle_no']))
            
            return render_template('login.html', error="❌ Vehicle number not found! Register first.")
        
        elif action == 'register':
            new_driver = {
                'vehicle_no': normalize_vehicle_no(request.form.get('vehicle_no')),
                'company': request.form.get('company'),
                'model': request.form.get('model'),
                'range': int(request.form.get('range', 0))
            }
            
            # Check if already exists
            for driver in data['drivers']:
                if normalize_vehicle_no(driver.get('vehicle_no')) == new_driver['vehicle_no']:
                    return render_template('login.html', error="❌ Vehicle already registered!")
            
            data['drivers'].append(new_driver)
            save_data(data)
            
            # AUTO LOGIN after registration
            session['user_id'] = new_driver['vehicle_no']
            session['user_type'] = 'driver'
            session['vehicle_no'] = new_driver['vehicle_no']
            
            print(f"✅ NEW DRIVER REGISTERED: {new_driver['vehicle_no']}")
            return redirect(url_for('driver_route', vehicle_no=new_driver['vehicle_no']))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Admin Dashboard - Clickable drivers list
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    
    data = load_data()
    drivers_count = len(data['drivers'])
    assignments_count = sum(len(orders) for orders in data['assignments'].values())
    
    return render_template('admin_dashboard.html', 
                         drivers=drivers_count,
                         drivers_list=data['drivers'],
                         assignments_count=assignments_count)

# Admin Assign Orders (CSV + K-Means)
@app.route('/admin/assign', methods=['GET', 'POST'])
def admin_assign():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    
    data = load_data()
    
    if request.method == 'POST':
        try:
            file = request.files['csv_file']
            if file and file.filename:
                df = pd.read_csv(file)
                coords = df[['latitude', 'longitude']].values
                
                if len(data['drivers']) > 0 and len(coords) > 0:
                    n_clusters = min(len(data['drivers']), len(coords))
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    clusters = kmeans.fit_predict(coords)
                    
                    data['assignments'] = {}
                    for i, driver in enumerate(data['drivers']):
                        driver_orders = df[clusters == i].to_dict('records')
                        data['assignments'][driver['vehicle_no']] = driver_orders
                    
                    save_data(data)
                    return render_template('admin_assign.html', 
                                         success='✅ Orders assigned using K-Means clustering!',
                                         drivers=data['drivers'])
        except Exception as e:
            return render_template('admin_assign.html', 
                                 error=f'❌ Error: {str(e)}', 
                                 drivers=data['drivers'])
    
    return render_template('admin_assign.html', drivers=data['drivers'])

# Driver Route Optimization - Hub → Orders → Hub
@app.route('/driver_route/<vehicle_no>', methods=['GET', 'POST'])
def driver_route(vehicle_no):
    # 🔥 FIXED: Works for ALL registered vehicles + direct access
    data = load_data()
    
    # Verify vehicle exists
    driver_exists = any(normalize_vehicle_no(d.get('vehicle_no')) == normalize_vehicle_no(vehicle_no) 
                       for d in data['drivers'])
    
    if not driver_exists:
        return render_template('login.html', error="❌ Vehicle not registered! Register first.")
    
    # Auto-set session for direct access / bookmarks
    session['user_id'] = vehicle_no
    session['user_type'] = 'driver'
    session['vehicle_no'] = vehicle_no
    
    orders = data['assignments'].get(vehicle_no, [])
    
    if request.method == 'POST':
        # Save vehicle stats for route optimization
        session['vehicle_stats'] = {
            'temp': float(request.form['temp']),
            'load': float(request.form['load']),
            'battery': float(request.form['battery'])
        }
        print(f"✅ Vehicle stats: Temp={session['vehicle_stats']['temp']}°C, Load={session['vehicle_stats']['load']}kg, Battery={session['vehicle_stats']['battery']}%")
    
    stats = session.get('vehicle_stats', {'temp': 25.0, 'load': 0, 'battery': 80})
    
    return render_template('driver_route.html', 
                         orders=orders, 
                         vehicle_no=vehicle_no, 
                         stats=stats)

if __name__ == '__main__':
    os.makedirs('static/uploads', exist_ok=True)
    print("🚀 EV ROUTEX Production Ready!")
    print("✅ Admin: admin / admin@123")
    print("✅ Driver: Register OR login with vehicle number")
    print("✅ Visit /debug to see all registered vehicles")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))



