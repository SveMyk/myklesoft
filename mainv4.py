from flask import Flask, request, render_template
import serial
import time
import threading
import RPi.GPIO as GPIO

# Sett opp GPIO for HC-SR04 ultralydsensor
TRIG_PIN = 17  # GPIO17 (Pinne 11)
ECHO_PIN = 27  # GPIO27 (Pinne 13)

GPIO.setwarnings(False)  # Slår av advarsler
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# Sett opp seriell kommunikasjon med Arduino
SERIAL_PORT = "/dev/ttyACM0"  # Endre hvis nødvendig
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Vent til tilkobling er stabil
    print("Seriell tilkobling etablert!")
except Exception as e:
    print(f"Feil ved oppkobling til seriell port: {e}")
    ser = None

def send_to_arduino(command):
    """Sender kommando til Arduino via seriell kommunikasjon."""
    if ser and ser.is_open:
        ser.write((command + "\n").encode())
        return f"Kommando sendt: {command}"
    else:
        return "Seriell port ikke tilgjengelig"

def get_distance():
    """Måler avstand med HC-SR04."""
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)  # 10µs puls til trigger
    GPIO.output(TRIG_PIN, False)

    start_time = time.time()
    stop_time = time.time()

    while GPIO.input(ECHO_PIN) == 0:
        start_time = time.time()

    while GPIO.input(ECHO_PIN) == 1:
        stop_time = time.time()

    elapsed_time = stop_time - start_time
    distance = (elapsed_time * 34300) / 2  # Lydens hastighet i luft

    return round(distance, 2)  # Avstand i cm

def log_distance():
    """Logger avstandsdata til terminalen hvert sekund."""
    while True:
        avstand = get_distance()
        print(f"[AVSTAND]: {avstand} cm")
        time.sleep(1)

# Start Flask-server
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/control")
def control():
    """Behandler kommandoer fra webgrensesnittet."""
    cmd = request.args.get("cmd", "")
    if cmd:
        response = send_to_arduino(cmd)
        print(response)
        return response
    return "Ingen kommando mottatt"

@app.route("/distance")
def distance():
    """Returnerer avstandsmåling fra ultralydsensoren."""
    avstand = get_distance()
    print(f"[FLASK API] Avstand: {avstand} cm")  # Skriver til terminalen for debugging
    return {"distance": avstand}  # Returnerer JSON-respons

if __name__ == "__main__":
    # Start tråd for avstandslogging i terminalen
    distance_thread = threading.Thread(target=log_distance, daemon=True)
    distance_thread.start()

    # Start Flask-serveren
    app.run(host="0.0.0.0", port=80)
