import socket                                 # ソケット通信のためのライブラリをインポート
import threading                              # スレッド処理のためのライブラリをインポート
import msvcrt                                 # Windows専用：キーボード入力（ESCキー検出）を扱うライブラリ

clients = {}                                  # クライアント情報を格納する辞書（名前をキーにして接続情報を管理）
server_running = True                         # サーバが稼働中かどうかのフラグ

def handle_client(conn, addr):                # クライアントとの接続を処理する関数
    name = None                               # クライアント名を初期化
    try:
        init_msg = conn.recv(1024).decode().strip()  # 初回メッセージを受信してデコード・整形

        # 名前とIP:PORTのパース
        if ";" in init_msg and ":" in init_msg:       # 初期メッセージが適切な形式か確認
            name_part, ip_port_part = init_msg.split(";", 1)  # 名前とIP:PORTに分割
            ip, port_str = ip_port_part.split(":", 1)         # IPとポートに分割
            name = name_part.strip()                          # 名前を取得
            reported_ip = ip.strip()                          # IPを取得
            reported_port = int(port_str.strip())             # ポートを整数として取得
        else:
            # 不正な形式
            conn.sendall("[エラー] 初期メッセージ形式が不正です。'名前;IP:PORT'の形式で送信してください。".encode())  # エラーメッセージ送信
            conn.close()                                       # 接続を閉じる
            return

        # 同名クライアントがすでに存在する場合は拒否
        if name in clients:                                     # 同名が存在するか確認
            error_msg = f"[拒否] 名前 '{name}' はすでに使用されています。他の名前で接続してください。"  # エラーメッセージ作成
            print(error_msg)                                    # エラーを表示
            conn.sendall(error_msg.encode())                    # クライアントに送信
            conn.close()                                        # 接続を閉じる
            return

        print(f"[接続] {name} ({reported_ip}:{reported_port}) が接続しました")  # 接続通知を表示
        clients[name] = {                                       # クライアント情報を保存
            "conn": conn,
            "ip": reported_ip,
            "port": reported_port
        }

        while server_running:                                   # サーバが稼働中の間
            try:
                data = conn.recv(1024)                          # メッセージを受信
                if not data:                                    # 接続が切れた場合
                    break

                message = data.decode().strip()                 # メッセージをデコード・整形
                print(f"[受信] {name} → {message}")            # 受信ログを表示

                # メッセージ形式: 宛先名;メッセージ内容
                if ";" in message:                              # セミコロンが含まれていれば
                    target_name, content = message.split(";", 1)  # 宛先とメッセージに分割
                    target = clients.get(target_name)              # 宛先クライアントを取得
                    if target:                                     # 宛先が存在すれば
                        target["conn"].sendall(content.encode())   # メッセージを転送
                        print(f"[転送] {name} → {target_name} : {content}")  # 転送ログ
                    else:
                        conn.sendall(f"[エラー] 宛先 '{target_name}' が見つかりません".encode())  # エラー送信
                else:
                    conn.sendall("[エラー] メッセージは '宛先名;内容' の形式で送信してください".encode())  # フォーマットエラー通知

            except Exception as e:                                # 受信中の例外処理
                print(f"[エラー] 受信中に例外発生：{e}")           # エラーログを表示
                break

    finally:                                                      # 接続終了時の処理
        if name:
            client_info = clients.get(name)                       # クライアント情報を取得
            if client_info:
                print(f"[切断] {client_info['ip']}:{client_info['port']} ({name}) の接続を終了")  # 切断通知
                del clients[name]                                 # クライアント情報を削除
        conn.close()                                              # 接続を閉じる

def watch_for_esc():                                              # ESCキーを監視してサーバを終了する関数
    global server_running
    print("[操作] ESCキーでサーバを終了できます")                  # 操作案内を表示
    while server_running:
        if msvcrt.kbhit():                                        # キー入力があるか確認
            key = msvcrt.getch()                                  # 入力キーを取得
            if key == b'\x1b':  # ESCキー                         # ESCキーが押されたら
                print("\n[操作] ESCキーが押されました。サーバを終了します。")  # 終了通知
                server_running = False                            # サーバ稼働フラグをFalseに
                break

def start_server(host='localhost', port=9000):                    # サーバを起動する関数
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # TCPソケットを作成
    server.bind((host, port))                                    # 指定ホスト・ポートでバインド
    server.listen()                                              # 接続待機状態にする
    print(f"[起動] BlackBoardサーバが {host}:{port} で待機中...")  # 起動ログ表示

    esc_thread = threading.Thread(target=watch_for_esc, daemon=True)  # ESCキー監視スレッド作成（デーモン）
    esc_thread.start()                                               # ESC監視スレッド開始

    try:
        while server_running:                                       # サーバが稼働中の間
            server.settimeout(1.0)                                  # 1秒ごとにタイムアウトチェック
            try:
                conn, addr = server.accept()                        # 新しい接続を受け入れる
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)  # クライアント用スレッド
                thread.start()                                      # クライアント処理スレッド開始
            except socket.timeout:                                  # タイムアウトしたら再ループ
                continue
    finally:
        print("[終了] サーバ停止中...")                            # サーバ終了メッセージ
        for client in clients.values():                             # 全クライアント接続を閉じる
            client["conn"].close()
        server.close()                                              # サーバソケットを閉じる

if __name__ == "__main__":                                         # スクリプトが直接実行された場合
    start_server()                                                 # サーバを起動
