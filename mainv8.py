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

autonom_aktiv = False
autonom_status = "Venter på start"

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

# --- Seriell tilkobling til Arduino
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Seriell tilkobling etablert!")
except Exception as e:
    print(f"Feil ved seriell tilkobling: {e}")
    ser = None

siste_aktiv_kommando = ""
sensor_data = {"left": 0.0, "mid": 0.0, "right": 0.0}
ir_sensor_data = {"D1": 0, "D3": 0, "D4": 0, "D6": 0}
battery_level = 0         # i prosent
battery_voltage = 0     # i volt
linje_status = "Søker etter linje"
navigasjon_aktiv = False

def send_to_arduino(command):
    global siste_aktiv_kommando
    if ser and ser.is_open:
        ser.write((command + "\n").encode())
        print(f"[SENDT] {command}")
        siste_aktiv_kommando = command  # lagre sist kjørte
        return f"Kommando sendt: {command}"
    return "Seriell port ikke tilgjengelig"

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

def update_sensor_data():
    while True:
        for key, pins in SENSORS.items():
            try:
                sensor_data[key] = get_distance(pins["TRIG"], pins["ECHO"])
            except:
                sensor_data[key] = 0
        time.sleep(0.25)

def read_serial_from_arduino():
    global battery_level, battery_voltage
    while True:
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode().strip()
                if line.startswith("IR:"):
                    parts = line[3:].strip().split(",")
                    if len(parts) == 4:
                        ir_sensor_data["D1"] = int(parts[0])
                        ir_sensor_data["D3"] = int(parts[1])
                        ir_sensor_data["D4"] = int(parts[2])
                        ir_sensor_data["D6"] = int(parts[3])
                elif line.startswith("BAT:"):
                    spenning_lest = float(line[4:].strip())
                    delingsfaktor = 3.13
                    battery_voltage = round(spenning_lest * delingsfaktor, 2)
                    battery_level = beregn_batteriprosent(battery_voltage)
            except Exception as e:
                print(f"[SERIAL ERROR] {e}")

def beregn_batteriprosent(spenning):
    # For 4S Li-ion: 12.0V (tom) – 16.8V (full)
    spenning_max = 16.8
    spenning_min = 12.0
    prosent = (spenning - spenning_min) / (spenning_max - spenning_min) * 100
    return int(max(0, min(100, prosent)))

def linjenavigasjon():
    global linje_status, navigasjon_aktiv
    linje_status = "Søker etter linje"
    navigasjon_aktiv = True

    fart = sensor_settings.get("linje_fart", 0.4)
    r_svak = sensor_settings.get("rotasjon_svak", 1)
    r_sterk = sensor_settings.get("rotasjon_sterk", 2)
    bruk_y = sensor_settings.get("bruk_y_retning", False)

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

def autonom_navigasjon():
    global autonom_aktiv, autonom_status
    autonom_aktiv = True
    autonom_status = "Autonom kjøring aktivert"

    rotasjon_grense = sensor_settings.get("auto_rotate", 20)
    unnam_grense = sensor_settings.get("auto_avoid", 40)

    while autonom_aktiv:
        left = sensor_data["left"]
        mid = sensor_data["mid"]
        right = sensor_data["right"]

        # 1. Blokkert begge sider
        if left < rotasjon_grense and right < rotasjon_grense:
            send_to_arduino("MOV:X=0,Y=0,R=180")
            autonom_status = "Roterer 180° – begge sider blokkert"
            time.sleep(3)

        # 2. Venstre blokkert – sving høyre (rotér litt med klokka)
        elif left < unnam_grense and right > left + 10:
            send_to_arduino("MOV:X=0,Y=0,R=15")
            autonom_status = "Roterer høyre – venstre blokkert"
            time.sleep(0.5)  # liten rotasjon

        # 3. Høyre blokkert – sving venstre (rotér litt mot klokka)
        elif right < unnam_grense and left > right + 10:
            send_to_arduino("MOV:X=0,Y=0,R=-15")
            autonom_status = "Roterer venstre – høyre blokkert"
            time.sleep(0.5)

        # 4. Fri bane – kjør frem
        else:
            send_to_arduino("MOV:X=1,Y=0,R=0")
            autonom_status = "Fremover – ingen hindring"

        time.sleep(0.2)

        
app = Flask(__name__)

@app.route("/")
def index(): return render_template("index.html")

@app.route("/manual")
def manual(): return render_template("manual.html")

@app.route("/line")
def line(): return render_template("linjenavigasjon.html")

@app.route("/auto")
def auto(): return render_template("autonom.html")

@app.route("/settings")
def settings(): return render_template("settings.html")

@app.route("/save_settings", methods=["POST"])
def save_sensor_settings():
    global sensor_settings
    data = request.get_json()
    if data:
        sensor_settings = data
        save_settings(sensor_settings)
        return "Innstillinger lagret."
    return "Ingen data mottatt."

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

@app.route("/linje_status")
def linje_status_api(): return jsonify({"status": linje_status})

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

def delayed_reboot():
    time.sleep(2)
    os.system("sudo reboot")

@app.route("/reboot")
def reboot():
    threading.Thread(target=delayed_reboot, daemon=True).start()
    return "Raspberry Pi vil starte på nytt om få sekunder."

@app.route("/settings_data")
def settings_data():
    return jsonify(sensor_settings)

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

if __name__ == "__main__":
    threading.Thread(target=update_sensor_data, daemon=True).start()
    threading.Thread(target=read_serial_from_arduino, daemon=True).start()
    threading.Thread(target=overvåk_for_hindring, daemon=True).start() 
    app.run(host="0.0.0.0", port=80)
