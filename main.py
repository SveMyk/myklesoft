from flask import Flask, request, render_template
import smbus

app = Flask(__name__)

# Sett opp I2C-kommunikasjon
I2C_BUS = 1
ARDUINO_ADDR = 0x08
bus = smbus.SMBus(I2C_BUS)

def send_to_arduino(command):
    try:
        data = [ord(c) for c in command]  # Konverterer til ASCII-verdier
        bus.write_i2c_block_data(ARDUINO_ADDR, 0, data)
        return f"Kommando sendt: {command}"
    except Exception as e:
        return f"Feil ved sending til Arduino: {e}"

@app.route("/")
def home():
    return render_template("index.html")  # Laster HTML fra templates/index.html

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
