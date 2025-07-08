import socket
import threading
import serial.tools.list_ports
import serial
import time

# --- BlackBoard通信設定 ---
HOST = 'localhost'
PORT = 9000
CLIENT_NAME = 'BM'
s = None
arduino = None

# --- Arduino接続処理（VID:PIDによる確実な識別） ---
def connect_to_arduino():
    global arduino
    target_vid_pid_list = ["2341:0069"]  # Uno R4 Minima専用
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        print(f"[DEBUG] 発見: {port.device} - {port.hwid}")
        for vid_pid in target_vid_pid_list:
            if f"VID:PID={vid_pid}" in port.hwid:
                try:
                    arduino = serial.Serial(port.device, 9600, timeout=0.5)
                    print(f"[Arduino] 接続成功: {port.device} ({port.description})")
                    start_arduino_receive_thread()
                    return
                except Exception as e:
                    print(f"[Arduino] 接続失敗: {port.device}, {e}")
    print("[Arduino] 対象のVID:PIDデバイスが見つかりませんでした")

# --- Arduinoからのメッセージ受信処理 ---
def start_arduino_receive_thread():
    def read_from_arduino():
        global arduino
        while True:
            if arduino and arduino.is_open:
                try:
                    line = arduino.readline().decode(errors='ignore').strip()
                    if line:
                        print(f"[Arduino→BM] {line}")
                except Exception as e:
                    print(f"[Arduino受信エラー] {e}")
                    time.sleep(1)
            else:
                print("[Arduino] ポートが閉じられました")
                break
    t = threading.Thread(target=read_from_arduino, daemon=True)
    t.start()

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
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))

    local_ip, local_port = s.getsockname()
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"
    s.sendall(init_msg.encode())

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)
    recv_thread.start()

# --- メイン処理 ---
def main():
    connect_to_blackboard()
    connect_to_arduino()

    print("[BM] 起動中。BlackBoardからのメッセージを待機しています...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[BM] 終了要求を受け取りました。")
    finally:
        if arduino:
            arduino.close()
            print("[BM] Arduinoとの接続を閉じました。")
        if s:
            s.close()
            print("[BM] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":
    main()
