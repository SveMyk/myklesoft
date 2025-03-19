// Arduinov5 - Klar for fleksibel bevegelse og rotasjon via Raspberry Pi
// + IR-sensoravlesning sendt via Serial uten å blokkere motorrespons

// --- Konfigurerbare parametere ---
const float hjul_diameter_cm = 6.0;
const float hjul_radius_cm = hjul_diameter_mm / 2.0;
const float hjul_omkrets_cm = 2 * 3.1416 * hjul_radius_cm;

const float r_robot_cm = 11.0;
const float max_RPM = 115.0;
const float v_max_hjul_cm_per_s = (hjul_omkrets_cm * max_RPM) / 60.0;
const float omega_max_rad_per_s = v_max_hjul_cm_per_s / r_robot_cm;
const float omega_max_deg_per_s = omega_max_rad_per_s * (180.0 / 3.1416);

// --- Motorpinner ---
const int motor1_IN1 = 9;
const int motor1_IN2 = 10;
const int motor2_IN1 = 11;
const int motor2_IN2 = 12;
const int motor3_IN1 = 7;
const int motor3_IN2 = 8;
const int motor1_PWM = 5;
const int motor2_PWM = 6;
const int motor3_PWM = 3;

// --- IR-sensorer (D1, D3, D4, D6) på A0-A3 ---
const int sensorD1 = A0;
const int sensorD3 = A1;
const int sensorD4 = A2;
const int sensorD6 = A3;

// --- Variabler ---
const int pwmMax = 255;
const float pwmHastighet = 0.4 * pwmMax;
String kommando = "";

// --- Tid for IR-oppdatering ---
unsigned long forrigeIRtid = 0;
const unsigned long irOppdateringsIntervall = 500; // ms

void setup() {
  pinMode(motor1_IN1, OUTPUT); pinMode(motor1_IN2, OUTPUT);
  pinMode(motor2_IN1, OUTPUT); pinMode(motor2_IN2, OUTPUT);
  pinMode(motor3_IN1, OUTPUT); pinMode(motor3_IN2, OUTPUT);
  pinMode(motor1_PWM, OUTPUT); pinMode(motor2_PWM, OUTPUT); pinMode(motor3_PWM, OUTPUT);
  Serial.begin(115200);
}

void loop() {
  // --- Mottak av kommandoer fra RPi ---
  if (Serial.available()) {
    kommando = Serial.readStringUntil('\n');
    kommando.trim();

    if (kommando.startsWith("MOV:")) {
      float vx = 0, vy = 0, rotasjon = 0;

      int posX = kommando.indexOf("X=");
      int posY = kommando.indexOf("Y=");
      int posR = kommando.indexOf("R=");

      if (posX != -1) vx = kommando.substring(posX + 2, kommando.indexOf(",", posX)).toFloat();
      if (posY != -1) vy = kommando.substring(posY + 2, kommando.indexOf(",", posY)).toFloat();
      if (posR != -1) rotasjon = kommando.substring(posR + 2).toFloat();

      float omega = 0;
      int varighet = 0;

      if (rotasjon != 0) {
        omega = (rotasjon > 0) ? 1.0 : -1.0;
        varighet = abs(rotasjon) / omega_max_deg_per_s * 1000;
      }

      settHastighet(vx, vy, omega);

      if (rotasjon != 0 && vx == 0 && vy == 0) {
        delay(varighet);
        stoppMotorer();
      }
    }
  }

  // --- Skriv IR-verdier til Serial hvert 500 ms ---
  if (millis() - forrigeIRtid >= irOppdateringsIntervall) {
    int valD1 = analogRead(sensorD1);
    int valD3 = analogRead(sensorD3);
    int valD4 = analogRead(sensorD4);
    int valD6 = analogRead(sensorD6);

    Serial.print("IR ");
    Serial.print("D1:"); Serial.print(valD1); Serial.print(" ");
    Serial.print("D3:"); Serial.print(valD3); Serial.print(" ");
    Serial.print("D4:"); Serial.print(valD4); Serial.print(" ");
    Serial.print("D6:"); Serial.println(valD6);

    forrigeIRtid = millis();
  }
}

void settHastighet(float vx, float vy, float omega) {
  const float theta1 = 0;
  const float theta2 = 2.0944; // 120 grader i radianer
  const float theta3 = 4.1888; // 240 grader i radianer
  const float r = 1.0;

  float v1 = vx * sin(theta1) - vy * cos(theta1) - omega * r;
  float v2 = vx * sin(theta2) - vy * cos(theta2) - omega * r;
  float v3 = vx * sin(theta3) - vy * cos(theta3) - omega * r;

  float maxV = max(max(abs(v1), abs(v2)), abs(v3));
  if (maxV > 1) { v1 /= maxV; v2 /= maxV; v3 /= maxV; }

  settMotorHastighet(motor1_IN1, motor1_IN2, motor1_PWM, v1 * pwmHastighet);
  settMotorHastighet(motor2_IN1, motor2_IN2, motor2_PWM, v2 * pwmHastighet);
  settMotorHastighet(motor3_IN1, motor3_IN2, motor3_PWM, v3 * pwmHastighet);
}

void settMotorHastighet(int in1, int in2, int pwm, float hastighet) {
  if (hastighet > 0) {
    digitalWrite(in1, HIGH); digitalWrite(in2, LOW);
  } else if (hastighet < 0) {
    digitalWrite(in1, LOW); digitalWrite(in2, HIGH);
    hastighet = -hastighet;
  } else {
    digitalWrite(in1, LOW); digitalWrite(in2, LOW);
  }
  analogWrite(pwm, (int)hastighet);
}

void stoppMotorer() {
  settMotorHastighet(motor1_IN1, motor1_IN2, motor1_PWM, 0);
  settMotorHastighet(motor2_IN1, motor2_IN2, motor2_PWM, 0);
  settMotorHastighet(motor3_IN1, motor3_IN2, motor3_PWM, 0);
}
