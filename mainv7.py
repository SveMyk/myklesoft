from flask import Flask, request, render_template, jsonify
import serial
import time
import os
import threading
import RPi.GPIO as GPIO

# Sensoroppsett for HC-SR04
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

# Seriell tilkobling til Arduino
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Seriell tilkobling etablert!")
except Exception as e:
    print(f"Feil ved seriell tilkobling: {e}")
    ser = None

sensor_data = {"left": 0.0, "mid": 0.0, "right": 0.0}
ir_sensor_data = {"D1": 0, "D3": 0, "D4": 0, "D6": 0}
battery_level = 78
linje_status = "Søker etter linje"
navigasjon_aktiv = False

def send_to_arduino(command):
    if ser and ser.is_open:
        ser.write((command + "\n").encode())
        print(f"[SENDT] {command}")
        return f"Kommando sendt: {command}"
    return "Seriell port ikke tilgjengelig"

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
            except Exception as e:
                print(f"[SERIAL ERROR] {e}")

def linjenavigasjon():
    global linje_status, navigasjon_aktiv
    linje_status = "Søker etter linje"
    siste_tid_linje = None
    start_tid = time.time()
    navigasjon_aktiv = True

    while navigasjon_aktiv:
        d3 = ir_sensor_data["D3"]
        d4 = ir_sensor_data["D4"]
        d1 = ir_sensor_data["D1"]
        d6 = ir_sensor_data["D6"]

        MIN = 200
        MAX = 600

        d3_detect = MIN <= d3 <= MAX
        d4_detect = MIN <= d4 <= MAX
        d1_detect = MIN <= d1 <= MAX
        d6_detect = MIN <= d6 <= MAX

        if d3_detect or d4_detect:
            siste_tid_linje = time.time()
            linje_status = "Linje detektert"
            if d3_detect and d4_detect:
                send_to_arduino("MOV:X=0,Y=1,R=0")
            elif d3_detect and not d4_detect:
                send_to_arduino("MOV:X=0,Y=1,R=5")
            elif d4_detect and not d3_detect:
                send_to_arduino("MOV:X=0,Y=1,R=-5")
        else:
            linje_status = "Søker etter linje"
            if d1_detect:
                send_to_arduino("MOV:X=0,Y=1,R=-15")
            elif d6_detect:
                send_to_arduino("MOV:X=0,Y=1,R=15")

        if not siste_tid_linje and time.time() - start_tid > 10:
            send_to_arduino("MOV:X=0,Y=0,R=0")
            linje_status = "Ingen linje detektert"
            navigasjon_aktiv = False
            break

        if siste_tid_linje and time.time() - siste_tid_linje > 5:
            send_to_arduino("MOV:X=0,Y=0,R=0")
            linje_status = "Ingen linje detektert"
            navigasjon_aktiv = False
            break

        time.sleep(0.25)

app = Flask(__name__)

@app.route("/")
def index(): return render_template("index.html")

@app.route("/manual")
def manual(): return render_template("manual.html")

@app.route("/line")
def line(): return render_template("linjenavigasjon.html")

@app.route("/auto")
def auto(): return render_template("autonom.html")

@app.route("/control")
def control():
    cmd = request.args.get("cmd")
    if cmd: return send_to_arduino(cmd)
    return "Ingen kommando mottatt"

@app.route("/sensors")
def sensors():
    rounded_data = {k: int(round(v)) for k, v in sensor_data.items()}
    return jsonify(rounded_data)

@app.route("/battery")
def battery(): return jsonify({"level": battery_level})

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

if __name__ == "__main__":
    threading.Thread(target=update_sensor_data, daemon=True).start()
    threading.Thread(target=read_serial_from_arduino, daemon=True).start()
    app.run(host="0.0.0.0", port=80)
