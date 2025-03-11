from flask import Flask, request, render_template
import serial
import time
import threading
import RPi.GPIO as GPIO

# GPIO-oppsett for HC-SR04 (valgfritt om du vil bruke det videre)
TRIG_PIN = 17
ECHO_PIN = 27
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# Seriell kommunikasjon med Arduino
SERIAL_PORT = "/dev/ttyACM0"  # Endre ved behov
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("[INFO] Seriell tilkobling etablert!")
except Exception as e:
    print(f"[ERROR] Seriell oppkobling feilet: {e}")
    ser = None

# Funksjon for å sende kommando til Arduino
def send_to_arduino(command):
    if ser and ser.is_open:
        ser.write((command + "\n").encode())
        print(f"[SENDT TIL ARDUINO] {command}")
        return f"Kommando sendt: {command}"
    else:
        return "Seriell port ikke tilgjengelig"

# Flask-app
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/control")
def control():
    try:
        x = float(request.args.get("x", 0))
        y = float(request.args.get("y", 0))
        r = float(request.args.get("r", 0))

        cmd = f"MOV:X={x},Y={y},R={r}"
        response = send_to_arduino(cmd)
        return response
    except Exception as e:
        return f"[ERROR] Feil i mottak av parametere: {e}"

@app.route("/distance")
def distance():
    distance_cm = get_distance()
    return {"distance": distance_cm}

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
        dist = get_distance()
        print(f"[AVSTAND] {dist} cm")
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=log_distance, daemon=True).start()
    app.run(host="0.0.0.0", port=80)
