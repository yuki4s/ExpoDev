#include <AccelStepper.h>
#include <EEPROM.h>
#include <DynamixelShield.h>
#include <math.h>    // sin(), fmod(), PI

// ───── 定数定義 ─────
#define BAUDRATE              57600
#define PROTOCOL_VERSION      2.0
#define DXL_ID1               1
#define DXL_ID2               2
#define BASE_POSITION         1000

const int stepPin       = 9;      // ステップパルス入力ピン
const int dirPin        = 8;      // 回転方向制御ピン
const int stepDelay     = 10000;  // 1ステップの半周期 (µs)
const int maxSteps      = 1900;   // 安全上の最大ステップ数
const int rewindSteps   = 200;    // 部分巻き戻しステップ数
const int laidThreshold = 100;    // 圧力センサ閾値

// ───── グローバル変数 ─────
long  currentSteps       = 0;      // 累積ステップ数
int   lastCond           = -1;     // 最新のCond値 (-1: 未設定)
bool  emergencyRequested = false;  // 緊急停止要求フラグ
int   lastPos1           = BASE_POSITION; // ID1の最終位置
int   lastPos2           = BASE_POSITION; // ID2の最終位置

// ステッピングモータ制御（非ブロッキング）
float stepRate = 1000000.0 / (stepDelay * 2.0);
AccelStepper stepper(AccelStepper::DRIVER, stepPin, dirPin);

// Dynamixel制御
DynamixelShield dxl;

// プロトタイプ宣言
void  handleSerialCommands();
bool  runEggLayingCycle();
bool  rewindToStart();
bool  rewindStepsFromCurrentPosition(int steps);
bool  emergencyStopAndSave();
void  saveStepsToEEPROM(long steps);
long  loadStepsFromEEPROM();
void  smoothReturnToBase();

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // 乱数シード
  randomSeed(analogRead(A3));

  // ステッパー初期設定
  stepper.setMaxSpeed(stepRate * 2);
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);

  // 圧力センサ入力設定
  pinMode(A0, INPUT);
  pinMode(A1, INPUT);
  pinMode(A2, INPUT);

  // Dynamixel初期設定
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

  // 初期状態
  lastCond = -1;
  emergencyRequested = false;
  lastPos1 = BASE_POSITION;
  lastPos2 = BASE_POSITION;
  Serial.println("Dynamixel Ready");
}

void loop() {
  handleSerialCommands();
  if (emergencyRequested) return;

  if (lastCond == 1 || lastCond == 2) {
    runEggLayingCycle();
    if (emergencyRequested) return;

    // 卵産み後の滑らかな戻し
    smoothReturnToBase();
    if (emergencyRequested) return;

    // 最終の追加動作: 2秒停止 → 1000->1500(up 2000ms) -> 1500->1000(down 4000ms)
    {
      delay(2000); // 2秒停止
      const unsigned long upDuration   = 2000; // 上昇 2000ms
      const unsigned long downDuration = 4000; // 下降 4000ms
      unsigned long startFinal = millis();
      while (!emergencyRequested) {
        unsigned long t = millis() - startFinal;
        int pos;
        if (t <= upDuration) {
          // 上昇フェーズ: 0 -> π/2
          float angle = (PI / 2) * t / (float)upDuration;
          pos = BASE_POSITION + (int)(500 * sin(angle));
        } else if (t <= upDuration + downDuration) {
          // 下降フェーズ: π/2 -> π
          float dt = t - upDuration;
          float angle = PI / 2 + (PI / 2) * dt / (float)downDuration;
          pos = BASE_POSITION + (int)(500 * sin(angle));
        } else {
          break;
        }
        dxl.setGoalPosition(DXL_ID1, pos);
        delay(30);
      }
      dxl.setGoalPosition(DXL_ID1, BASE_POSITION);
    }
    if (emergencyRequested) return;

    // ステッパー巻き戻し
    rewindToStart();
    if (emergencyRequested) return;

    saveStepsToEEPROM(0);
    Serial.println("Egg-laying cycle complete");
    lastCond = -1;
  }
  delay(100);
}

void handleSerialCommands() {
  while (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() == 0) continue;

    if (cmd.equalsIgnoreCase("reset")) {
      emergencyRequested = false;
      long saved = loadStepsFromEEPROM();
      if (saved > 0) rewindStepsFromCurrentPosition(saved);
      currentSteps = 0;
      stepper.setCurrentPosition(0);
      saveStepsToEEPROM(0);
      dxl.setGoalPosition(DXL_ID1, BASE_POSITION);
      dxl.setGoalPosition(DXL_ID2, BASE_POSITION);
      lastCond = -1;
      Serial.println("-> Reset: cleared, waiting for Cond");
    } else if (cmd.startsWith("ID:") && cmd.indexOf("Cond:") > 0) {
      int idx = cmd.indexOf("Cond:") + 5;
      lastCond = cmd.substring(idx).toInt();
      emergencyRequested = false;
      Serial.print("-> Start received: Cond="); Serial.println(lastCond);
    } else if (cmd.equalsIgnoreCase("emergency_stop")) {
      emergencyRequested = true;
      emergencyStopAndSave();
    } else {
      Serial.print("-> Unknown command: "); Serial.println(cmd);
    }
  }
}

bool runEggLayingCycle() {
  bool eggLaid = false;
  stepper.setSpeed(stepRate);

  float id1Period = random(4000, 8001);
  unsigned long transitionStart1 = millis();
  bool initialTransitionDone1 = false;
  unsigned long waveStart1 = 0;

  float id2Period = random(6000, 10001);
  unsigned long transitionStart2 = millis();
  bool initialTransitionDone2 = false;
  unsigned long waveStart2 = 0;

  while (!eggLaid && !emergencyRequested) {
    handleSerialCommands();
    unsigned long now = millis();

    // ID1 サイン波
    unsigned long dt1 = now - transitionStart1;
    int pos1;
    if (!initialTransitionDone1 && dt1 <= id1Period / 4) {
      float angle1 = -2.0f * PI * dt1 / id1Period;
      pos1 = BASE_POSITION + (int)(300 * sin(angle1));
    } else {
      if (!initialTransitionDone1) {
        initialTransitionDone1 = true;
        waveStart1 = now;
      }
      float t1 = fmod((now - waveStart1), id1Period) / id1Period;
      pos1 = 700 + (int)(100 * sin(t1 * 2.0f * PI));
    }
    dxl.setGoalPosition(DXL_ID1, pos1);
    lastPos1 = pos1;

    // ID2 サイン波（Cond==2 のみ）
    if (lastCond == 2) {
      unsigned long dt2 = now - transitionStart2;
      int pos2;
      if (!initialTransitionDone2 && dt2 <= id2Period / 4) {
        float angle2 = 2.0f * PI * dt2 / id2Period;
        pos2 = BASE_POSITION + (int)(500 * sin(angle2));
      } else {
        if (!initialTransitionDone2) {
          initialTransitionDone2 = true;
          waveStart2 = now;
        }
        float t2 = fmod((now - waveStart2), id2Period) / id2Period;
        pos2 = 1500 + (int)(300 * sin(t2 * 2.0f * PI));
      }
      dxl.setGoalPosition(DXL_ID2, pos2);
      lastPos2 = pos2;
    }

    // 圧力センサ
    int p0 = analogRead(A0), p1 = analogRead(A1), p2 = analogRead(A2);
    Serial.print("Steps:"); Serial.print(currentSteps);
    Serial.print(", A0="); Serial.print(p0);
    Serial.print(", A1="); Serial.print(p1);
    Serial.print(", A2="); Serial.println(p2);
    if (p0 <= laidThreshold && p1 <= laidThreshold && p2 <= laidThreshold) {
      eggLaid = true;
    }
    // ステッパー回転
    if (stepper.runSpeed()) {
      currentSteps++;
      if (currentSteps > maxSteps) {
        rewindStepsFromCurrentPosition(rewindSteps);
        currentSteps -= rewindSteps;
      }
    }
  }
  return eggLaid;
}

// 卵産み後の滑らかな戻し (Cond=1: ID1のみ, Cond=2: 両方)
void smoothReturnToBase() {
  const unsigned long returnDuration = 2000;
  unsigned long startTime = millis();
  int start1 = lastPos1;
  int start2 = lastPos2;
  while (!emergencyRequested) {
    unsigned long t = millis() - startTime;
    if (t > returnDuration) break;
    float ratio = (float)t / returnDuration;
    float factor = sin(ratio * (PI/2));
    int p1 = start1 + (int)((BASE_POSITION - start1) * factor);
    int p2 = start2 + (int)((BASE_POSITION - start2) * factor);
    if (lastCond == 1) {
      dxl.setGoalPosition(DXL_ID1, p1);
    } else if (lastCond == 2) {
      dxl.setGoalPosition(DXL_ID1, p1);
      dxl.setGoalPosition(DXL_ID2, p2);
    }
    delay(20);
  }
  dxl.setGoalPosition(DXL_ID1, BASE_POSITION);
  if (lastCond == 2) dxl.setGoalPosition(DXL_ID2, BASE_POSITION);
}

bool rewindToStart() {
  stepper.setSpeed(-stepRate);
  while (currentSteps > 0 && !emergencyRequested) {
    handleSerialCommands();
    if (stepper.runSpeed()) {
      currentSteps--;
      Serial.print("Rewinding, steps remaining: ");
      Serial.println(currentSteps);
    }
  }
  if (!emergencyRequested) Serial.println("-> Rewound to start");
  return !emergencyRequested;
}

bool rewindStepsFromCurrentPosition(int steps) {
  stepper.setSpeed(-stepRate);
  for (int i=0; i<steps && !emergencyRequested; i++) {
    handleSerialCommands();
    while (!stepper.runSpeed() && !emergencyRequested);
  }
  return !emergencyRequested;
}

bool emergencyStopAndSave() {
  Serial.print("Emergency stop at step count: ");
  Serial.println(currentSteps);
  saveStepsToEEPROM(currentSteps);
  Serial.println("-> Position saved to EEPROM");
  delay(500);
  return true;
}

void saveStepsToEEPROM(long steps) {
  EEPROM.put(0, steps);
}

long loadStepsFromEEPROM() {
  long s;
  EEPROM.get(0, s);
  return s;
}
