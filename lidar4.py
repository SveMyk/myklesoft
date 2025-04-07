from rplidar import RPLidar, RPLidarException

# Konfigurasjon
PORT = '/dev/ttyUSB0'    # Juster hvis din port er annerledes
BAUD = 115200

def main():
    print("🔄 Koble til og start LIDAR...\nTrykk Ctrl+C for å stoppe.\n")
    
    try:
        lidar = RPLidar(PORT, baudrate=BAUD)

        # Start skanning med riktig skannetype for A1
        for i, scan in enumerate(lidar.iter_scans(scan_type='standard')):
            print(f"[Scan {i}] ({len(scan)} målinger)")
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
        try:
            print("🔌 Stopper og frakobler LIDAR...")
            lidar.stop()
            lidar.disconnect()
            print("✅ Ferdig.")
        except:
            print("⚠️ Klarte ikke stoppe LIDAR på vanlig måte.")

if __name__ == '__main__':
    main()
