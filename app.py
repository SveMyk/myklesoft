from flask import Flask, render_template, jsonify
from rplidar import RPLidar
import threading
import time

app = Flask(__name__)
lidar = RPLidar('/dev/ttyUSB0')  # Endre port om nødvendig

scan_data = []
robot_is_moving = False  # Du kan senere hente dette fra motorstatus
