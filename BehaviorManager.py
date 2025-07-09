import socket  # BlackBoardとの通信に使用するソケット通信モジュール
import threading  # 並列処理を行うためのスレッドモジュール
import serial.tools.list_ports  # 接続されているシリアルポート一覧を取得するためのモジュール
import serial  # Arduinoとのシリアル通信に使用するモジュール
import time  # スリープや時間処理に使用

# --- BlackBoard通信設定 ---
HOST = 'localhost'  # BlackBoardのホスト名（ローカル接続）
PORT = 9000  # BlackBoardのポート番号
CLIENT_NAME = 'BM'  # このクライアント（BehaviorManager）の識別名
s = None  # ソケット通信のための変数（後で初期化）
arduino = None  # Arduinoとのシリアル接続オブジェクト（後で初期化）

# --- Arduino接続処理（VID:PIDによる確実な識別） ---
def connect_to_arduino():
    global arduino
    target_vid_pid_list = ["2341:0069"]  # 対象のArduino（Uno R4 Minima）のVID:PIDリスト
    ports = list(serial.tools.list_ports.comports())  # 接続されているシリアルポートの一覧を取得
    for port in ports:
        print(f"[DEBUG] 発見: {port.device} - {port.hwid}")  # デバッグ用に接続デバイス情報を表示
        for vid_pid in target_vid_pid_list:
            if f"VID:PID={vid_pid}" in port.hwid:  # 指定されたVID:PIDと一致するデバイスを探す
                try:
                    arduino = serial.Serial(port.device, 9600, timeout=0.5)  # Arduinoにシリアル接続
                    print(f"[Arduino] 接続成功: {port.device} ({port.description})")
                    start_arduino_receive_thread()  # Arduinoからの受信スレッドを開始
                    return
                except Exception as e:
                    print(f"[Arduino] 接続失敗: {port.device}, {e}")  # 接続失敗時のエラー表示
    print("[Arduino] 対象のVID:PIDデバイスが見つかりませんでした")  # 該当するデバイスがない場合

# --- Arduinoからのメッセージ受信処理 ---
def start_arduino_receive_thread():
    def read_from_arduino():  # Arduinoからの受信を行うスレッド関数
        global arduino
        while True:
            if arduino and arduino.is_open:  # Arduinoが接続されている場合
                try:
                    line = arduino.readline().decode(errors='ignore').strip()  # 1行読み取り＆整形
                    if line:
                        print(f"[Arduino→BM] {line}")  # Arduinoからのメッセージを表示
                except Exception as e:
                    print(f"[Arduino受信エラー] {e}")  # 読み取り時のエラー
                    time.sleep(1)  # 1秒待機してリトライ
            else:
                print("[Arduino] ポートが閉じられました")  # Arduinoが切断された場合
                break
    t = threading.Thread(target=read_from_arduino, daemon=True)  # デーモンスレッドで実行
    t.start()  # スレッド開始

# --- BlackBoardからのメッセージ受信処理 ---
def receive_from_blackboard():
    global s, arduino
    while True:
        try:
            msg = s.recv(1024).decode().strip()  # BlackBoardからのメッセージ受信（最大1024バイト）
            if msg:
                print(f"[BlackBoard→{CLIENT_NAME}] {msg}")  # BlackBoardから受信した内容を表示
                content = msg  # 内容をそのまま保持（将来的なパースにも対応可能）
                print(f"[BM] コマンド抽出: {content}")
                if arduino and arduino.is_open:  # Arduinoが接続されていれば
                    try:
                        arduino.write((content + '\n').encode())  # Arduinoへコマンドを送信
                        print(f"[Arduinoへ送信] {content}")
                    except Exception as e:
                        print(f"[Arduino送信エラー] {e}")  # 送信失敗時の表示
                else:
                    print("[Arduino] 未接続のため送信できません")  # Arduinoが未接続の場合
        except Exception as e:
            print(f"[BM] 受信処理エラー: {e}")  # BlackBoardとの通信エラー
            break

# --- BlackBoardへの接続処理 ---
def connect_to_blackboard():
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPソケットを作成
    s.connect((HOST, PORT))  # 指定ホスト・ポートに接続

    local_ip, local_port = s.getsockname()  # 自身のIPとポート番号を取得
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"  # 初期メッセージ（識別情報）を作成
    s.sendall(init_msg.encode())  # BlackBoardに送信

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)  # 受信用スレッドを作成
    recv_thread.start()  # スレッド開始

# --- メイン処理 ---
def main():
    connect_to_blackboard()  # BlackBoardへの接続を確立
    connect_to_arduino()  # Arduinoとの接続を試行

    print("[BM] 起動中。BlackBoardからのメッセージを待機しています...")
    try:
        while True:
            time.sleep(1)  # 1秒ごとのループ（メインスレッドの維持）
    except KeyboardInterrupt:
        print("[BM] 終了要求を受け取りました。")  # Ctrl+Cなどによる終了
    finally:
        if arduino:
            arduino.close()  # Arduinoとの接続を終了
            print("[BM] Arduinoとの接続を閉じました。")
        if s:
            s.close()  # BlackBoardとの接続を終了
            print("[BM] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":
    main()  # スクリプトが直接実行された場合、main() を実行
