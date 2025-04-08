from rplidar import RPLidar, RPLidarException

PORT = '/dev/ttyUSB0'   # Endre hvis porten er annerledes
BAUD = 115200

lidar = None

try:
    print("🔄 Koble til og start LIDAR...\nTrykk Ctrl+C for å stoppe.\n")
    lidar = RPLidar(PORT, baudrate=BAUD)

    # Start skanning
    for i, scan in enumerate(lidar.iter_scans()):
        print(f"[Scan {i}] {len(scan)} målinger")
        for quality, angle, distance in scan:
            print(f"  Vinkel: {round(angle, 1)}°\tAvstand: {round(distance, 1)} mm\tKvalitet: {quality}")
        print("-" * 40)

except KeyboardInterrupt:
    print("\n🛑 Avbrutt av bruker.")

except RPLidarException as e:
    print(f"\n❌ RPLidar-feil: {e}")

except Exception as e:
    print(f"\n❌ Uventet feil: {e}")

finally:
    if lidar:
        print("🔌 Stopper og frakobler LIDAR...")
        try:
            lidar.stop()
            lidar.disconnect()
            print("✅ Ferdig.")
        except:
            print("⚠️ Kunne ikke stoppe LIDAR skikkelig.")

