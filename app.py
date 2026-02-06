from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from sklearn.cluster import KMeans
import pandas as pd
import numpy as np
from datetime import datetime
import traceback

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
        action = request.form.get('action', 'login')
        
        if action == 'register':
            # ✅ NEW DRIVER SELF-REGISTRATION
            vehicle_no = request.form['vehicle_no'].strip().upper()
            company = request.form['company']
            model = request.form['model']
            range_km = float(request.form['range'])
            
            data = load_data()
            
            # Check if driver exists
            if any(d['vehicle_no'] == vehicle_no for d in data['drivers']):
                return render_template('login.html', error=f'Driver {vehicle_no} already registered!')
            
            # Auto-register
            new_driver = {
                'vehicle_no': vehicle_no,
                'company': company,
                'model': model,
                'range': range_km,
                'status': 'active',
                'assigned_orders': []
            }
            data['drivers'].append(new_driver)
            save_data(data)
            
            # Auto-login new driver
            session['user_id'] = vehicle_no
            session['user_type'] = 'driver'
            return redirect(url_for('driver_dashboard'))
        
        else:  # Existing login
            data = load_data()
            user_type = request.form['user_type']
            login_id = request.form['login_id'].strip()
            password = request.form.get('password', '').strip()
            
            if user_type == 'admin':
                admin = next((a for a in data['admins'] if a['username'] == login_id and a['password'] == password), None)
                if admin:
                    session['user_id'] = login_id
                    session['user_type'] = 'admin'
                    return redirect(url_for('admin_dashboard'))
            else:  # driver login
                driver = next((d for d in data['drivers'] if d['vehicle_no'] == login_id), None)
                if driver:
                    session['user_id'] = login_id
                    session['user_type'] = 'driver'
                    return redirect(url_for('driver_dashboard'))
            
            return render_template('login.html', error='Invalid credentials!')
    
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
