# === [1] IMPORTERTE BIBLIOTEK OG KONSTANTER ===

from flask import Flask, request, render_template, jsonify
import serial
import time
import os
import threading
import json
import re
import RPi.GPIO as GPIO

# --- Konfigurasjonsfil for sensorinnstillinger
settings_file = "sensor_settings.json"

# --- Seriell tilkobling - Arduino
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200


# === [2] GLOBALE VARIABLER OG STARTVERDIER ===

siste_aktiv_kommando = "" # brukes av nødbrems for å sjekke om roboten kjører fremover

sensor_data = {"left": 0.0, "mid": 0.0, "right": 0.0}
ir_sensor_data = {"D1": 0, "D3": 0, "D4": 0, "D6": 0}

battery_level = 0         # i prosent
battery_voltage = 0     # i volt

linje_status = "Søker etter linje"
navigasjon_aktiv = False

autonom_aktiv = False
autonom_status = "Venter på start"


# === [3] LASTE OG LAGRE SENSORINNSTILLINGER ===

def load_settings():
    try:
        with open(settings_file, "r") as f:
            return json.load(f)
    except:
        return {"ultra_threshold": 20, "ultra_reduce": 40, "ir_min": 200, "ir_max": 600}

def save_settings(data):
    with open(settings_file, "w") as f:
        json.dump(data, f)

sensor_settings = load_settings()


# === [4] OPPSETT AV HC-SR04 OG GPIO ===

# --- Sensoroppsett for HC-SR04
SENSORS = {
    "left": {"TRIG": 17, "ECHO": 27},
    "mid": {"TRIG": 22, "ECHO": 23},
    "right": {"TRIG": 24, "ECHO": 25}
}

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
for sensor in SENSORS.values():
    GPIO.setup(sensor["TRIG"], GPIO.OUT)
    GPIO.setup(sensor["ECHO"], GPIO.IN)
    
    
# === [5] SERIELL KOMMUNIKASJON MED ARDUINO ===

# --- Opprette seriell forbindelse med Arduino
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Seriell tilkobling etablert!")
except Exception as e:
    print(f"Feil ved seriell tilkobling: {e}")
    ser = None

# --- Funksjon for å sende kommandoer til Arduino
def send_to_arduino(command):
    global siste_aktiv_kommando
    if ser and ser.is_open:
        ser.write((command + "\n").encode())
        print(f"[SENDT] {command}")
        siste_aktiv_kommando = command  # lagre sist kjørte
        return f"Kommando sendt: {command}"
    return "Seriell port ikke tilgjengelig"


# === [6] SENSORBEHANDLING OG OVERVÅKING ===

# --- Funksjon for å oppdage hindring og stanse roboten (nødstopp)
def overvåk_for_hindring():
    global autonom_aktiv, autonom_status
    while True:
        try:
            if "MOV:X=1" in siste_aktiv_kommando:
                dist = min(sensor_data["left"], sensor_data["mid"], sensor_data["right"])
                if dist < sensor_settings.get("ultra_threshold", 20):
                    print("[BREMS] Hindring for nær! Stopper robot.")
                    send_to_arduino("MOV:X=0,Y=0,R=0")
                    if autonom_aktiv:
                        autonom_aktiv = False
                        autonom_status = "Stoppet av bremselogikk"
        except Exception as e:
            print(f"[BREMS-FEIL] {e}")
        time.sleep(0.1)

# --- Funksjon for å måle avstand med én HC-SR04-sensor
def get_distance(trig, echo):
    GPIO.output(trig, True)
    time.sleep(0.00001)
    GPIO.output(trig, False)
    start_time = time.time()
    stop_time = time.time()
    timeout = start_time + 0.04
    while GPIO.input(echo) == 0 and time.time() < timeout:
        start_time = time.time()
    timeout = time.time() + 0.04
    while GPIO.input(echo) == 1 and time.time() < timeout:
        stop_time = time.time()
    elapsed = stop_time - start_time
    distance = (elapsed * 34300) / 2
    return round(distance)

# --- Funksjon som kontinuerlig oppdaterer avstand fra alle sensorer
def update_sensor_data():
    while True:
        for key, pins in SENSORS.items():
            try:
                sensor_data[key] = get_distance(pins["TRIG"], pins["ECHO"])
            except:
                sensor_data[key] = 0
        time.sleep(0.25)
        
# --- Funksjon som leser IR-verdier og batterispenning fra Arduino (seriell)        
def read_serial_from_arduino():
    global battery_level, battery_voltage
    while True:
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode().strip()
                # --- Del 1: Les IR-sensorverdier 
                if line.startswith("IR:"):
                    parts = line[3:].strip().split(",")
                    if len(parts) == 4:
                        ir_sensor_data["D1"] = int(parts[0])
                        ir_sensor_data["D3"] = int(parts[1])
                        ir_sensor_data["D4"] = int(parts[2])
                        ir_sensor_data["D6"] = int(parts[3])
                # --- Del 2: Les batterispenning og beregn prosent
                elif line.startswith("BAT:"):
                    spenning_lest = float(line[4:].strip())
                    delingsfaktor = 3.13
                    battery_voltage = round(spenning_lest * delingsfaktor, 2)
                    battery_level = beregn_batteriprosent(battery_voltage)
            except Exception as e:
                print(f"[SERIAL ERROR] {e}")

# --- Funksjon for å beregne batteriprosent ut fra spenning
def beregn_batteriprosent(spenning):
    # For 4S Li-ion: 12.0V (tom) – 16.8V (full)
    spenning_max = 16.8
    spenning_min = 12.0
    prosent = (spenning - spenning_min) / (spenning_max - spenning_min) * 100
    return int(max(0, min(100, prosent)))


# === [7] NAVIGASJONSLOGIKK: LINJEFØLGING OG AUTONOMI ===

# --- Funksjon for linjefølging med 4 IR-sensorer og rotasjonskorrigering
def linjenavigasjon():
    global linje_status, navigasjon_aktiv
    linje_status = "Søker etter linje"
    navigasjon_aktiv = True

    fart = sensor_settings.get("linje_fart", 0.4)
    r_svak = sensor_settings.get("rotasjon_svak", 1)
    r_sterk = sensor_settings.get("rotasjon_sterk", 2)

    MIN = sensor_settings["ir_min"]
    MAX = sensor_settings["ir_max"]

    # --- Fase 1: Søk etter linje i maks 10 sekunder ---
    start_tid = time.time()
    linje_funnet = False

    while navigasjon_aktiv and time.time() - start_tid < 10:
        send_to_arduino(f"MOV:X={fart},Y=0,R=0")
        linje_status = "Søker etter linje"

        d3 = ir_sensor_data["D3"]
        d4 = ir_sensor_data["D4"]

        if MIN <= d3 <= MAX or MIN <= d4 <= MAX:
            linje_funnet = True
            break

        time.sleep(0.2)

    if not linje_funnet:
        send_to_arduino("MOV:X=0,Y=0,R=0")
        linje_status = "Ingen linje detektert"
        navigasjon_aktiv = False
        return

    # --- Fase 2: Følg linje med korreksjon ---
    while navigasjon_aktiv:
        d1 = ir_sensor_data["D1"]
        d3 = ir_sensor_data["D3"]
        d4 = ir_sensor_data["D4"]
        d6 = ir_sensor_data["D6"]

        d1_høy = MIN <= d1 <= MAX
        d3_høy = MIN <= d3 <= MAX
        d4_høy = MIN <= d4 <= MAX
        d6_høy = MIN <= d6 <= MAX

        kommando = None

        if d3_høy or d4_høy:
            kommando = f"MOV:X={fart},Y=0,R=0"
            linje_status = "Følger linje"
        elif d1_høy and d3_høy:
            kommando = f"MOV:X={fart},Y=0,R={r_svak}"
            linje_status = "Lett høyre"
        elif d4_høy and d6_høy:
            kommando = f"MOV:X={fart},Y=0,R={-r_svak}"
            linje_status = "Lett venstre"
        elif d1_høy and not d3_høy:
            kommando = f"MOV:X={fart},Y=0,R={r_sterk}"
            linje_status = "Kraftig høyre"
        elif d6_høy and not d4_høy:
            kommando = f"MOV:X={fart},Y=0,R={-r_sterk}"
            linje_status = "Kraftig venstre"
        else:
            kommando = None
            linje_status = "Søker etter linje..."

        if kommando:
            send_to_arduino(kommando)

        # Hvis alle sensorer er lave – start søk
        if not (d1_høy or d3_høy or d4_høy or d6_høy):
                send_to_arduino("MOV:X=0,Y=0,R=0")
                linje_status = "Mistet linje – søker med rotasjon"
            
                # Søk rotasjon mot venstre i 2 sek
                søk_start = time.time()
                while time.time() - søk_start < 2:
                    send_to_arduino(f"MOV:X=0,Y=0,R={-r_svak}")
                    time.sleep(0.2)
            
                    d3 = ir_sensor_data["D3"]
                    d4 = ir_sensor_data["D4"]
                    if MIN <= d3 <= MAX or MIN <= d4 <= MAX:
                        linje_status = "Linje gjenfunnet (venstre rotasjon)"
                        break
            
                else:
                    # Søk mot høyre i 4 sek
                    søk_start = time.time()
                    while time.time() - søk_start < 4:
                        send_to_arduino(f"MOV:X=0,Y=0,R={r_svak}")
                        time.sleep(0.2)
            
                        d3 = ir_sensor_data["D3"]
                        d4 = ir_sensor_data["D4"]
                        if MIN <= d3 <= MAX or MIN <= d4 <= MAX:
                            linje_status = "Linje gjenfunnet (høyre rotasjon)"
                            break
            
                    else:
                        # Siste forsøk: roter mot venstre i 2 sek
                        søk_start = time.time()
                        while time.time() - søk_start < 2:
                            send_to_arduino(f"MOV:X=0,Y=0,R={-r_svak}")
                            time.sleep(0.2)
            
                            d3 = ir_sensor_data["D3"]
                            d4 = ir_sensor_data["D4"]
                            if MIN <= d3 <= MAX or MIN <= d4 <= MAX:
                                linje_status = "Linje gjenfunnet (venstre avsluttende)"
                                break
                        else:
                            send_to_arduino("MOV:X=0,Y=0,R=0")
                            linje_status = "Linje tapt etter rotasjonssøk"
                            navigasjon_aktiv = False
                            break
                            
        time.sleep(0.2)

# --- Funksjon for vektorbasert autonom hindringsunngåelse
def autonom_navigasjon():
    global autonom_aktiv, autonom_status
    autonom_aktiv = True
    autonom_status = "Autonom kjøring aktivert (vektorstyrt)"

    # Maks og min tillatt avstand til hindring i cm
    MAX_DIST = 60 # brukes til å beregne unngåelsesstyrke
    MIN_DIST = 30 # under dette aktiveres nødbrems og løsrivning

    while autonom_aktiv:
        # --- Hent avstander fra de tre ultralydsensorene
        left = sensor_data["left"]
        mid = sensor_data["mid"]
        right = sensor_data["right"]

        # --- 1. Hindring for nær: stopp roboten og start løsrivning
        if mid < MIN_DIST or (left < MIN_DIST and right < MIN_DIST):
            send_to_arduino("MOV:X=0,Y=0,R=0")
            autonom_status = "Nødbrems – hindring for nær"
            print("[AUTONOM] Hindring – starter løsrivning")
            time.sleep(0.3)

            # --- Start roterende bevegelse til alle sensorer har fri sikt
            while autonom_aktiv:
                send_to_arduino("MOV:X=0,Y=0,R=20")
                time.sleep(0.4)

                left = sensor_data["left"]
                mid = sensor_data["mid"]
                right = sensor_data["right"]

                # --- Hvis roboten er fri, stopp rotasjon og fortsett
                if left > 40 and mid > 40 and right > 40:
                    autonom_status = "Løsrivning ferdig – fortsetter"
                    print("[AUTONOM] Løsrivning vellykket")

                    # Ekstra rotasjon for sikkerhetsmargin
                    send_to_arduino("MOV:X=0,Y=0,R=20")
                    time.sleep(1)
                    send_to_arduino("MOV:X=0,Y=0,R=0")

                    break  # gå videre til neste vurdering


            continue  # gå rett til ny sensoravlesning
        
        # --- 2. Vektorstyrt hindringsunngåelse basert på venstre/høyre avstand
        styrke_venstre = max(0, MAX_DIST - left)
        styrke_høyre = max(0, MAX_DIST - right)
        rotasjonskraft = styrke_venstre - styrke_høyre
  
        # Begrens rotasjon til ±30 grader
        rotasjonsgrad = int(max(-30, min(30, rotasjonskraft)))

        # Beregn fremoverfart: redusert dersom rotasjon trengs
        r_abs = abs(rotasjonsgrad)
        x_hastighet = round(1.0 - 0.8 * (r_abs / 30), 2)
        x_hastighet = max(0.2, x_hastighet)

        # --- Send bevegelseskommando med justert fart og rotasjon
        send_to_arduino(f"MOV:X={x_hastighet},Y=0,R={rotasjonsgrad}")
        autonom_status = f"X={x_hastighet}, R={rotasjonsgrad}"

        time.sleep(0.2)

# === [8] FLASK-RUTER – HTML-SIDER OG VISNING ===
app = Flask(__name__)

@app.route("/")
def index(): return render_template("index.html")

@app.route("/manual")
def manual(): return render_template("manual.html")

@app.route("/line")
def line(): return render_template("linjenavigasjon.html")

@app.route("/auto")
def auto(): return render_template("autonom.html")

@app.route("/lidar")
def lidar(): return render_template("lidar.html")

@app.route("/settings")
def settings(): return render_template("settings.html")

# === [9] FLASK-RUTER – DATA, KOMMANDOER OG INNSTILLINGER ===

@app.route("/control")
def control():
    cmd = request.args.get("cmd")
    if not cmd:
        return "Ingen kommando mottatt"
    return send_to_arduino(cmd)

@app.route("/sensors")
def sensors():
    rounded_data = {k: int(round(v)) for k, v in sensor_data.items()}
    return jsonify(rounded_data)

@app.route("/battery")
def battery():
    return jsonify({
        "level": battery_level,
        "voltage": battery_voltage
    })

@app.route("/distance")
def distance(): return jsonify({"distance": int(round(sensor_data["mid"]))})

@app.route("/ir_data")
def ir_data(): return jsonify(ir_sensor_data)

@app.route("/settings_data")
def settings_data():
    return jsonify(sensor_settings)

@app.route("/save_settings", methods=["POST"])
def save_sensor_settings():
    global sensor_settings
    data = request.get_json()
    if data:
        sensor_settings = data
        save_settings(sensor_settings)
        return "Innstillinger lagret."
    return "Ingen data mottatt."

@app.route("/linje_status")
def linje_status_api(): return jsonify({"status": linje_status})

# === [10] FLASK-RUTER – START/STOPP FOR NAVIGASJONSMODUSER ===

@app.route("/start_linjenavigasjon")
def start_linje():
    thread = threading.Thread(target=linjenavigasjon, daemon=True)
    thread.start()
    return "Linjenavigasjon startet."

@app.route("/stop_linjenavigasjon")
def stop_linje():
    global navigasjon_aktiv
    navigasjon_aktiv = False
    send_to_arduino("MOV:X=0,Y=0,R=0")
    return "Linjenavigasjon stoppet."

@app.route("/start_autonom")
def start_autonom():
    thread = threading.Thread(target=autonom_navigasjon, daemon=True)
    thread.start()
    return "Autonom navigasjon startet."

@app.route("/stop_autonom")
def stop_autonom():
    global autonom_aktiv, autonom_status
    autonom_aktiv = False
    autonom_status = "Autonom kjøring stoppet"
    send_to_arduino("MOV:X=0,Y=0,R=0")
    return "Autonom navigasjon stoppet."

@app.route("/autonom_status")
def get_autonom_status():
    return jsonify({"status": autonom_status})

# === [11] REBOOT-FUNKSJON FOR RASPBERRY PI ===

def delayed_reboot():
    time.sleep(2)
    os.system("sudo reboot")

@app.route("/reboot")
def reboot():
    threading.Thread(target=delayed_reboot, daemon=True).start()
    return "Raspberry Pi vil starte på nytt om få sekunder."

# === [12] OPPSTART AV BAKGRUNNSFUNKSJONER OG FLASK-APP ===

# --- Start bakgrunnstråder
threading.Thread(target=update_sensor_data, daemon=True).start()
threading.Thread(target=read_serial_from_arduino, daemon=True).start()
threading.Thread(target=overvåk_for_hindring, daemon=True).start() 

# --- Start Flask-applikasjon

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
    
    














