from flask import Flask, request, render_template, jsonify
import serial
import time
import threading
import RPi.GPIO as GPIO

# ==== GPIO-OPPSETT FOR 3x HC-SR04 ====
SENSORS = {
    "left":  {"TRIG": 17, "ECHO": 27},
    "mid":   {"TRIG": 22, "ECHO": 23},
    "right": {"TRIG": 24, "ECHO": 25}
}

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
for sensor in SENSORS.values():
    GPIO.setup(sensor["TRIG"], GPIO.OUT)
    GPIO.setup(sensor["ECHO"], GPIO.IN)

# ==== Serielt mot Arduino ====
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Seriell tilkobling etablert!")
except Exception as e:
    print(f"Feil ved seriell tilkobling: {e}")
    ser = None

# ==== Globale data ====
sensor_data = {"left": 0.0, "mid": 0.0, "right": 0.0}
battery_level = 78  # Dummy verdi

# ==== Funksjoner ====
def send_to_arduino(command):
    if ser and ser.is_open:
        ser.write((command + "\n").encode())
        print(f"[SENDT] {command}")
        return f"Kommando sendt: {command}"
    else:
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
    return round(distance, 2)

def update_sensor_data():
    while True:
        for key, pins in SENSORS.items():
            try:
                sensor_data[key] = get_distance(pins["TRIG"], pins["ECHO"])
            except:
                sensor_data[key] = 0.0
        print(f"[ULTRALYD] V: {sensor_data['left']}  M: {sensor_data['mid']}  H: {sensor_data['right']}")
        time.sleep(1)

# ==== Flask Webserver ====
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/manual")
def manual():
    return render_template("manual.html")

@app.route("/line")
def linjenavigasjon():
    return render_template("linjenavigasjon.html")

@app.route("/auto")
def autonom():
    return render_template("autonom.html")

@app.route("/control")
def control():
    # Ny: Støtte for både "cmd" og MOV:X/Y/R-parametre
    cmd = request.args.get("cmd")
    if cmd:
        return send_to_arduino(cmd)

    try:
        x = float(request.args.get("x", 0))
        y = float(request.args.get("y", 0))
        r = float(request.args.get("r", 0))
        mov_cmd = f"MOV:X={x},Y={y},R={r}"
        return send_to_arduino(mov_cmd)
    except Exception as e:
        return f"Feil i mottak av parametere: {e}"

@app.route("/battery")
def battery():
    return jsonify({"level": battery_level})

@app.route("/sensors")
def sensors():
    return jsonify(sensor_data)

@app.route("/distance")
def distance():
    return jsonify({"distance": sensor_data["mid"]})

# ==== Start Flask-server ====
if __name__ == "__main__":
    sensor_thread = threading.Thread(target=update_sensor_data, daemon=True)
    sensor_thread.start()
    app.run(host="0.0.0.0", port=80)
