import socket
import threading
import msvcrt  # Windows専用：ESCキー検出用

clients = {}
server_running = True

def handle_client(conn, addr):
    name = None
    try:
        init_msg = conn.recv(1024).decode().strip()

        # 名前とIP:PORTのパース
        if ";" in init_msg and ":" in init_msg:
            name_part, ip_port_part = init_msg.split(";", 1)
            ip, port_str = ip_port_part.split(":", 1)
            name = name_part.strip()
            reported_ip = ip.strip()
            reported_port = int(port_str.strip())
        else:
            # 不正な形式
            conn.sendall("[エラー] 初期メッセージ形式が不正です。'名前;IP:PORT'の形式で送信してください。".encode())
            conn.close()
            return

        # 同名クライアントがすでに存在する場合は拒否
        if name in clients:
            error_msg = f"[拒否] 名前 '{name}' はすでに使用されています。他の名前で接続してください。"
            print(error_msg)
            conn.sendall(error_msg.encode())
            conn.close()
            return

        print(f"[接続] {name} ({reported_ip}:{reported_port}) が接続しました")
        clients[name] = {
            "conn": conn,
            "ip": reported_ip,
            "port": reported_port
        }

        while server_running:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                message = data.decode().strip()
                print(f"[受信] {name} → {message}")

                # メッセージ形式: 宛先名;メッセージ内容
                if ";" in message:
                    target_name, content = message.split(";", 1)
                    target = clients.get(target_name)
                    if target:
                        target["conn"].sendall(content.encode())
                        print(f"[転送] {name} → {target_name} : {content}")
                    else:
                        conn.sendall(f"[エラー] 宛先 '{target_name}' が見つかりません".encode())
                else:
                    conn.sendall("[エラー] メッセージは '宛先名;内容' の形式で送信してください".encode())

            except Exception as e:
                print(f"[エラー] 受信中に例外発生：{e}")
                break

    finally:
        if name:
            client_info = clients.get(name)
            if client_info:
                print(f"[切断] {client_info['ip']}:{client_info['port']} ({name}) の接続を終了")
                del clients[name]
        conn.close()

def watch_for_esc():
    global server_running
    print("[操作] ESCキーでサーバを終了できます")
    while server_running:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\x1b':  # ESCキー
                print("\n[操作] ESCキーが押されました。サーバを終了します。")
                server_running = False
                break

def start_server(host='localhost', port=9000):
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    print(f"[起動] BlackBoardサーバが {host}:{port} で待機中...")

    esc_thread = threading.Thread(target=watch_for_esc, daemon=True)
    esc_thread.start()

    try:
        while server_running:
            server.settimeout(1.0)
            try:
                conn, addr = server.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                thread.start()
            except socket.timeout:
                continue
    finally:
        print("[終了] サーバ停止中...")
        for client in clients.values():
            client["conn"].close()
        server.close()

if __name__ == "__main__":
    start_server()
