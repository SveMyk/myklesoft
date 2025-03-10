from flask import Flask, request, render_template, jsonify
import serial
import time
import threading
import RPi.GPIO as GPIO

# ==== HC-SR04 Ultrasonisk Sensor GPIO ====
TRIG_PIN = 17  # GPIO17 (Pinne 11)
ECHO_PIN = 27  # GPIO27 (Pinne 13)

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# ==== Serielt mot Arduino ====
SERIAL_PORT = "/dev/ttyACM0"  # Endre ved behov
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Seriell tilkobling etablert!")
except Exception as e:
    print(f"Feil ved seriell tilkobling: {e}")
    ser = None

# ==== Globale variabler ====
sensor_data = {"left": 0.0, "mid": 0.0, "right": 0.0}
battery_level = 78  # Simulert batterinivå

# ==== Funksjoner ====
def send_to_arduino(command):
    if ser and ser.is_open:
        ser.write((command + "\n").encode())
        return f"Kommando sendt: {command}"
    else:
        return "Seriell port ikke tilgjengelig"

def get_distance():
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    start_time = time.time()
    stop_time = time.time()

    while GPIO.input(ECHO_PIN) == 0:
        start_time = time.time()
    while GPIO.input(ECHO_PIN) == 1:
        stop_time = time.time()

    elapsed_time = stop_time - start_time
    distance = (elapsed_time * 34300) / 2
    return round(distance, 2)

def log_distance():
    while True:
        sensor_data["mid"] = get_distance()
        sensor_data["left"] = sensor_data["mid"] + 2.5
        sensor_data["right"] = sensor_data["mid"] - 2.5
        print(f"[Sensorer] V: {sensor_data['left']}  M: {sensor_data['mid']}  H: {sensor_data['right']}")
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
    cmd = request.args.get("cmd", "")
    if cmd:
        return send_to_arduino(cmd)
    return "Ingen kommando mottatt"

@app.route("/battery")
def battery():
    return jsonify({"level": battery_level})

@app.route("/sensors")
def sensors():
    return jsonify(sensor_data)

@app.route("/distance")
def distance():
    avstand = get_distance()
    return jsonify({"distance": avstand})

# ==== Start Flask-server ====
if __name__ == "__main__":
    distance_thread = threading.Thread(target=log_distance, daemon=True)
    distance_thread.start()
    app.run(host="0.0.0.0", port=80)
