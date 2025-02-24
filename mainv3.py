import time
import spidev
import RPi.GPIO as GPIO
from luma.lcd.device import pcd8544
from luma.core.interface.serial import spi
from luma.core.render import canvas
from PIL import ImageFont
from flask import Flask, request, render_template
import serial

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

# Konfigurer pins for LCD-skjerm
RST = 17  # GPIO 17
CE = 8    # SPI CE0
DC = 25   # GPIO 25
DIN = 10  # SPI MOSI
CLK = 11  # SPI SCLK

# Initialiser skjermen
serial = spi(port=0, device=0, gpio=GPIO, gpio_DC=DC, gpio_RST=RST)
lcd = pcd8544(serial, rotate=0)

# Bruk standard font
font = ImageFont.load_default()

def update_display(command):
    with canvas(lcd) as draw:
        draw.text((10, 20), f"Kommando:", font=font, fill=255)
        draw.text((10, 35), command, font=font, fill=255)

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
        # Send kommando til Arduino
        response = send_to_arduino(cmd)
        print(response)
        
        # Oppdater skjerm med kommandoen
        update_display(cmd)
        
        return response
    return "Ingen kommando mottatt"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
