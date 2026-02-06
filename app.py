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

# 🔥 DEBUG ROUTE - FIXED POSITION
@app.route('/debug')
def debug():
    try:
        import json
        data = load_data()
        drivers = data.get('drivers', [])
        return f"""
        <h1>🚀 EV ROUTEX DEBUG - PRODUCTION</h1>
        <h2>✅ LIVE ON RENDER</h2>
        <h3>Drivers ({len(drivers)}):</h3>
        <pre style="background:#f8f9fa;padding:1rem;border-radius:8px;overflow:auto;max-height:400px;font-size:12px;">
{json.dumps(drivers[:5], indent=2)}
        </pre>
        <h3>🔑 Session:</h3>
        <pre>{json.dumps(dict(session), indent=2)}</pre>
        <p><a href="/login" style="padding:1rem 2rem;background:#10b981;color:white;text-decoration:none;border-radius:8px;font-weight:600;">← Back to Login</a></p>
        """
    except Exception as e:
        return f"<h1>❌ ERROR</h1><p>{str(e)}</p>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        user_type = request.form.get('user_type')
        login_id = request.form.get('login_id', '').upper().strip()
        password = request.form.get('password', '')
        
        print(f"LOGIN DEBUG: action={action}, type={user_type}, id={login_id}")
        
        data = load_data()
        
        if action == 'login':
            # 🔥 FIXED ADMIN LOGIN - accepts 'admin' OR 'ADMIN'
            if user_type == 'admin' and login_id in ['ADMIN', 'ADMIN@123', 'admin', 'ADMIN123'] and password == 'admin@123':
                session['user_id'] = 'admin'
                session['user_type'] = 'admin'
                print("✅ ADMIN LOGIN SUCCESS")
                return redirect(url_for('admin_dashboard'))
            
            # DRIVER LOGIN
            for driver in data['drivers']:
                if driver.get('vehicle_no', '').upper() == login_id:
                    session['user_id'] = driver['vehicle_no']
                    session['user_type'] = 'driver'
                    session['vehicle_no'] = driver['vehicle_no']
                    print(f"✅ DRIVER LOGIN: {driver['vehicle_no']}")
                    return redirect(url_for('driver_route', vehicle_no=driver['vehicle_no']))
            
            return render_template('login.html', error="❌ Invalid credentials!")
        
        elif action == 'register':
            new_driver = {
                'vehicle_no': request.form.get('vehicle_no', '').upper().strip(),
                'company': request.form.get('company'),
                'model': request.form.get('model'),
                'range': int(request.form.get('range', 0))
            }
            
            # Check if driver exists
            for driver in data['drivers']:
                if driver['vehicle_no'].upper() == new_driver['vehicle_no']:
                    return render_template('login.html', error="❌ Driver already registered!")
            
            data['drivers'].append(new_driver)
            save_data(data)
            
            # AUTO LOGIN
            session['user_id'] = new_driver['vehicle_no']
            session['user_type'] = 'driver'
            session['vehicle_no'] = new_driver['vehicle_no']
            
            print(f"✅ NEW DRIVER: {new_driver}")
            return redirect(url_for('driver_route', vehicle_no=new_driver['vehicle_no']))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Admin routes
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    data = load_data()
    drivers_count = len(data['drivers'])
    assignments_count = sum(1 for orders in data['assignments'].values() if len(orders) > 0)
    return render_template('admin_dashboard.html', 
                         drivers=drivers_count,
                         drivers_list=data['drivers'],
                         assignments_count=assignments_count)

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
                    
                    data['assignments'] = {}
                    for i, driver in enumerate(data['drivers']):
                        driver_orders = df[clusters == i].to_dict('records')
                        data['assignments'][driver['vehicle_no']] = driver_orders
                    save_data(data)
                    return render_template('admin_assign.html', success='✅ Orders assigned successfully!', drivers=data['drivers'])
        except Exception as e:
            return render_template('admin_assign.html', error=str(e), drivers=data['drivers'])
    
    return render_template('admin_assign.html', drivers=data['drivers'])

# Driver routes
@app.route('/driver_route/<vehicle_no>', methods=['GET', 'POST'])
def driver_route(vehicle_no):
    if session.get('user_type') != 'driver' or session['user_id'] != vehicle_no:
        return redirect(url_for('login'))
    
    data = load_data()
    orders = data['assignments'].get(vehicle_no, [])
    
    if request.method == 'POST':
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


