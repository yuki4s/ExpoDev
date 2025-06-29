# BlackBoard.py

import socket                                   # ソケット通信を行うための標準ライブラリ
import threading                                # スレッド処理用標準ライブラリ
import msvcrt                                   # WindowsでESCキー検出用

###### ログ記録設定 #########

import logging                                  # ログ出力用モジュール
from datetime import datetime                   # タイムスタンプ用
import os                                          # OS操作用
import glob                                        # ファイル検索用
import re                                          # 正規表現用

log_dir = "Log"                                    # ログフォルダ名
os.makedirs(log_dir, exist_ok=True)               # ログフォルダがなければ作成

# Logフォルダ内のlog*.logをすべて取得
existing_logs = glob.glob(os.path.join(log_dir, "log*.log"))

max_index = 0                                     # ログ番号の最大値を初期化
for log_file in existing_logs:
    match = re.match(r".*log(\d+)\.log$", log_file)  # ファイル名から番号を抽出
    if match:
        idx = int(match.group(1))                 # 抽出した番号を整数に変換
        if idx > max_index:
            max_index = idx                      # 最大値を更新

next_index = max_index + 1                       # 次のログ番号を決定
log_filename = os.path.join(log_dir, f"log{next_index}.log")  # ファイル名作成

logging.basicConfig(                           # ログの基本設定
    filename=log_filename,                     # ログファイル出力先
    level=logging.INFO,                        # ログレベルINFO以上を出力
    format='%(asctime)s [%(levelname)s] %(message)s',  # ログ出力フォーマット
    datefmt='%Y-%m-%d %H:%M:%S'                # タイムスタンプ形式
)

console_handler = logging.StreamHandler()      # コンソール出力用ハンドラ作成
console_handler.setLevel(logging.INFO)         # INFO以上を表示
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')  # コンソールのフォーマット
console_handler.setFormatter(formatter)        # ハンドラにフォーマットを設定
logging.getLogger().addHandler(console_handler)  # ルートロガーにハンドラを追加

###### BlackBoard処理内容 #########

clients = {}                                    # 接続中クライアントの情報を格納する辞書
server_running = True                           # サーバ実行中フラグ

def handle_client(conn, addr):                  # クライアントごとの接続を処理する関数
    name = None                                 # クライアント名を格納する変数
    try:
        init_msg = conn.recv(1024).decode().strip()  # 初回メッセージを受信しデコード

        if ";" in init_msg and ":" in init_msg:     # メッセージに';'と':'が含まれるか確認
            name_part, ip_port_part = init_msg.split(";", 1)     # 名前とIP:PORT部分に分割
            ip, port_str = ip_port_part.split(":", 1)            # IPとPORTに分割
            name = name_part.strip()                             # クライアント名
            reported_ip = ip.strip()                             # クライアントIP
            reported_port = int(port_str.strip())                # クライアントPORT（int変換）
        else:
            conn.sendall("[エラー] 初期メッセージ形式が不正です。'名前;IP:PORT'の形式で送信してください。".encode())  # エラーメッセージ送信
            conn.close()                                        # 接続終了
            return

        if name in clients:                                    # 同じ名前がすでにclientsに存在するか確認
            error_msg = f"[拒否] 名前 '{name}' はすでに使用されています。他の名前で接続してください。"
            logging.error(error_msg)                           # エラーをログ出力
            conn.sendall(error_msg.encode())                   # エラーメッセージ送信
            conn.close()                                       # 接続終了
            return

        logging.info(f"[接続] {name} ({reported_ip}:{reported_port}) が接続しました")  # 接続成功をログ出力
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
                logging.info(f"[受信] {name} → {message}")     # 受信内容をログ出力

                if ";" in message:                            # メッセージが';'を含むか確認
                    target_name, content = message.split(";", 1)  # 宛先名と内容に分割
                    target = clients.get(target_name)             # 宛先クライアント情報を取得
                    if target:                                   # 宛先が存在すれば
                        target["conn"].sendall(content.encode())  # 宛先にメッセージを送信
                        logging.info(f"[転送] {name} → {target_name} : {content}")  # 転送内容をログ出力
                    else:
                        err_msg = f"[エラー] 宛先 '{target_name}' が見つかりません"
                        conn.sendall(err_msg.encode())            # 宛先不明のエラーメッセージ送信
                        logging.error(err_msg)                    # エラーをログ出力
                else:
                    err_msg = "[エラー] メッセージは '宛先名;内容' の形式で送信してください"
                    conn.sendall(err_msg.encode())               # メッセージ形式不正時
                    logging.error(err_msg)                       # エラーをログ出力

            except Exception as e:
                logging.error(f"[エラー] 受信中に例外発生：{e}")  # 受信中に例外が発生した場合ログ出力
                break

    finally:
        if name:                                               # クライアント名が取得できている場合
            client_info = clients.get(name)                    # 登録情報を取得
            if client_info:
                logging.info(f"[切断] {client_info['ip']}:{client_info['port']} ({name}) の接続を終了")  # 切断をログ出力
                del clients[name]                              # クライアント情報を辞書から削除
        conn.close()                                           # 接続をクローズ

def watch_for_esc():                                           # ESCキー押下でサーバを終了する監視スレッド
    global server_running
    logging.info("[操作] ESCキーでサーバを終了できます")        # ESC監視開始をログ出力
    while server_running:
        if msvcrt.kbhit():                                     # キーボード入力を検出
            key = msvcrt.getch()                               # 押されたキーを取得
            if key == b'\x1b':  # ESCキー                      # ESCキーが押された場合
                logging.info("[操作] ESCキーが押されました。サーバを終了します。")  # ESC押下をログ出力
                server_running = False                        # サーバ稼働フラグをFalseに
                break

def start_server(host='localhost', port=9000):                 # サーバ起動関数
    global server_running
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPソケットを作成
    server.bind((host, port))                                   # 指定ホスト・ポートにバインド
    server.listen()                                             # 接続待機状態にする
    logging.info(f"[起動] BlackBoardサーバが {host}:{port} で待機中...")  # サーバ起動をログ出力

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
        logging.info("[終了] サーバ停止中...")                # サーバ停止開始をログ出力
        for client in clients.values():                        # 接続中クライアント全ての接続を閉じる
            client["conn"].close()
        server.close()                                         # サーバソケットを閉じる

if __name__ == "__main__":                                    # スクリプトが直接実行されたときのみ
    start_server()                                             # サーバ起動
