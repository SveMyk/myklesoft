from rplidar import RPLidar 

PORT = '/dev/ttyUSB0'  # Juster hvis porten er annerledes 

lidar = RPLidar(None, PORT) 

try: 

    print("Starter LIDAR-lesing...\nTrykk Ctrl+C for å stoppe.\n") 

    for i, scan in enumerate(lidar.iter_scans()): 

        print(f"[Scan {i}]") 

        for quality, angle, distance in scan: 

            print(f"Vinkel: {round(angle,1)}°\tAvstand: {round(distance,1)} cm") 

        print("-" * 40) 

except KeyboardInterrupt: 

    print("Avslutter...") 

finally: 

    lidar.stop() 

    lidar.disconnect() 

 
