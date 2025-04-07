from flask import Flask, render_template, jsonify
from lidar_reader import start_lidar_thread, get_latest_scan

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scan')
def scan():
    return jsonify(get_latest_scan())

if __name__ == '__main__':
    start_lidar_thread()
    app.run(host='0.0.0.0', port=5000, debug=True)
