from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <html>
        <head><title>GASSO Kontroll</title></head>
        <body>
            <h1>Velkommen til GASSO</h1>
            <button onclick="sendCommand('xX+1')">Forover</button>
            <button onclick="sendCommand('xX-1')">Bakover</button>
            <button onclick="sendCommand('xY+1')">Venstre</button>
            <button onclick="sendCommand('xY-1')">Høyre</button>
            <button onclick="sendCommand('xCW')">Rotér CW</button>
            <button onclick="sendCommand('xCCW')">Rotér CCW</button>
            <button onclick="sendCommand('xSTOP')">Stopp</button>
            <script>
                function sendCommand(command) {
                    fetch('/control?cmd=' + command);
                }
            </script>
        </body>
    </html>
    """

@app.route("/control")
def control():
    cmd = request.args.get("cmd", "")
    if cmd:
        print(f"Mottatt kommando: {cmd}")  # Her kan du sende til Arduino via I2C
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
