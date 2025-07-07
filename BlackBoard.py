# BlackBoard.py

import socket                                   # ソケット通信を行うための標準ライブラリ
import threading                                # スレッド処理用標準ライブラリ
import msvcrt                                   # WindowsでESCキー検出用

###### ログ記録設定 #########

import logging                                  # ログ出力用モジュール
import os                                      # OS操作用
import glob                                    # ファイル検索用
import re                                      # 正規表現
import json                                    # 設定ファイル読み込み用
import time                                    # 待機処理用

# --- ログ記録用関数 ---
def initialize_blackboard_logging():
    """
    logging_config.json の設定に基づき、BlackBoard用ログをLog/BlackBoardLogに保存する。
    保存しない設定なら、標準出力のみのロガーを構成する。
    """
    try:
        with open("logging_config.json", "r", encoding="utf-8") as f:  # 設定ファイルを開く
            config_data = json.load(f)                                 # JSONデータを辞書として読み込み
        save_blackboard_logs = config_data.get("save_blackboard_logs", False)  # ログ保存ON/OFFを取得（デフォルトFalse）
        print(f"[設定] save_blackboard_logs={save_blackboard_logs}")  # 設定内容をコンソールに出力
    except Exception as e:                                            # 設定ファイル読み込み失敗時
        print(f"[設定エラー] logging_config.json の読み込みに失敗しました: {e}")  # エラーメッセージを出力
        save_blackboard_logs = False                                  # ログ保存はOFFに設定

    log_dir = os.path.join("Log", "BlackBoardLog")        # ログ保存ディレクトリを作成
    os.makedirs(log_dir, exist_ok=True)                  # ディレクトリが無ければ作成する

    logger = logging.getLogger()                         # ルートロガーを取得
    logger.setLevel(logging.INFO)                       # ログレベルをINFOに設定

    if logger.hasHandlers():                            # 既にハンドラがある場合
        logger.handlers.clear()                        # 古いハンドラを削除

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')  # フォーマット作成

    console_handler = logging.StreamHandler()           # コンソール用ハンドラ作成
    console_handler.setLevel(logging.INFO)              # INFOレベルに設定
    console_handler.setFormatter(formatter)             # フォーマット適用
    logger.addHandler(console_handler)                  # ハンドラ追加

    if save_blackboard_logs:                            # ログ保存がONの場合
        existing_logs = glob.glob(os.path.join(log_dir, "log*_blackBoard.log"))  # 既存ログファイルを探索
        max_index = 0                                   # ログ番号最大値を初期化
        for log_file in existing_logs:                  # 既存ログを走査
            match = re.match(r".*log(\d+)_blackBoard\.log$", log_file)  # ログ番号抽出
            if match:
                idx = int(match.group(1))               # 抽出番号をint変換
                if idx > max_index: max_index = idx     # 最大値更新

        next_index = max_index + 1                     # 次に使うログ番号決定
        log_filename = os.path.join(log_dir, f"log{next_index}_blackBoard.log")  # ログファイル名作成
        print(f"[ログ初期化] ログファイル: {log_filename}")                     # ログファイル名を表示

        file_handler = logging.FileHandler(log_filename, encoding="utf-8")  # ファイル用ハンドラ作成
        file_handler.setLevel(logging.INFO)              # INFOレベル設定
        file_handler.setFormatter(formatter)             # フォーマット適用
        logger.addHandler(file_handler)                  # ハンドラ追加

###### ---BlackBoard処理内容--- #########

clients = {}                                            # 接続中クライアントを格納する辞書
server_running = True                                   # サーバ実行フラグ
exit_acks_received = set()                             # EXIT受領ACKを受け取ったクライアント名の集合

def send_exit_to_all_clients():                        # 全クライアントにEXITを送信する関数
    logging.info("[CMD] 全クライアントにEXITを送信中...")
    for client_name, client_info in list(clients.items()):  # 接続中クライアントを走査
        try:
            client_info["conn"].sendall(b"EXIT")       # 各クライアントにEXITを送信
            logging.info(f"[CMD] {client_name} に EXIT を送信しました。")
        except Exception as e:
            logging.error(f"[CMD] {client_name} へのEXIT送信に失敗: {e}")

    expected_acks = set(clients.keys())               # 期待するACK送信元クライアント集合
    timeout = 5.0                                     # ACK待機の最大時間（秒）
    start_time = time.time()                          # 待機開始時間を取得
    while time.time() - start_time < timeout:         # タイムアウトまで待機
        if exit_acks_received >= expected_acks:       # すべてのACKを受領したら終了
            logging.info("[CMD] 全クライアントからEXIT受領ACKを確認しました。")
            return
        time.sleep(0.1)                               # ACKを待機しつつループ
    missing = expected_acks - exit_acks_received      # 未受領クライアントを計算
    if missing:
        logging.warning(f"[CMD] タイムアウト: 以下のクライアントからACKが未受領: {missing}")

def handle_client(conn, addr):                        # クライアント接続を処理する関数
    global server_running
    name = None                                       # クライアント名変数
    try:
        init_msg = conn.recv(1024).decode().strip()   # 初期メッセージを受信しデコード

        if ";" in init_msg and ":" in init_msg:       # 初期メッセージ形式を確認
            name_part, ip_port_part = init_msg.split(";", 1)  # 名前・IP:PORTを分割
            ip, port_str = ip_port_part.split(":", 1)         # IPとPORTを分割
            name = name_part.strip()                         # クライアント名
            reported_ip = ip.strip()                         # IP
            reported_port = int(port_str.strip())            # PORT
        else:
            conn.sendall("[エラー] 初期メッセージ形式が不正です。'名前;IP:PORT'の形式で送信してください。".encode())
            conn.close()
            return

        if name in clients:                                # 名前重複を確認
            error_msg = f"[拒否] 名前 '{name}' はすでに使用されています。他の名前で接続してください。"
            logging.error(error_msg)
            conn.sendall(error_msg.encode())
            conn.close()
            return

        logging.info(f"[接続] {name} ({reported_ip}:{reported_port}) が接続しました")
        clients[name] = { "conn": conn, "ip": reported_ip, "port": reported_port }  # クライアントを登録

        while server_running:                            # サーバ稼働中ループ
            try:
                data = conn.recv(1024)                   # クライアントからデータ受信
                if not data: break                      # データが空なら切断扱い
                message = data.decode().strip()         # デコードしてメッセージ取得
                logging.info(f"[受信] {name} → {message}")

                if message == "CMD;shutdown":           # CMD;shutdown受信時
                    logging.info("[CMD] CMD;shutdown を受信しました。全クライアントに終了指示を送信します。")
                    send_exit_to_all_clients()          # 全クライアントにEXIT送信＆ACK確認
                    server_running = False              # すべて完了後にサーバ停止
                    break                               # クライアントループ終了

                elif message.startswith("ACK;EXIT_RECEIVED"):  # クライアントからのEXIT ACK
                    logging.info(f"[ACK受信] {name} からEXIT受領確認を受信しました。")
                    exit_acks_received.add(name)

                elif ";" in message:                    # メッセージが;を含む場合は転送
                    target_name, content = message.split(";", 1)  # 宛先と内容を分割
                    target = clients.get(target_name)   # 宛先を取得
                    if target:
                        target["conn"].sendall(content.encode())  # 宛先に転送
                        logging.info(f"[転送] {name} → {target_name} : {content}")
                    else:
                        err_msg = f"[エラー] 宛先 '{target_name}' が見つかりません"
                        conn.sendall(err_msg.encode())
                        logging.error(err_msg)
                else:
                    err_msg = "[エラー] メッセージは '宛先名;内容' の形式で送信してください"
                    conn.sendall(err_msg.encode())
                    logging.error(err_msg)
            except Exception as e:
                logging.error(f"[エラー] 受信中に例外発生：{e}")
                break
    finally:
        if name:
            client_info = clients.get(name)
            if client_info:
                logging.info(f"[切断] {client_info['ip']}:{client_info['port']} ({name}) の接続を終了")
                del clients[name]
        conn.close()

def watch_for_esc():                                   # ESCキー押下でサーバ終了を監視する関数
    global server_running
    logging.info("[操作] ESCキーでサーバを終了できます")
    while server_running:
        if msvcrt.kbhit():                            # キーボード入力を検出
            key = msvcrt.getch()                      # 入力キーを取得
            if key == b'\x1b':                        # ESCキーの場合
                logging.info("[操作] ESCキーが押されました。サーバを終了します。")
                server_running = False
                break

def start_server(host='localhost', port=9000):        # サーバを起動する関数
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPソケット作成
    server.bind((host, port))                         # ホスト・ポートにバインド
    server.listen()                                   # 接続待機状態にする
    logging.info(f"[起動] BlackBoardサーバが {host}:{port} で待機中...")

    esc_thread = threading.Thread(target=watch_for_esc, daemon=True)  # ESC監視スレッド作成
    esc_thread.start()

    try:
        while server_running:                        # サーバ稼働中ループ
            server.settimeout(1.0)                   # 1秒ごとにacceptをタイムアウトしてESC監視
            try:
                conn, addr = server.accept()         # クライアント接続受付
                thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)  # クライアントごとにスレッド作成
                thread.start()
            except socket.timeout:                   # タイムアウト時
                continue                             # ESC監視へ戻る
    finally:
        logging.info("[終了] サーバ停止中...")
        for client in clients.values():              # 接続中クライアント全ての接続を閉じる
            client["conn"].close()
        server.close()                               # サーバソケットを閉じる

if __name__ == "__main__":                           # スクリプトが直接実行されたときのみ
    initialize_blackboard_logging()                 # ログ初期化
    start_server()                                  # サーバ起動
