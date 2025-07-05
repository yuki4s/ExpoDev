# BehaviorManager.py

import socket                                      # ソケット通信ライブラリ
import threading                                   # スレッド処理ライブラリ
import serial.tools.list_ports                    # シリアルポート探索用ライブラリ
import serial                                     # シリアル通信ライブラリ
import time                                       # 時間操作用標準ライブラリ

# --- BlackBoard通信設定 ---
HOST = 'localhost'                                # BlackBoardサーバのホスト名
PORT = 9000                                       # BlackBoardサーバのポート番号
CLIENT_NAME = 'BM'                                # このクライアントの名前（Behavior Manager）
s = None                                          # ソケット接続オブジェクト
arduino = None                                    # Arduino接続オブジェクト
running = True                                    # プロセス稼働フラグ

# --- Arduino接続処理 ---
def connect_to_arduino():                         # Arduinoへ接続する関数
    global arduino
    target_vid_pid_list = ["2341:0069"]           # 接続対象ArduinoのVID:PID（Uno R4 Minima用）
    ports = list(serial.tools.list_ports.comports())  # 利用可能なシリアルポート一覧取得
    for port in ports:
        print(f"[DEBUG] 発見: {port.device} - {port.hwid}")  # 検出したポート情報を表示
        for vid_pid in target_vid_pid_list:
            if f"VID:PID={vid_pid}" in port.hwid:  # VID:PID一致を確認
                try:
                    arduino = serial.Serial(port.device, 9600, timeout=0.5)  # Arduinoへシリアル接続
                    print(f"[Arduino] 接続成功: {port.device} ({port.description})")
                    start_arduino_receive_thread()  # Arduino受信用スレッド開始
                    return
                except Exception as e:
                    print(f"[Arduino] 接続失敗: {port.device}, {e}")
    print("[Arduino] 対象のVID:PIDデバイスが見つかりませんでした")  # 指定デバイスが見つからない場合

# --- Arduinoからのメッセージ受信処理 ---
def start_arduino_receive_thread():
    def read_from_arduino():
        global arduino
        while True:
            if arduino and arduino.is_open:         # Arduino接続中確認
                try:
                    line = arduino.readline().decode(errors='ignore').strip()  # メッセージ受信
                    if line:
                        print(f"[Arduino→BM] {line}")  # Arduinoからのメッセージを表示
                except Exception as e:
                    print(f"[Arduino受信エラー] {e}")  # 読み取りエラー表示
                    time.sleep(1)
            else:
                print("[Arduino] ポートが閉じられました")  # Arduino切断検知
                break
    t = threading.Thread(target=read_from_arduino, daemon=True)  # Arduino受信用スレッド作成
    t.start()                                        # スレッド開始

# --- BlackBoardからのメッセージ受信処理 ---
def receive_from_blackboard():
    global s, arduino, running
    while True:
        try:
            msg = s.recv(1024).decode().strip()    # BlackBoardからメッセージを受信しデコード
            if msg:
                print(f"[BlackBoard→{CLIENT_NAME}] {msg}")  # 受信内容を表示

                if msg == "EXIT":                 # EXITを受信した場合
                    print("[BM] EXITコマンドを受信しました。ACKを返して終了します。")
                    try:
                        s.sendall(b"ACK;EXIT_RECEIVED")  # BlackBoardにACK送信
                        print("[ACK送信] EXIT受領確認を送信しました。")
                    except Exception as e:
                        print(f"[ACK送信失敗] {e}")
                    running = False               # メインループを終了する
                    break                         # 受信用スレッド終了
                else:
                    content = msg                # その他のコマンド内容を取得
                    print(f"[BM] コマンド抽出: {content}")
                    if arduino and arduino.is_open:  # Arduino接続確認
                        try:
                            arduino.write((content + '\n').encode())  # Arduinoにコマンド送信
                            print(f"[Arduinoへ送信] {content}")
                        except Exception as e:
                            print(f"[Arduino送信エラー] {e}")
                    else:
                        print("[Arduino] 未接続のため送信できません")  # Arduino未接続時
        except Exception as e:
            print(f"[BM] 受信処理エラー: {e}")    # BlackBoard受信処理中の例外を表示
            break

# --- BlackBoardへの接続処理 ---
def connect_to_blackboard():                      # BlackBoardへ接続する関数
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPソケット生成
    try:
        s.connect((HOST, PORT))                            # BlackBoardに接続を試みる
    except Exception as e:                                 # 接続に失敗した場合
        print(f"[接続エラー] BlackBoardへの接続に失敗しました: {e}")  # エラーメッセージを表示
        print("[接続エラー] 5秒後に終了します。")                       # 終了前に待機することを案内
        time.sleep(5)                                      # 手動確認できるよう5秒間待機
        exit(1)                                            # エラーコード1で終了

    local_ip, local_port = s.getsockname()                # 自分側のIP・ポート取得
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"   # 初期メッセージ作成
    s.sendall(init_msg.encode())                          # 初期メッセージをBlackBoardに送信

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")  # 接続完了メッセージを表示

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)  # BlackBoard受信用スレッド生成
    recv_thread.start()                                  # 受信用スレッド開始

# --- メイン処理 ---
def main():
    connect_to_blackboard()                              # BlackBoard接続
    connect_to_arduino()                                # Arduino接続
    print("[BM] 起動中。BlackBoardからのメッセージを待機しています...")
    try:
        while running:                                  # メインループ
            time.sleep(1)                               # スリープでCPU負荷軽減
    except KeyboardInterrupt:
        print("[BM] 終了要求を受け取りました。")         # Ctrl+Cなどで終了要求検知
    finally:
        if arduino:
            arduino.close()                            # Arduino接続を閉じる
            print("[BM] Arduinoとの接続を閉じました。")
        if s:
            s.close()                                  # BlackBoard接続を閉じる
            print("[BM] BlackBoardとの接続を閉じました。")

if __name__ == "__main__": main()                      # スクリプトが直接実行されたときのみメイン処理開始
