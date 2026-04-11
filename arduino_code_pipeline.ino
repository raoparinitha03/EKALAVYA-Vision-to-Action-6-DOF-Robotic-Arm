#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// Channels
#define C4_WAIST 4
#define C5_SHDR  5
#define C6_ELBW  6
#define C7_ROLL  7
#define C8_PTCH  8
#define C9_GRP   9

// Pulse conversion
int mg(int d) { return map(d, 0, 180, 150, 600); }
int sg(int d) { return map(d, 0, 180, 130, 520); }

void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(50);
  set_home();
  Serial.println("SYSTEM_READY");
}

void set_home() {
  // Set all to 90 degrees as requested
  pwm.setPWM(C4_WAIST, 0, mg(90));
  pwm.setPWM(C5_SHDR,  0, mg(60));
  pwm.setPWM(C6_ELBW,  0, mg(90));
  pwm.setPWM(C7_ROLL,  0, sg(90));
  pwm.setPWM(C8_PTCH,  0, sg(90));
  pwm.setPWM(C9_GRP,   0, sg(90)); // Closed
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd == 'S') { 
      int targetWaist = Serial.parseInt();
      String label = Serial.readStringUntil('\n');
      label.trim();

      // 1. POINT TO OBJECT (WAIST ONLY)
      pwm.setPWM(C4_WAIST, 0, mg(targetWaist));
      delay(1000);

      // 2. PICK POSITION (DROP ARM)
      pwm.setPWM(C9_GRP,   0, sg(90));  // Open Gripper
      pwm.setPWM(C5_SHDR,  0, mg(0));  // Shoulder to 20
      pwm.setPWM(C6_ELBW,  0, mg(120)); // Elbow to 120
      pwm.setPWM(C8_PTCH,  0, sg(60));  // Pitch to 80
      delay(10000); // Wait for human handover

      // 3. GRAB
      pwm.setPWM(C9_GRP,   0, sg(60)); // Close Gripper
      delay(2000);

      // 4. LIFT
      pwm.setPWM(C5_SHDR,  0, mg(90));  // Lift shoulder to 70
      delay(2000);

      // 5. ROTATE TO BIN
      if (label == "cylinder") {
        pwm.setPWM(C4_WAIST, 0, mg(45));
      } else {
        pwm.setPWM(C4_WAIST, 0, mg(135));
      }
      delay(1500);

      // 6. DROP 
      pwm.setPWM(C8_PTCH,  0, sg(0));   // Drop wrist
      delay(1000);
      pwm.setPWM(C9_GRP,   0, sg(90));  // Release
      delay(2000);

      // 7. RETURN HOME & SIGNAL PI
      set_home();
      delay(2000);
      Serial.println("DONE"); 
    }
  }
}