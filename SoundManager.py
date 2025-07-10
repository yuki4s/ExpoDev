# SoundManager.py

import socket
import threading
import os
from playsound import playsound

# --- 設定 ---
HOST = 'localhost'
PORT = 9000
CLIENT_NAME = 'SM'
s = None

SOUND_DIR = 'Sound'  # mp3ファイルが格納されたフォルダ

# --- コマンドに応じたサウンド再生処理 ---
def handle_command(msg):
    print(f"[デバッグ] msg内容（repr）: {repr(msg)}")
    print(f"[BlackBoard→SM] {msg}")
    
    filename = f"{msg}.mp3"
    filepath = os.path.join(SOUND_DIR, filename)
    if os.path.isfile(filepath):
        print(f"[SM] 再生: {filepath}")
        try:
            playsound(filepath)
        except Exception as e:
            print(f"[SM] 再生エラー: {e}")
    else:
        print(f"[SM] 音声ファイルが見つかりません: {filepath}")

# --- BlackBoardからの受信処理 ---
def receive_from_blackboard():
    while True:
        try:
            msg = s.recv(1024).decode().strip()
            if msg:
                handle_command(msg)
        except Exception as e:
            print(f"[SM] エラー: {e}")
            break

# --- BlackBoardへ接続 ---
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
    print("[SM] 起動中。BlackBoardからのコマンドを待機中...")
    try:
        while True:
            pass  # 無限ループでプロセス維持
    except KeyboardInterrupt:
        print("[SM] 終了要求を受け取りました。")
    finally:
        if s:
            s.close()
            print("[SM] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":
    main()
