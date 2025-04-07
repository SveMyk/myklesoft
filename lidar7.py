from rplidar import RPLidar

PORT = '/dev/ttyUSB0'  # Juster hvis du bruker en annen port

def main():
    print("🔄 Starter LIDAR-test med RPLidar A1M8")

    lidar = RPLidar(PORT)

    try:
        # Enhetsinfo
        info = lidar.get_info()
        print("📦 Info:", info)

        # Helsekontroll
        health = lidar.get_health()
        print("❤️ Health:", health)

        # Start skanning
        print("\n🔁 Starter skanning (10 omganger)...\n")
        for i, scan in enumerate(lidar.iter_scans()):
            print(f"{i}: Got {len(scan)} measurements")
            if i > 10:
                break

    except KeyboardInterrupt:
        print("\n🛑 Avbrutt av bruker.")

    except Exception as e:
        print(f"\n❌ Feil under kjøring: {e}")

    finally:
        print("\n🧹 Stopper og frakobler...")
        try:
            lidar.stop()
            lidar.stop_motor()
            lidar.disconnect()
            print("✅ LIDAR avsluttet korrekt.")
        except:
            print("⚠️ Klarte ikke stoppe LIDAR helt.")

if __name__ == '__main__':
    main()
