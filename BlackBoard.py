# BlackBoard.py

import socket                                    # ソケット通信を行うための標準ライブラリ
import threading                                 # スレッド処理用標準ライブラリ
import msvcrt  # Windows専用：ESCキー検出用   # Windowsでキー入力検出を行うための標準ライブラリ

clients = {}                                    # 接続中クライアントの情報を格納する辞書
server_running = True                           # サーバ実行中フラグ

def handle_client(conn, addr):                  # クライアントごとの接続を処理する関数
    name = None                                 # クライアント名を格納する変数
    try:
        init_msg = conn.recv(1024).decode().strip()  # 初回メッセージを受信しデコード

        # 名前とIP:PORTのパース
        if ";" in init_msg and ":" in init_msg:     # メッセージに';'と':'が含まれるか確認
            name_part, ip_port_part = init_msg.split(";", 1)     # 名前とIP:PORT部分に分割
            ip, port_str = ip_port_part.split(":", 1)            # IPとPORTに分割
            name = name_part.strip()                            # クライアント名
            reported_ip = ip.strip()                            # クライアントIP
            reported_port = int(port_str.strip())               # クライアントPORT（int変換）
        else:
            # 不正な形式
            conn.sendall("[エラー] 初期メッセージ形式が不正です。'名前;IP:PORT'の形式で送信してください。".encode())  # エラーメッセージ送信
            conn.close()                                        # 接続終了
            return

        # 同名クライアントがすでに存在する場合は拒否
        if name in clients:                                    # 同じ名前がすでにclientsに存在するか確認
            error_msg = f"[拒否] 名前 '{name}' はすでに使用されています。他の名前で接続してください。"
            print(error_msg)                                   # エラー内容を表示
            conn.sendall(error_msg.encode())                   # エラーメッセージ送信
            conn.close()                                       # 接続終了
            return

        print(f"[接続] {name} ({reported_ip}:{reported_port}) が接続しました")  # 接続成功を表示
        clients[name] = {                                      # クライアント情報を辞書に登録
            "conn": conn,
            "ip": reported_ip,
            "port": reported_port
        }

        while server_running:                                  # サーバが稼働中の間ループ
            try:
                data = conn.recv(1024)                         # クライアントからデータ受信
                if not data:                                   # データが空なら切断と判断
                    break

                message = data.decode().strip()                # メッセージをデコード
                print(f"[受信] {name} → {message}")            # 受信内容を表示

                # メッセージ形式: 宛先名;メッセージ内容
                if ";" in message:                            # メッセージが';'を含むか確認
                    target_name, content = message.split(";", 1)  # 宛先名と内容に分割
                    target = clients.get(target_name)             # 宛先クライアント情報を取得
                    if target:                                   # 宛先が存在すれば
                        target["conn"].sendall(content.encode())  # 宛先にメッセージを送信
                        print(f"[転送] {name} → {target_name} : {content}")  # 転送内容を表示
                    else:
                        conn.sendall(f"[エラー] 宛先 '{target_name}' が見つかりません".encode())  # 宛先不明のエラー
                else:
                    conn.sendall("[エラー] メッセージは '宛先名;内容' の形式で送信してください".encode())  # メッセージ形式不正時

            except Exception as e:
                print(f"[エラー] 受信中に例外発生：{e}")        # 受信中に例外が発生した場合表示
                break

    finally:
        if name:                                              # クライアント名が取得できている場合
            client_info = clients.get(name)                   # 登録情報を取得
            if client_info:
                print(f"[切断] {client_info['ip']}:{client_info['port']} ({name}) の接続を終了")  # 切断メッセージ表示
                del clients[name]                             # クライアント情報を辞書から削除
        conn.close()                                          # 接続をクローズ

def watch_for_esc():                                          # ESCキー押下でサーバを終了する監視スレッド
    global server_running
    print("[操作] ESCキーでサーバを終了できます")
    while server_running:
        if msvcrt.kbhit():                                    # キーボード入力を検出
            key = msvcrt.getch()                              # 押されたキーを取得
            if key == b'\x1b':  # ESCキー                    # ESCキーが押された場合
                print("\n[操作] ESCキーが押されました。サーバを終了します。")
                server_running = False                       # サーバ稼働フラグをFalseに
                break

def start_server(host='localhost', port=9000):                # サーバ起動関数
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPソケットを作成
    server.bind((host, port))                                   # 指定ホスト・ポートにバインド
    server.listen()                                             # 接続待機状態にする
    print(f"[起動] BlackBoardサーバが {host}:{port} で待機中...")

    esc_thread = threading.Thread(target=watch_for_esc, daemon=True)  # ESC監視スレッド作成
    esc_thread.start()                                          # ESC監視スレッド開始

    try:
        while server_running:                                  # サーバ稼働中はループ
            server.settimeout(1.0)                             # 1秒ごとにacceptをタイムアウトさせてESC監視を挟む
            try:
                conn, addr = server.accept()                   # クライアント接続を受け付ける
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)  # クライアントごとにスレッド作成
                thread.start()                                 # クライアントスレッド開始
            except socket.timeout:                             # acceptがタイムアウトした場合
                continue                                       # ループを継続しESC監視へ戻る
    finally:
        print("[終了] サーバ停止中...")
        for client in clients.values():                        # 接続中クライアント全ての接続を閉じる
            client["conn"].close()
        server.close()                                         # サーバソケットを閉じる

if __name__ == "__main__":                                    # スクリプトが直接実行されたときのみ
    start_server()                                             # サーバ起動
