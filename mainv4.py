from flask import Flask, request, render_template
import serial
import time
import threading
import RPi.GPIO as GPIO

# Flask-app
app = Flask(__name__)

# Seriell kommunikasjon med Arduino
SERIAL_PORT = "/dev/ttyACM0"  # Sjekk riktig port med `ls /dev/tty*`
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Vent til tilkobling er stabil
    print("Seriell tilkobling etablert!")
except Exception as e:
    print(f"Feil ved oppkobling til seriell port: {e}")
    ser = None

# GPIO-oppsett for ultralydsensor
TRIG_PIN = 17  # GPIO17 (Pinne 11)
ECHO_PIN = 27  # GPIO27 (Pinne 13)

GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)

# Funksjon for å måle avstand med HC-SR04
def mål_avstand():
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)  # 10µs puls
    GPIO.output(TRIG_PIN, False)

    start_tid, stopp_tid = 0, 0

    while GPIO.input(ECHO_PIN) == 0:
        start_tid = time.time()
    
    while GPIO.input(ECHO_PIN) == 1:
        stopp_tid = time.time()

    tid_forskjell = stopp_tid - start_tid
    avstand = (tid_forskjell * 34300) / 2  # Lydens hastighet i luft: 343 m/s
    return avstand

# Funksjon for å kontinuerlig måle avstand og skrive til terminal
def logg_avstand():
    while True:
        avstand = mål_avstand()
        print(f"Avstand: {avstand:.2f} cm")  # Skriver til terminal hvert 2. sekund
        time.sleep(2)

# Starter tråd for avstandsmålinger
måle_tråd = threading.Thread(target=logg_avstand, daemon=True)
måle_tråd.start()

# Flask-ruter
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/control")
def control():
    cmd = request.args.get("cmd", "")
    if cmd:
        response = send_to_arduino(cmd)
        print(response)
        return response
    return "Ingen kommando mottatt"

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=80)
    except KeyboardInterrupt:
        print("Avslutter program...")
        GPIO.cleanup()
