# BehaviorManager.py

import socket                                      # ソケット通信用標準ライブラリ
import threading                                   # スレッド処理用標準ライブラリ
import serial.tools.list_ports                    # シリアルポート探索用ライブラリ
import serial                                     # シリアル通信ライブラリ
import time                                       # 時間制御用標準ライブラリ

# --- BlackBoard通信設定 ---
HOST = 'localhost'                                # BlackBoardサーバのホスト名
PORT = 9000                                       # BlackBoardサーバのポート番号
CLIENT_NAME = 'BM'                                # このクライアントの名前（Behavior Manager）
s = None                                          # ソケット接続オブジェクト
arduino = None                                    # Arduino接続オブジェクト

# --- Arduino接続処理（VID:PIDによる確実な識別） ---
def connect_to_arduino():                         # Arduinoへ接続する関数
    global arduino
    target_vid_pid_list = ["2341:0069"]           # 接続対象とするArduinoのVID:PID（Uno R4 Minima専用）
    ports = list(serial.tools.list_ports.comports())  # 利用可能なシリアルポート一覧取得
    for port in ports:
        print(f"[DEBUG] 発見: {port.device} - {port.hwid}")  # 検出したポート情報を表示
        for vid_pid in target_vid_pid_list:
            if f"VID:PID={vid_pid}" in port.hwid:            # VID:PID一致を確認
                try:
                    arduino = serial.Serial(port.device, 9600, timeout=0.5)  # シリアル通信開始
                    print(f"[Arduino] 接続成功: {port.device} ({port.description})")
                    start_arduino_receive_thread()                          # Arduino受信用スレッド開始
                    return
                except Exception as e:
                    print(f"[Arduino] 接続失敗: {port.device}, {e}")
    print("[Arduino] 対象のVID:PIDデバイスが見つかりませんでした")  # 指定VID:PIDが見つからない場合

# --- Arduinoからのメッセージ受信処理 ---
def start_arduino_receive_thread():                # Arduinoからのメッセージを受信するスレッド開始
    def read_from_arduino():                       # スレッド内で実行される関数
        global arduino
        while True:
            if arduino and arduino.is_open:        # Arduinoが接続されているか確認
                try:
                    line = arduino.readline().decode(errors='ignore').strip()  # Arduinoから1行読み取り
                    if line:
                        print(f"[Arduino→BM] {line}")        # 受信内容を表示
                except Exception as e:
                    print(f"[Arduino受信エラー] {e}")        # 読み取り時の例外を表示
                    time.sleep(1)
            else:
                print("[Arduino] ポートが閉じられました")    # Arduino接続が閉じた場合
                break
    t = threading.Thread(target=read_from_arduino, daemon=True)  # Arduino受信用スレッド生成
    t.start()                                      # スレッド開始

# --- BlackBoardからのメッセージ受信処理 ---
def receive_from_blackboard():                    # BlackBoardからのメッセージ受信処理
    global s, arduino
    while True:
        try:
            msg = s.recv(1024).decode().strip()   # BlackBoardからメッセージを受信しデコード
            if msg:
                print(f"[BlackBoard→{CLIENT_NAME}] {msg}")  # 受信内容を表示
                content = msg                     # メッセージ内容を抽出
                print(f"[BM] コマンド抽出: {content}")
                if arduino and arduino.is_open:   # Arduino接続確認
                    try:
                        arduino.write((content + '\n').encode())  # Arduinoへメッセージ送信
                        print(f"[Arduinoへ送信] {content}")
                    except Exception as e:
                        print(f"[Arduino送信エラー] {e}")
                else:
                    print("[Arduino] 未接続のため送信できません")  # Arduino未接続時の警告
        except Exception as e:
            print(f"[BM] 受信処理エラー: {e}")   # BlackBoard受信処理中の例外を表示
            break

# --- BlackBoardへの接続処理 ---
def connect_to_blackboard():                      # BlackBoardへ接続する関数
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # ソケット生成
    s.connect((HOST, PORT))                                # BlackBoardに接続

    local_ip, local_port = s.getsockname()                 # 自分側のIP・ポート取得
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"    # 初期メッセージ作成
    s.sendall(init_msg.encode())                           # 初期メッセージを送信

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)  # BlackBoard受信用スレッド作成
    recv_thread.start()                                  # 受信用スレッド開始

# --- メイン処理 ---
def main():                                             # メインエントリポイント
    connect_to_blackboard()                             # BlackBoard接続処理
    connect_to_arduino()                               # Arduino接続処理

    print("[BM] 起動中。BlackBoardからのメッセージを待機しています...")
    try:
        while True:
            time.sleep(1)                              # 常に動作を継続（スリープしながら待機）
    except KeyboardInterrupt:
        print("[BM] 終了要求を受け取りました。")        # Ctrl+Cなどで終了要求を受けた場合
    finally:
        if arduino:
            arduino.close()                           # Arduino接続を閉じる
            print("[BM] Arduinoとの接続を閉じました。")
        if s:
            s.close()                                 # BlackBoard接続を閉じる
            print("[BM] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":                            # スクリプトが直接実行されたときのみ
    main()                                            # メイン処理を開始
