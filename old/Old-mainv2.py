from flask import Flask, request, render_template
import serial
import time

app = Flask(__name__)

# Sett opp seriell kommunikasjon med Arduino
SERIAL_PORT = "/dev/ttyUSB0"  # Bytt til riktig port, f.eks. "/dev/ttyAMA0" eller "/dev/ttyACM0"
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Vent til tilkobling er stabil
    print("Seriell tilkobling etablert!")
except Exception as e:
    print(f"Feil ved oppkobling til seriell port: {e}")
    ser = None

def send_to_arduino(command):
    if ser and ser.is_open:
        ser.write((command + "\n").encode())  # Send kommando med newline
        return f"Kommando sendt: {command}"
    else:
        return "Seriell port ikke tilgjengelig"

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
    app.run(host="0.0.0.0", port=80)
