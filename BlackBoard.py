import socket                                   # ソケット通信を行うための標準ライブラリ
import threading                                # 並列処理用のスレッドライブラリ
import msvcrt                                   # Windows専用：キーボード入力を非同期で検出するためのライブラリ（ESCキー検出に使用）

clients = {}                                    # 接続中のクライアント情報を保持する辞書
server_running = True                           # サーバの稼働状態を示すフラグ

def handle_client(conn, addr):                  # クライアントごとの通信処理を行う関数（スレッドごとに実行）
    name = None
    try:
        init_msg = conn.recv(1024).decode().strip()  # 初回にクライアント名とアドレス情報を受信

        # 名前とIP:PORTのパース
        if ";" in init_msg and ":" in init_msg:      # 正しい形式（名前;IP:PORT）か確認
            name_part, ip_port_part = init_msg.split(";", 1)       # 名前とIP:PORTに分割
            ip, port_str = ip_port_part.split(":", 1)              # IPとPORTに分割
            name = name_part.strip()                               # クライアント名を取得
            reported_ip = ip.strip()                               # IPアドレスを取得
            reported_port = int(port_str.strip())                  # ポート番号を取得
        else:
            # 不正な形式
            conn.sendall("[エラー] 初期メッセージ形式が不正です。'名前;IP:PORT'の形式で送信してください。".encode())  # エラー送信
            conn.close()                                           # 接続を閉じる
            return

        # 同名クライアントがすでに存在する場合は拒否
        if name in clients:
            error_msg = f"[拒否] 名前 '{name}' はすでに使用されています。他の名前で接続してください。"  # 重複名エラー
            print(error_msg)
            conn.sendall(error_msg.encode())                       # クライアントにエラーを通知
            conn.close()                                           # 接続を閉じる
            return

        print(f"[接続] {name} ({reported_ip}:{reported_port}) が接続しました")  # 接続ログ表示
        clients[name] = {                                          # クライアント情報を登録
            "conn": conn,
            "ip": reported_ip,
            "port": reported_port
        }

        while server_running:                                     # サーバが稼働中の間、クライアントからの受信処理を継続
            try:
                data = conn.recv(1024)                             # クライアントからデータを受信
                if not data:
                    break                                          # 空データなら切断とみなす

                message = data.decode().strip()                    # メッセージをデコード
                print(f"[受信] {name} → {message}")                # 受信ログを表示

                # メッセージ形式: 宛先名;メッセージ内容
                if ";" in message:
                    target_name, content = message.split(";", 1)  # 宛先名と内容に分割
                    target = clients.get(target_name)             # 宛先のクライアントを検索
                    if target:
                        target["conn"].sendall(content.encode())  # 宛先にメッセージを転送
                        print(f"[転送] {name} → {target_name} : {content}")  # 転送ログ表示
                    else:
                        conn.sendall(f"[エラー] 宛先 '{target_name}' が見つかりません".encode())  # 宛先が見つからない場合
                else:
                    conn.sendall("[エラー] メッセージは '宛先名;内容' の形式で送信してください".encode())  # 不正な形式の場合

            except Exception as e:
                print(f"[エラー] 受信中に例外発生：{e}")            # 受信中にエラーが発生した場合に表示
                break

    finally:
        if name:
            client_info = clients.get(name)
            if client_info:
                print(f"[切断] {client_info['ip']}:{client_info['port']} ({name}) の接続を終了")  # 切断ログを表示
                del clients[name]                               # クライアント辞書から削除
        conn.close()                                            # ソケットを閉じる

def watch_for_esc():                                            # ESCキー入力を監視する関数（別スレッドで実行）
    global server_running
    print("[操作] ESCキーでサーバを終了できます")               # 操作方法の案内を表示
    while server_running:
        if msvcrt.kbhit():                                      # キーが押されたかチェック
            key = msvcrt.getch()                                # 押されたキーを取得
            if key == b'\x1b':  # ESCキー                        # ESCキー（16進で0x1B）が押されたら
                print("\n[操作] ESCキーが押されました。サーバを終了します。")  # 終了メッセージ表示
                server_running = False                          # サーバ停止フラグをFalseに
                break

def start_server(host='localhost', port=9000):                  # サーバ起動関数（メイン）
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPサーバソケットを作成
    server.bind((host, port))                                  # 指定ホストとポートにバインド
    server.listen()                                            # クライアントからの接続を待ち受け
    print(f"[起動] BlackBoardサーバが {host}:{port} で待機中...")  # 起動ログ表示

    esc_thread = threading.Thread(target=watch_for_esc, daemon=True)  # ESCキー監視スレッドを開始
    esc_thread.start()

    try:
        while server_running:                                  # サーバ稼働中はループ
            server.settimeout(1.0)                              # 1秒ごとにタイムアウトを設定
            try:
                conn, addr = server.accept()                    # クライアントからの接続を受け入れる
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)  # クライアント処理用スレッドを作成
                thread.start()                                  # クライアント処理スレッドを開始
            except socket.timeout:
                continue                                        # タイムアウト時は何もしない（ESC監視のため）

    finally:
        print("[終了] サーバ停止中...")                        # 終了メッセージを表示
        for client in clients.values():                         # 接続中の全クライアントを処理
            client["conn"].close()                              # クライアントとの接続を閉じる
        server.close()                                          # サーバソケットを閉じる

if __name__ == "__main__":                                     # スクリプトが直接実行されたとき
    start_server()                                             # サーバを起動
