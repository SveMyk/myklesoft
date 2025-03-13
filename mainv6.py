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
ir_sensor_data = {"D1": 0, "D3": 0, "D4": 0, "D6": 0}
battery_level = 78  # Dummy-verdi

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
        time.sleep(0.25)

def read_serial_from_arduino():
    while True:
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode().strip()
                if line.startswith("IR"):
                    # Eksempel: IR D1:420 D3:435 D4:440 D6:410
                    parts = line[3:].strip().split()
                    for part in parts:
                        if ':' in part:
                            key, val = part.split(":")
                            if key in ir_sensor_data:
                                ir_sensor_data[key] = int(val)
                    print("[IR-SENSORER]", ir_sensor_data)
            except Exception as e:
                print(f"[SERIAL ERROR] {e}")

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

@app.route("/ir_data")
def ir_data():
    return jsonify(ir_sensor_data)

# ==== Start Flask-server ====
if __name__ == "__main__":
    thread_ultrasonic = threading.Thread(target=update_sensor_data, daemon=True)
    thread_irserial = threading.Thread(target=read_serial_from_arduino, daemon=True)

    thread_ultrasonic.start()
    thread_irserial.start()

    app.run(host="0.0.0.0", port=80)
