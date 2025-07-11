import socket                                  # ソケット通信のための標準ライブラリ
import threading                               # スレッド処理のための標準ライブラリ
import serial.tools.list_ports                 # シリアルポートの列挙用ツール
import serial                                  # PySerialライブラリ（Arduino通信用）
import time                                    # 時間制御のための標準ライブラ
import os

# --- BlackBoard通信設定 ---
HOST = 'localhost'                             # BlackBoardサーバのホスト名
PORT = 9000                                    # BlackBoardサーバのポート番号
CLIENT_NAME = 'BM'                             # このクライアントの名前（Board Manager）
s = None                                       # BlackBoardとのソケット接続オブジェクト
arduino = None                                 # Arduinoとのシリアル接続オブジェクト

# --- Arduino接続処理（VID:PIDによる確実な識別） ---
def connect_to_arduino():
    global arduino
    target_vid_pid_list = ["2341:0069"]        # 対象とするArduinoデバイスのVID:PID（Uno R4 Minima）
    ports = list(serial.tools.list_ports.comports())  # 使用可能な全シリアルポートを取得
    for port in ports:
        print(f"[DEBUG] 発見: {port.device} - {port.hwid}")  # 発見されたポートのデバッグ表示
        for vid_pid in target_vid_pid_list:
            if f"VID:PID={vid_pid}" in port.hwid:             # 一致するVID:PIDがあるか確認
                try:
                    arduino = serial.Serial(port.device, 9600, timeout=0.5)  # シリアル通信開始（9600bps）
                    print(f"[Arduino] 接続成功: {port.device} ({port.description})")  # 成功メッセージ表示
                    start_arduino_receive_thread()            # Arduino受信スレッドを開始
                    return
                except Exception as e:
                    print(f"[Arduino] 接続失敗: {port.device}, {e}")  # 接続失敗のエラーメッセージ
    print("[Arduino] 対象のVID:PIDデバイスが見つかりませんでした")  # 対象デバイス未検出時の表示

# --- Arduinoからのメッセージ受信処理 ---
def start_arduino_receive_thread():
    def read_from_arduino():                                 # Arduinoからの非同期受信用関数
        global arduino
        while True:
            if arduino and arduino.is_open:                  # Arduinoが接続されていて開いていれば
                try:
                    line = arduino.readline().decode(errors='ignore').strip()  # 1行読み取り・デコード
                    if line:
                        print(f"[Arduino→BM] {line}")        # 受信内容を表示
                except Exception as e:
                    print(f"[Arduino受信エラー] {e}")        # 読み取りエラーの表示
                    time.sleep(1)                             # 少し待機して再試行
            else:
                print("[Arduino] ポートが閉じられました")     # ポートが閉じられた場合の警告
                break
    t = threading.Thread(target=read_from_arduino, daemon=True)  # デーモンスレッドで受信処理を実行
    t.start()                                                # スレッド開始

# --- BlackBoardからのメッセージ受信処理 ---
def receive_from_blackboard():
    global s, arduino
    while True:
        try:
            msg = s.recv(1024).decode().strip()
            if msg:
                print(f"[BlackBoard→{CLIENT_NAME}] {msg}")
                content = msg
                print(f"[BM] コマンド抽出: {content}")

                if content == "CMD;shutdown":
                    print("[BM] shutdown コマンドを受信しました。プログラムを終了します。")
                    if arduino:
                        arduino.close()
                        print("[BM] Arduinoとの接続を閉じました。")
                    if s:
                        s.close()
                        print("[BM] BlackBoardとの接続を閉じました。")
                    os._exit(0)

                if arduino and arduino.is_open:
                    try:
                        arduino.write((content + '\n').encode())
                        print(f"[Arduinoへ送信] {content}")
                    except Exception as e:
                        print(f"[Arduino送信エラー] {e}")
                else:
                    print("[Arduino] 未接続のため送信できません")
        except Exception as e:
            print(f"[BM] 受信処理エラー: {e}")
            break

# --- BlackBoardへの接続処理 ---
def connect_to_blackboard():
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    # TCPソケットを作成
    s.connect((HOST, PORT))                                  # 指定ホスト・ポートに接続

    local_ip, local_port = s.getsockname()                   # 自身のIPアドレスとポートを取得
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"     # 初期接続メッセージの作成
    s.sendall(init_msg.encode())                             # エンコードして送信

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")  # 接続成功メッセージ

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)  # BlackBoard受信スレッドを作成
    recv_thread.start()                                      # スレッドを開始

# --- メイン処理 ---
def main():
    connect_to_blackboard()                                  # BlackBoardへの接続を開始
    connect_to_arduino()                                     # Arduinoへの接続を試みる

    print("[BM] 起動中。BlackBoardからのメッセージを待機しています...")  # 待機メッセージ
    try:
        while True:                                          # メインスレッドを生かすためのループ
            time.sleep(1)                                    # 1秒ごとにスリープ
    except KeyboardInterrupt:                                # Ctrl+Cで停止された場合
        print("[BM] 終了要求を受け取りました。")             # 終了メッセージ表示
    finally:
        if arduino:
            arduino.close()                                  # Arduino接続を閉じる
            print("[BM] Arduinoとの接続を閉じました。")
        if s:
            s.close()                                        # ソケットを閉じる
            print("[BM] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":                                   # このスクリプトが直接実行された場合
    main()                                                   # メイン関数を実行
