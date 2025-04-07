from rplidar import RPLidar
import threading

PORT = '/dev/ttyUSB0'  # Juster hvis LIDAR er på annen port

scan_data = []
lock = threading.Lock()

def lidar_loop():
    global scan_data
    lidar = RPLidar(PORT)
    try:
        lidar.clean_input()              # 🔄 Tøm bufferen først
        time.sleep(0.5)                  # ⏳ Gi den tid til å våkne
        for scan in lidar.iter_scans(scan_type='normal'):
            with lock:
                scan_data = [
                    {'angle': round(angle, 1), 'distance': round(distance, 1)}
                    for (_, angle, distance) in scan
                    if distance > 0
                ]
    except Exception as e:
        print(f"🚨 LIDAR-feil: {e}")
    finally:
        print("🛑 Stopper LIDAR...")
        lidar.stop()
        lidar.stop_motor()
        lidar.disconnect()

def get_latest_scan():
    with lock:
        return scan_data.copy()

def start_lidar_thread():
    thread = threading.Thread(target=lidar_loop, daemon=True)
    thread.start()
