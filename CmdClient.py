# CmdClient.py

from tkinter import *                         # GUI作成用のtkinterライブラリをインポート
import socket                                 # ソケット通信を行うための標準ライブラリ

s = None                                     # グローバル変数: ソケットオブジェクト格納用

# --- ソケット接続処理 ---
def connect_socket():                        # サーバへ接続する関数
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)      # TCPソケット作成
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)    # ソケットオプション設定
    s.connect(('localhost', 9000))                             # localhost:9000へ接続

    local_ip, local_port = s.getsockname()                     # 自分側のIPアドレスとポート番号を取得
    name = "Cmd"                                               # クライアント名としてCmdを使用
    init_msg = f"{name};{local_ip}:{local_port}"               # 初期メッセージ作成
    s.send(init_msg.encode())                                  # サーバへ初期メッセージ送信
    connection_status_label.config(text=f"Connected: {name} ({local_ip}:{local_port})")  # 接続状態をGUIに表示

# --- コマンド送信（送りっぱなし） ---
def send_command(command):                                    # 任意のコマンド文字列をサーバへ送信する関数
    if s:                                                    # ソケットが接続されていれば
        try:
            s.send(command.encode())                         # コマンドをサーバへ送信
            response_label.config(text=f"Sent: {command}")   # 送信結果をGUIに表示
        except Exception as e:
            response_label.config(text=f"[エラー] 送信失敗: {e}")  # 送信失敗時のエラーメッセージ表示

# --- リセット処理 ---
def send_reset_command():                                    # リセット用コマンドを送信する関数
    send_command("BM;reset")                                 # BM宛にresetコマンド送信
    user_id_menu.config(state=NORMAL)                       # GUIのID選択を再び有効化
    condition1_radio.config(state=NORMAL)                   # 条件1ラジオボタンを有効化
    condition2_radio.config(state=NORMAL)                   # 条件2ラジオボタンを有効化
    start_button.config(state=NORMAL, text="Start")         # スタートボタンを有効化

# --- スタート処理 ---
def start_pressed():                                        # Startボタンが押されたときの処理
    am_command = f"BM;ID:{user_id.get()},Cond:{condition.get()}"  # BM宛にIDと条件を含むコマンドを作成
    send_command(am_command)                               # コマンド送信
    user_id_menu.config(state=DISABLED)                    # ID選択を無効化
    condition1_radio.config(state=DISABLED)                # 条件1ラジオボタンを無効化
    condition2_radio.config(state=DISABLED)                # 条件2ラジオボタンを無効化
    start_button.config(state=DISABLED, text="Started")    # スタートボタンを無効化＆テキスト変更

# --- ESCキーによる強制終了 ---
def handle_esc(event):                                     # ESCキー押下時の終了処理
    root.destroy()                                         # GUIアプリケーションを終了

# --- GUI 初期化 ---
root = Tk()                                                # Tkinterのメインウィンドウ作成
root.title("CmdClient GUI")                                # ウィンドウタイトル設定
root.geometry("400x300")                                   # ウィンドウサイズ設定
root.bind("<Escape>", handle_esc)                         # ESCキーで終了するイベントバインド

user_id = IntVar(value=1)                                 # ID選択用変数（初期値1）
condition = StringVar(value="1")                          # 条件選択用変数（初期値1）

Label(root, text="ID (1-30):").pack()                     # ID選択ラベル
user_id_menu = Spinbox(root, from_=1, to=30, textvariable=user_id, width=5)  # ID選択スピンボックス
user_id_menu.pack(pady=5)                                 # スピンボックスを配置

condition1_radio = Radiobutton(root, text="条件1", variable=condition, value="1")  # 条件1ラジオボタン
condition1_radio.pack()
condition2_radio = Radiobutton(root, text="条件2", variable=condition, value="2")  # 条件2ラジオボタン
condition2_radio.pack()

start_button = Button(root, text="Start", command=start_pressed, height=2, width=20)  # Startボタン
start_button.pack(pady=5)

reset_button = Button(root, text="Reset", command=send_reset_command, height=2, width=20)  # Resetボタン
reset_button.pack(pady=5)

connection_status_label = Label(root, text="Not Connected")  # 接続状態を表示するラベル
connection_status_label.pack(pady=10)
response_label = Label(root, text="")                        # 送受信結果を表示するラベル
response_label.pack()

connect_socket()                                             # アプリ起動時にサーバ接続
root.mainloop()                                              # GUIメインループ開始
