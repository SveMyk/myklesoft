// Arduinov5 - Fullversjon med bevegelse og IR-sensoravlesning

// --- Konfigurerbare parametere ---
const float hjul_diameter_mm = 60.0;
const float hjul_radius_cm = hjul_diameter_mm / 20.0;
const float hjul_omkrets_cm = 2 * 3.1416 * hjul_radius_cm;

const float r_robot_cm = 11.0;
const float max_RPM = 115.0;
const float v_max_hjul_cm_per_s = (hjul_omkrets_cm * max_RPM) / 60.0;
const float omega_max_rad_per_s = v_max_hjul_cm_per_s / r_robot_cm;

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

// --- IR-sensorer (D1, D3, D4, D6) ---
const int sensorD1 = A0;
const int sensorD3 = A1;
const int sensorD4 = A2;
const int sensorD6 = A3;

// --- Variabler ---
const int pwmMax = 255;
const float PWM_BASE = 0.4 * pwmMax;
const float OMEGA_SCALE = 0.5;
String kommando = "";

unsigned long forrigeIRtid = 0;
const unsigned long irOppdateringsIntervall = 200;

void setup() {
  pinMode(motor1_IN1, OUTPUT); pinMode(motor1_IN2, OUTPUT);
  pinMode(motor2_IN1, OUTPUT); pinMode(motor2_IN2, OUTPUT);
  pinMode(motor3_IN1, OUTPUT); pinMode(motor3_IN2, OUTPUT);
  pinMode(motor1_PWM, OUTPUT); pinMode(motor2_PWM, OUTPUT); pinMode(motor3_PWM, OUTPUT);
  Serial.begin(115200);
}

void loop() {
  if (Serial.available()) {
    kommando = Serial.readStringUntil('\n');
    kommando.trim();

    if (kommando.startsWith("MOV:")) {
      float vx = 0, vy = 0, omega = 0;
      int posX = kommando.indexOf("X=");
      int posY = kommando.indexOf("Y=");
      int posR = kommando.indexOf("R=");
      if (posX != -1) vx = kommando.substring(posX + 2, kommando.indexOf(',', posX)).toFloat();
      if (posY != -1) vy = kommando.substring(posY + 2, kommando.indexOf(',', posY)).toFloat();
      if (posR != -1) omega = kommando.substring(posR + 2).toFloat();
      settHastighet(vx, vy, omega);
    } else if (kommando == "STOP") {
      stoppMotorer();
    }
  }

  // --- Send IR-sensorverdier hvert 500 ms ---
  if (millis() - forrigeIRtid >= irOppdateringsIntervall) {
    int ir1 = analogRead(sensorD1);
    int ir3 = analogRead(sensorD3);
    int ir4 = analogRead(sensorD4);
    int ir6 = analogRead(sensorD6);
    Serial.print("IR:");
    Serial.print(ir1); Serial.print(",");
    Serial.print(ir3); Serial.print(",");
    Serial.print(ir4); Serial.print(",");
    Serial.println(ir6);
    forrigeIRtid = millis();
  }
}

void settHastighet(float vx, float vy, float omega) {
  const float theta1 = 0;
  const float theta2 = 120 * (PI / 180);
  const float theta3 = 240 * (PI / 180);
  const float r = 1.0;

  float v1 = vx * sin(theta1) - vy * cos(theta1) - omega * r * OMEGA_SCALE;
  float v2 = vx * sin(theta2) - vy * cos(theta2) - omega * r * OMEGA_SCALE;
  float v3 = vx * sin(theta3) - vy * cos(theta3) - omega * r * OMEGA_SCALE;

  float maxV = max(max(abs(v1), abs(v2)), abs(v3));
  if (maxV > 1.0) {
    v1 /= maxV;
    v2 /= maxV;
    v3 /= maxV;
  }

  settMotorHastighet(motor1_IN1, motor1_IN2, motor1_PWM, v1 * PWM_BASE);
  settMotorHastighet(motor2_IN1, motor2_IN2, motor2_PWM, v2 * PWM_BASE);
  settMotorHastighet(motor3_IN1, motor3_IN2, motor3_PWM, v3 * PWM_BASE);
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
  analogWrite(pwm, constrain((int)hastighet, 0, pwmMax));
}

void stoppMotorer() {
  settMotorHastighet(motor1_IN1, motor1_IN2, motor1_PWM, 0);
  settMotorHastighet(motor2_IN1, motor2_IN2, motor2_PWM, 0);
  settMotorHastighet(motor3_IN1, motor3_IN2, motor3_PWM, 0);
}
