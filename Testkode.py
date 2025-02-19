# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 10:52:52 2024

@author: mykle
"""
import numpy as np
import matplotlib.pyplot as plt

# Be om brukerinput
x = float(input("Skriv inn x-koordinaten for vektor A: "))
y = float(input("Skriv inn y-koordinaten for vektor A: "))
angle_step = float(input("Skriv inn vinkelsteg (i grader) for hver rotasjon: "))

# Beregn lengden på vektor A
length_A = np.sqrt(x**2 + y**2)
print(f"Lengden på vektor A er: {length_A:.2f}")

# Initialiser vektor A og startvinkelen
vector_A = np.array([x, y])
current_angle = 0

# Start figur for plotting
plt.figure()
plt.quiver(0, 0, vector_A[0], vector_A[1], angles='xy', scale_units='xy', scale=1, color='blue', 
           label=f"Vektor A (lengde={length_A:.2f})\nEndepunkt=({vector_A[0]:.2f}, {vector_A[1]:.2f})")
plt.plot(vector_A[0], vector_A[1], 'bo')  # Markør for første vektor

# Iterer og plott vektorer til vi når 360 grader
while current_angle < 360:
    # Konverter vinkel til radianer
    angle_rad = np.radians(current_angle)
    
    # Rotasjonsmatrise for 2D-plan
    rotation_matrix = np.array([[np.cos(angle_rad), -np.sin(angle_rad)],
                                [np.sin(angle_rad), np.cos(angle_rad)]])
    
    # Roter vektor A
    rotated_vector = rotation_matrix @ vector_A
    
    # Plot den roterte vektoren
    plt.quiver(0, 0, rotated_vector[0], rotated_vector[1], angles='xy', scale_units='xy', scale=1, color='red', 
               alpha=0.5)  # Bruk gjennomsiktighet for flere vektorer
    plt.plot(rotated_vector[0], rotated_vector[1], 'ro', alpha=0.5)  # Markør for endepunkt

    # Oppdater vinkel
    current_angle += angle_step

# Plotinnstillinger
plt.xlim(-length_A - 1, length_A + 1)
plt.ylim(-length_A - 1, length_A + 1)
plt.axhline(0, color='black', linewidth=0.5)
plt.axvline(0, color='black', linewidth=0.5)
plt.xlabel("X-akse")
plt.ylabel("Y-akse")
plt.title("Rotasjon av en 2D-vektor med flere vinkelsteg")

# Legg til legend utenfor plottet
plt.legend(loc='upper left', bbox_to_anchor=(1, 1))
plt.grid()
plt.gca().set_aspect('equal', adjustable='box')
plt.show()

