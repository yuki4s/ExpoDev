#include <DynamixelShield.h>

#define BAUDRATE         57600
#define PROTOCOL_VERSION 2.0

DynamixelShield dxl;

const uint8_t  DXL_ID1        = 1;
const uint8_t  DXL_ID2        = 2;
const uint16_t BASE_POSITION  = 1000;
const uint16_t ALT_POSITION   = 2000;
const uint16_t DEPTH_TRIGGER  = 250;

bool    isMoving    = false;
int     lastCond    = -1;     // -1: 起動時、1: Cond=1、2 or 3: Cond=2,3
bool    prevBelow   = false;  // 前回 depth ≤ DEPTH_TRIGGER だったか

float   measuredVoltageA0 = 0.0;
float   measuredVoltageA2 = 0.0;

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // A0〜A5 を内部 1.1V リファレンス基準に
  analogReference(AR_INTERNAL);

  // 乱数シード（A3 を浮遊入力に）
  randomSeed( analogRead(A3) );

  dxl.begin(BAUDRATE);
  dxl.setPortProtocolVersion(PROTOCOL_VERSION);

  dxl.torqueOff(DXL_ID1);
  dxl.torqueOff(DXL_ID2);
  dxl.setOperatingMode(DXL_ID1, OP_POSITION);
  dxl.setOperatingMode(DXL_ID2, OP_POSITION);
  dxl.torqueOn(DXL_ID1);
  dxl.torqueOn(DXL_ID2);

  dxl.setGoalPosition(DXL_ID1, BASE_POSITION);
  dxl.setGoalPosition(DXL_ID2, BASE_POSITION);

  Serial.println("Dynamixel Ready");
}

void loop() {
  // ─── A0: 電圧測定 ───
  int raw0 = analogRead(A0);
  measuredVoltageA0 = raw0 * (1.1 / 1023.0);
  if (measuredVoltageA0 > 1.1) measuredVoltageA0 = 1.1;

  // ─── A2: 水位センサ読み取り ───
  int raw2 = analogRead(A2);
  measuredVoltageA2 = raw2 * (1.1 / 1023.0);
  if (measuredVoltageA2 > 1.1) measuredVoltageA2 = 1.1;

  if (measuredVoltageA2 > 0.5) Serial.print("Water detected");

  // ─── シリアルコマンド処理 ───
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  if (cmd.length() == 0) return;

  Serial.print("受信: ");
  Serial.println(cmd);

  if (cmd.equalsIgnoreCase("reset")) {
    // リセット
    dxl.setGoalPosition(DXL_ID1, BASE_POSITION);
    dxl.setGoalPosition(DXL_ID2, BASE_POSITION);
    isMoving  = false;
    lastCond  = -1;
    prevBelow = false;
    Serial.println("→ Reset: both motors to BASE_POSITION");
  }
  else if (cmd.indexOf("Cond:") != -1) {
    // Cond:X の数字を抽出して保存
    int idx = cmd.indexOf("Cond:") + 5;
    lastCond = cmd.substring(idx).toInt();
    Serial.print("→ Cond value saved: ");
    Serial.println(lastCond);
  }
  else if (cmd.startsWith("Depth:")) {
    float depth = cmd.substring(6).toFloat();
    Serial.print("→ Depth received: ");
    Serial.println(depth, 1);

    bool below      = (depth <= DEPTH_TRIGGER);
    bool risingEdge = (!below && prevBelow);  // 閾値以下→超過
    bool fallingEdge= (below && !prevBelow);  // 閾値超過→以下

    if (!isMoving) {
      isMoving = true;

      // ─── 閾値以下→超過 または 閾値超過→以下 のときだけ動作 ───
      if (risingEdge || fallingEdge) {
        if (risingEdge) {
          // 超過した瞬間：ID1→BASE_POSITION
          Serial.println("→ Rising edge: Move ID1 to BASE_POSITION");
          dxl.setGoalPosition(DXL_ID1, BASE_POSITION);
          delay(500);

          // Cond が 2 or 3 のときのみ、ID2 をトグル
          if (lastCond == 2 || lastCond == 3) {
            int toggleCount = random(2, 5);     // 2～4 回
            int delayMs     = random(300, 501); // 300～500 ms
            Serial.print("→ ID2 Toggles: ");
            Serial.println(toggleCount);
            Serial.print("→ ID2 delayMs: ");
            Serial.println(delayMs);
            for (int i = 0; i < toggleCount; i++) {
              dxl.setGoalPosition(DXL_ID2, ALT_POSITION);
              delay(delayMs);
              dxl.setGoalPosition(DXL_ID2, BASE_POSITION);
              delay(delayMs);
            }
          }
        }
        else { // fallingEdge
          // 以下になった瞬間：ID1→0
          Serial.println("→ Falling edge: Move ID1 to 0");
          dxl.setGoalPosition(DXL_ID1, 0);
          delay(500);
        }
      }
      else {
        Serial.println("→ No edge: no action");
      }

      isMoving = false;
      while (Serial.available()) Serial.read();  // 余分なバッファ捨て
      Serial.println("→ Action complete");
    }
    else {
      Serial.println("→ Busy, ignored");
    }

    prevBelow = below;
  }
  else {
    Serial.println("→ Unknown command");
  }
}
