from rplidar import RPLidar, RPLidarException

PORT = '/dev/ttyUSB0'   # Endre hvis du bruker annen port
BAUD = 115200

def main():
    print("🔄 Koble til og start LIDAR...\nTrykk Ctrl+C for å stoppe.\n")

    try:
        lidar = RPLidar(PORT, baudrate=BAUD)

        scan_count = 0
        current_scan = []

        for measurement in lidar.iter_measurments():
            new_scan, quality, angle, distance = measurement

            if new_scan:
                # Ny skannelinje starter
                if current_scan:
                    print(f"[Scan {scan_count}] {len(current_scan)} målinger")
                    for q, a, d in current_scan:
                        print(f"  Vinkel: {round(a,1)}°\tAvstand: {round(d,1)} mm\tKvalitet: {q}")
                    print("-" * 40)
                    current_scan = []
                    scan_count += 1

            current_scan.append((quality, angle, distance))

    except KeyboardInterrupt:
        print("\n🛑 Avbrutt av bruker.")

    except RPLidarException as e:
        print(f"\n❌ RPLidar-feil: {e}")

    except Exception as e:
        print(f"\n❌ Uventet feil: {e}")

    finally:
        try:
            print("🔌 Stopper og frakobler LIDAR...")
            lidar.stop()
            lidar.disconnect()
            print("✅ Ferdig.")
        except:
            print("⚠️ Klarte ikke stoppe LIDAR på vanlig måte.")

if __name__ == '__main__':
    main()
