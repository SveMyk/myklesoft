from flask import Flask, request
import smbus2
import time

# Oppsett av I2C
I2C_BUS = 1  # Vanligvis 1 på Raspberry Pi
ARDUINO_ADDRESS = 0x08
bus = smbus2.SMBus(I2C_BUS)

app = Flask(__name__)

def send_to_arduino(command):
    try:
        bus.write_i2c_block_data(ARDUINO_ADDRESS, 0, list(command.encode('utf-8')))
        print(f"Sendt til Arduino: {command}")
    except Exception as e:
        print(f"Feil ved sending til Arduino: {e}")

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Robotkontroll</title>
        <style>
            button { padding: 20px; font-size: 18px; margin: 10px; }
        </style>
    </head>
    <body>
        <h1>Robotkontroll</h1>
        <button onclick="sendCommand('xX+1')">X-pluss (Forover)</button>
        <button onclick="sendCommand('xX-1')">X-minus (Bakover)</button>
        <button onclick="sendCommand('xY+1')">Y-pluss (Venstre)</button>
        <button onclick="sendCommand('xY-1')">Y-minus (Høyre)</button>
        <button onclick="sendCommand('xCW')">Snu Høyre (CW)</button>
        <button onclick="sendCommand('xCCW')">Snu Venstre (CCW)</button>
        <button onclick="sendCommand('xSTOP')">Stopp</button>
        <script>
            function sendCommand(command) {
                fetch('/control?cmd=' + command);
            }
        </script>
    </body>
    </html>
    '''

@app.route('/control')
def control():
    command = request.args.get('cmd')
    if command:
        print(f"Mottatt kommando: {command}")
        send_to_arduino(command)
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
