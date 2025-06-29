#include <DynamixelShield.h>                  // Dynamixel用のArduinoライブラリをインクルード

#define BAUDRATE         57600                // Dynamixelとの通信速度
#define PROTOCOL_VERSION 2.0                  // 使用するDynamixelのプロトコルバージョン

DynamixelShield dxl;                          // Dynamixel通信用オブジェクト作成

const uint8_t DXL_ID1 = 1;                    // モーター1のID
const uint8_t DXL_ID2 = 2;                    // モーター2のID
const uint16_t BASE_POSITION = 1000;          // モーター初期位置
const uint16_t OFFSET = 100;                  // 移動時のオフセット量
const uint16_t DEPTH_TRIGGER = 500;           // Depthトリガー閾値

String inputBuffer = "";                      // シリアル入力用バッファ
bool isMoving = false;                        // モーターが動作中かを示すフラグ

void setup() {
  Serial.begin(9600);                         // PCとのシリアル通信を9600bpsで開始
  while (!Serial);                            // シリアルポートが開くまで待機

  dxl.begin(BAUDRATE);                        // Dynamixelとの通信開始
  dxl.setPortProtocolVersion(PROTOCOL_VERSION); // Dynamixelのプロトコルバージョンを設定

  dxl.torqueOff(DXL_ID1);                     // モーターID1のトルクをオフ
  dxl.torqueOff(DXL_ID2);                     // モーターID2のトルクをオフ
  dxl.setOperatingMode(DXL_ID1, OP_POSITION); // モーターID1を位置制御モードに設定
  dxl.setOperatingMode(DXL_ID2, OP_POSITION); // モーターID2を位置制御モードに設定
  dxl.torqueOn(DXL_ID1);                      // モーターID1のトルクをオン
  dxl.torqueOn(DXL_ID2);                      // モーターID2のトルクをオン

  dxl.setGoalPosition(DXL_ID1, BASE_POSITION); // モーターID1を初期位置に移動
  dxl.setGoalPosition(DXL_ID2, BASE_POSITION); // モーターID2を初期位置に移動

  Serial.println("Dynamixel Ready");          // 初期化完了をシリアル出力
}

void loop() {
  while (Serial.available()) {                // シリアルにデータがあれば
    char c = Serial.read();                   // 1文字読み込み

    if (c == '\n') {                          // 改行文字で1コマンドの終端と判定
      inputBuffer.trim();                     // 受信文字列の前後空白を削除

      if (inputBuffer.length() > 0) {         // 入力が空でなければ
        Serial.print("受信: ");               // 入力内容を表示
        Serial.println(inputBuffer);

        if (inputBuffer == "reset") {         // "reset"コマンド受信時
          dxl.setGoalPosition(DXL_ID1, BASE_POSITION); // ID1を初期位置に移動
          dxl.setGoalPosition(DXL_ID2, BASE_POSITION); // ID2を初期位置に移動
          isMoving = false;                   // 動作フラグをリセット
          Serial.println("→ Reset: ID1 & ID2 を 1000 に設定");
        }
        else if (inputBuffer.startsWith("Depth:")) {   // "Depth:xxx"形式受信時
          if (!isMoving) {                  // 動作中でない場合のみ
            float depth = inputBuffer.substring(6).toFloat(); // Depth値を取得
            Serial.print("→ Depth受信: ");
            Serial.println(depth);

            if (depth < DEPTH_TRIGGER) {    // 閾値より小さい場合
              isMoving = true;              // 動作フラグをセット
              Serial.println("→ 動作開始（ID1 +200 → -200 → 初期位置）");

              dxl.setGoalPosition(DXL_ID1, BASE_POSITION + 200); // ID1を+200移動
              delay(3000);                 // 3秒待機
              dxl.setGoalPosition(DXL_ID1, BASE_POSITION - 200); // ID1を-200移動
              delay(3000);                 // 3秒待機
              dxl.setGoalPosition(DXL_ID1, BASE_POSITION);       // ID1を初期位置へ戻す
              delay(3000);                 // 3秒待機

              Serial.println("→ 動作完了、初期位置へ戻る");

              while (Serial.available()) Serial.read(); // 残りの受信データをクリア
              isMoving = false;           // 動作フラグをリセット
            } else {
              Serial.println("→ Depthは閾値より大きいため無視");
            }
          } else {
            Serial.println("→ 動作中のため無視");
          }
        }
        else if (inputBuffer.startsWith("ID:") && inputBuffer.indexOf("Cond:1") != -1) {
          dxl.setGoalPosition(DXL_ID1, BASE_POSITION + OFFSET); // 条件1: ID1を+100に移動
          Serial.println("→ ID1 を +100 に移動");
        }
        else if (inputBuffer.startsWith("ID:") && inputBuffer.indexOf("Cond:2") != -1) {
          dxl.setGoalPosition(DXL_ID2, BASE_POSITION + OFFSET); // 条件2: ID2を+100に移動
          Serial.println("→ ID2 を +100 に移動");
        }
        else {
          Serial.println("→ 未知のコマンド");       // 不明なコマンド時
        }
      }

      inputBuffer = "";                     // バッファをリセット
    } else {
      inputBuffer += c;                     // 受信文字をバッファに追加
    }
  }
}
