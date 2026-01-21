# -*- coding: utf-8 -*-
"""
Created on Thu Oct 30 19:12:20 2025

@author: rares
"""

# --- P1: Identificarea Resurlez din nou serverul selor (Software) ---
from flask import Flask, request, jsonify, render_template, g
import sqlite3
import os
import config # Importăm configurările comune

# --- Configurare Aplicație ---

DATABASE = 'trafic.db'
# Numele aplicației Flask
app = Flask(__name__)
# Setăm locația bazei de date în configurația Flask
app.config['DATABASE'] = DATABASE


# --- Managementul Bazei de Date (SQLite) ---

def get_db():
    """Funcție pentru a deschide o conexiune la baza de date."""
    # 'g' este un obiect special Flask care stochează date pe durata unei cereri
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        # Această setare (row_factory) ne ajută să obținem rezultatele
        # ca dicționare (ex: {'timestamp': '14:00', 'count': 150})
        # în loc de tupluri (ex: ('14:00', 150)).
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Funcție pentru a închide automat conexiunea la baza de date la finalul cererii."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Funcție pentru a crea tabelul bazei de date dacă nu există."""
    # Verificăm dacă baza de date există deja
    db_exists = os.path.exists(app.config['DATABASE'])
    
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        print("Se inițializează baza de date...")
        # Definim structura tabelului 'rapoarte'
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rapoarte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                count INTEGER NOT NULL,
                location TEXT
            )
        ''')
        
        # Migrare simplă: încercăm să adăugăm coloana 'location' dacă nu există
        try:
            cursor.execute("ALTER TABLE rapoarte ADD COLUMN location TEXT")
            print("Coloana 'location' a fost adăugată la tabelul 'rapoarte'.")
        except sqlite3.OperationalError:
            # Coloana există deja
            pass
            
        db.commit()
        if not db_exists:
            print(f"Baza de date '{app.config['DATABASE']}' a fost creată cu succes.")
        else:
            print("Baza de date a fost găsită și verificată.")


# --- P5: Implementare (Definirea Endpoint-urilor API) ---

# -----------------------------------------------------------------------------
# Endpoint 1: Primirea Datelor de la Scriptul de Procesare (POST)
# -----------------------------------------------------------------------------
@app.route('/api/raport', methods=['POST'])
def primeste_raport():
    """
    Acest endpoint este apelat de 'procesor_trafic.py'.
    Primește un JSON (ex: {"timestamp": "14:00", "count": 150})
    și îl salvează în baza de date.
    """
    print("\n[API] Cerere POST primită la /api/raport...")
    
    # 1. Preluăm datele JSON trimise de scriptul de procesare
    data = request.json
    
    # 2. Validare simplă
    if not data or 'timestamp' not in data or 'count' not in data:
        print("[API] Eroare: Date JSON invalide sau incomplete.")
        return jsonify({"status": "eroare", "mesaj": "JSON invalid"}), 400

    try:
        # 3. Extragem datele
        timestamp = data['timestamp']
        count = data['count']
        location = data.get('location', 'N/A') # Default N/A
        
        # 4. Salvăm în baza de date
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO rapoarte (timestamp, count, location) VALUES (?, ?, ?)", 
                       (timestamp, count, location))
        db.commit() # Salvăm modificările
        
        print(f"[API] Date salvate cu succes: Ora={timestamp}, Numar={count}")
        
        # 5. Trimitem un răspuns de succes (HTTP 201 = Created)
        return jsonify({"status": "succes", "date_primite": data}), 201
    
    except Exception as e:
        print(f"[API] Eroare la inserarea în baza de date: {e}")
        return jsonify({"status": "eroare", "mesaj": str(e)}), 500

# -----------------------------------------------------------------------------
# Endpoint 2: Trimiterea Datelor către Dashboard-ul Web (GET)
# -----------------------------------------------------------------------------
@app.route('/api/date_trafic', methods=['GET'])
def trimite_date_trafic():
    """
    Acest endpoint este apelat de pagina web (browser-ul)
    pentru a obține toate datele necesare construirii graficului.
    Returnează o listă de obiecte JSON.
    """
    print("\n[API] Cerere GET primită la /api/date_trafic...")
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Selectăm toate rapoartele din baza de date, ordonate după oră
        cursor.execute("SELECT timestamp, count, location FROM rapoarte ORDER BY timestamp ASC")
        # Preluăm toate rândurile
        toate_rapoartele = cursor.fetchall()
        
        # Convertim rândurile din formatul bazei de date în dicționare
        # Datorită 'db.row_factory = sqlite3.Row', putem face asta ușor
        lista_rezultate = [dict(row) for row in toate_rapoartele]
        
        print(f"[API] Se trimit {len(lista_rezultate)} înregistrări către frontend.")
        
        # Returnăm lista ca JSON
        return jsonify(lista_rezultate)
        
    except Exception as e:
        print(f"[API] Eroare la citirea din baza de date: {e}")
        return jsonify({"status": "eroare", "mesaj": str(e)}), 500

# -----------------------------------------------------------------------------
# Endpoint 3: Servirea Paginii Web (Dashboard-ul)
# -----------------------------------------------------------------------------
@app.route('/')
def dashboard():
    """
    Acest endpoint servește pagina 'index.html' când cineva
    vizitează adresa http://127.0.0.1:5000/
    """
    print("\n[API] Se servește pagina principală (dashboard)...")
    # Flask va căuta automat 'index.html' într-un folder numit 'templates'
    # Asigură-te că ai un folder 'templates' și în el fișierul 'index.html'
    
    # Verificam daca exista folderul 'templates' si fisierul 'index.html'
    if not os.path.exists('templates') or not os.path.exists('templates/index.html'):
        print("[API] AVERTISMENT: Nu gasesc folderul 'templates' sau fisierul 'index.html'.")
        print("[API] Voi returna un mesaj simplu.")
        return """
        <h1>Server API Trafic</h1>
        <p>Serverul funcționează. Nu am găsit fișierul <strong>templates/index.html</strong>.</p>
        <p>Creează folderul 'templates' în același director cu 'api_server.py' 
           și pune fișierul 'index.html' (frontend-ul) în el.</p>
        """
        
    return render_template('index.html', location_name=config.LOCATION_NAME, timezone=config.TIMEZONE)


# --- Pornirea Serverului ---
if __name__ == '__main__':
    # Inițializăm baza de date (creează fișierul și tabelul dacă e nevoie)
    init_db()
    
    print("\n==============================================")
    print("Se pornește serverul API Flask...")
    print("Serverul va rula la adresa: http://127.0.0.1:5000/")
    print("Apasă CTRL+C pentru a opri serverul.")
    print("==============================================")
    
    # Pornim serverul
    # debug=True repornește serverul automat la orice modificare de cod
    # host='0.0.0.0' îl face vizibil în rețea (folosim '127.0.0.1' pentru local)
    # use_reloader=False este necesar în Spyder/Anaconda pentru a evita eroarea SystemExit
    app.run(debug=True, use_reloader=False, host='127.0.0.1', port=5000)