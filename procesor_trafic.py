# -*- coding: utf-8 -*-
"""
Script Procesare Trafic - Versiunea YOLOv8 (AI)
Acest script folosește un model de Deep Learning pentru a detecta și număra vehiculele.
"""

import os
# Fix critic pentru eroarea "OMP: Error #15" care crashează Spyder/Jupyter
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
import sys
import numpy as np
import math
import time
import requests # Pentru API
from datetime import datetime
import streamlink

import re # Pentru extragere titlu

# Importăm pytz pentru fuse orare
try:
    import pytz
except ImportError:
    pytz = None
    print("AVERTISMENT: Libraria 'pytz' nu este instalata. Ora va fi cea a sistemului local, nu cea a camerei.")
    print("Pentru ora corecta, ruleaza: pip install pytz")

# Încercăm să importăm YOLO. Dacă nu există, dăm un mesaj clar.
try:
    from ultralytics import YOLO
except ImportError:
    print("\n==================================================================================")
    print("EROARE CRITICĂ: Librăria 'ultralytics' nu este instalată.")
    print("Acest script necesită YOLOv8 pentru a funcționa.")
    print("Te rog să rulezi în terminal/Anaconda Prompt comanda:")
    print("    pip install ultralytics")
    print("==================================================================================\n")
    sys.exit()

import config # Importăm fișierul de configurare creat

# --- Configurare Contorizare ---
MIN_DISTANCE_MOVEMENT = 100 # Pixeli pe care trebuie să îi parcurgă o mașină ca să fie numărată (evită parcările)

# --- Inițializare Model AI ---
print("Se încarcă modelul YOLOv8 Nano (poate dura puțin la prima rulare)...")
model = YOLO("yolov8n.pt") # Descarcă automat fisierul daca nu exista
print("Model încărcat cu succes!")

# --- Helper: Extragere Nume Locație ---
def get_location_from_url(url):
    """
    Încearcă să extragă titlul paginii pentru a-l folosi ca nume de locație.
    """
    # 1. Dacă e fișier direct video (.m3u8), nu avem titlu HTML
    if url.endswith('.m3u8'):
        return None
        
    try:
        print(f"Încercare extragere nume locație din URL: {url} ...")
        # Timeout scurt ca să nu blocăm pornirea
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            # Căutăm tag-ul <title>
            match = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE | re.DOTALL)
            if match:
                title = match.group(1).strip()
                # Curățăm titlul (scoatem chestii generice dacă e cazul)
                title = title.replace("EarthCam - ", "")
                return title
    except Exception as e:
        print(f"Nu s-a putut extrage numele locației: {e}")
    
    return None

# --- Auto-Detectare Locație ---
# Folosim variabila din config ca default
LOCATION_NAME = config.LOCATION_NAME

detected_name = get_location_from_url(config.VIDEO_SOURCE)
if detected_name:
    LOCATION_NAME = detected_name
    print(f"Nume locație detectat automat: {LOCATION_NAME}")
else:
    print(f"Folosim numele manual: {LOCATION_NAME}")

# --- Extragere Stream Video ---
video_path = config.VIDEO_SOURCE

# Logică: Dacă e link direct .m3u8, îl folosim direct. Altfel, încercăm Streamlink.
if config.VIDEO_SOURCE.endswith(".m3u8"):
    print(f"URL detectat ca stream direct (HLS). Se folosește: {config.VIDEO_SOURCE}")
    video_path = config.VIDEO_SOURCE
elif config.VIDEO_SOURCE.startswith("http"):
    print(f"Se extrage stream-ul live prin Streamlink: {config.VIDEO_SOURCE}")
    try:
        streams = streamlink.streams(config.VIDEO_SOURCE)
        if "best" in streams:
            video_path = streams["best"].url
        elif "720p" in streams:
            video_path = streams["720p"].url
        else:
             video_path = list(streams.values())[0].url
        print(f"URL Stream extras: {video_path}")
    except Exception as e:
        print(f"Eroare streamlink: {e}")
        sys.exit()

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Nu s-a putut deschide video.")
    sys.exit()

# Dicționar pentru a ține minte starea mașinilor
# track_history[track_id] = {'start_pos': (x,y), 'current_pos': (x,y)}
track_history = {}
counted_ids = set() # Set cu ID-urile unice care au fost deja numărate
track_history = {}
counted_ids = set() # Set cu ID-urile unice care au fost deja numărate
total_masini = 0

# --- Variabile Raportare ---
timp_ultima_raportare = time.time()
masini_raportate_anterior = 0

print("Se pornește detectia AI...")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 1. Detecție și Tracking cu YOLO
    results = model.track(frame, persist=True, classes=[2, 3, 5, 7], verbose=False)
    
    # 2. Procesare Rezultate
    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xywh.cpu()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        
        for box, track_id in zip(boxes, track_ids):
            x, y, w, h = box
            cx, cy = int(x), int(y)
            
            # --- Logică Contorizare Unică ---
            
            # 1. Inițializare pentru ID nou
            if track_id not in track_history:
                track_history[track_id] = {
                    'start_pos': (cx, cy),
                    'current_pos': (cx, cy)
                }
            
            # 2. Actualizare poziție
            track_history[track_id]['current_pos'] = (cx, cy)
            
            # 3. Verificare Distanță Parcursă
            if track_id not in counted_ids:
                start_x, start_y = track_history[track_id]['start_pos']
                dist = math.sqrt((cx - start_x)**2 + (cy - start_y)**2)
                
                if dist > MIN_DISTANCE_MOVEMENT:
                    # Mașina s-a mișcat suficient => O numărăm
                    total_masini += 1
                    counted_ids.add(track_id)
                    print(f"Counted Vehicle ID: {track_id} (Moved {int(dist)}px)")

            # --- Desenare ---
            # Culoare cutie: Verde (Activ/Numărat), Galben (În așteptare/Parcat)
            color = (0, 255, 0) if track_id in counted_ids else (0, 255, 255)
            
            x1, y1 = int(x - w/2), int(y - h/2)
            x2, y2 = int(x + w/2), int(y + h/2)
            
            # Cutie
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Etichetă: ID + Status
            status = "COUNTED" if track_id in counted_ids else "WAITING"
            label = f"ID:{track_id} {status}"
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Info UI
    cv2.putText(frame, f"Total Masini Unice: {total_masini}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
    cv2.putText(frame, f"Active Tracking: {len(track_history)}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

    # --- RAPORTARE API ---
    current_time = time.time()
    if current_time - timp_ultima_raportare >= config.INTERVAL_RAPORTARE:
        # Calculăm câte mașini au trecut în acest interval
        masini_noi = total_masini - masini_raportate_anterior
        
        # Formatăm ora folosind Timezone-ul din config
        if pytz:
            try:
                tz = pytz.timezone(config.TIMEZONE)
                timestamp_str = datetime.now(tz).strftime("%H:%M")
            except Exception as e:
                print(f"Eroare Timezone ({config.TIMEZONE}): {e}. Se folosește ora locală.")
                timestamp_str = datetime.now().strftime("%H:%M")
        else:
            timestamp_str = datetime.now().strftime("%H:%M")
        
        # Pregătim datele
        payload = {
            "timestamp": timestamp_str,
            "count": masini_noi,
            "location": LOCATION_NAME
        }
        
        print(f"\n[RAPORT] Se trimit datele la API: {payload}")
        
        try:
            # Trimitem POST request
            response = requests.post(config.API_ENDPOINT, json=payload)
            if response.status_code in [200, 201]:
                print("[RAPORT] Succes!")
            else:
                print(f"[RAPORT] Eroare API: {response.status_code}")
        except Exception as e:
            print(f"[RAPORT] Eroare conexiune: {e}")
            
        # Actualizăm contoarele pentru următorul interval
        timp_ultima_raportare = current_time
        masini_raportate_anterior = total_masini

    cv2.imshow("Traffic AI YOLOv8", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()