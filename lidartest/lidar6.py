from rplidar import RPLidar, RPLidarException

PORT = '/dev/ttyUSB0'  # Juster hvis du bruker annen port
BAUD = 115200

def main():
    print("🔧 Starter lavnivå LIDAR-lesing...\nTrykk Ctrl+C for å stoppe.\n")

    try:
        lidar = RPLidar(PORT, baudrate=BAUD)
        lidar.start_motor()
        lidar.start()

        for i, measurement in enumerate(lidar.iter_measurments()):
            new_scan, quality, angle, distance = measurement
            print(f"#{i}: Vinkel={round(angle, 1)}°\tAvstand={round(distance, 1)} mm\tKvalitet={quality}")

    except KeyboardInterrupt:
        print("\n🛑 Avbrutt av bruker.")

    except RPLidarException as e:
        print(f"\n❌ RPLidar-feil: {e}")

    except Exception as e:
        print(f"\n❌ Uventet feil: {e}")

    finally:
        try:
            print("🛑 Stopper motor og frakobler...")
            lidar.stop()
            lidar.stop_motor()
            lidar.disconnect()
            print("✅ Ferdig.")
        except:
            print("⚠️ Kunne ikke stoppe LIDAR normalt.")

if __name__ == '__main__':
    main()
