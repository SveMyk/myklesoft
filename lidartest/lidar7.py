from rplidar import RPLidar

PORT = '/dev/ttyUSB0'  # Juster om nødvendig

def main():
    lidar = RPLidar(PORT)

    try:
        print("📦 Enhetsinfo:")
        print(lidar.get_info())

        print("\n❤️ Helse:")
        print(lidar.get_health())

        print("\n📈 Starter skanning (scan_type='standard'):")
        for i, scan in enumerate(lidar.iter_scans(scan_type='standard')):
            print(f"[Scan {i}] {len(scan)} målinger")
            for quality, angle, distance in scan:
                print(f"  Vinkel: {round(angle,1)}°\tAvstand: {round(distance,1)} mm\tKvalitet: {quality}")
            print("-" * 40)
            if i >= 5:
                break

    except KeyboardInterrupt:
        print("\n🛑 Avbrutt av bruker.")
    finally:
        print("🧹 Stopper LIDAR...")
        lidar.stop()
        lidar.stop_motor()
        lidar.disconnect()
        print("✅ Ferdig.")

if __name__ == '__main__':
    main()
