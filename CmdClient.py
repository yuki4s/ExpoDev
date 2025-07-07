# CmdClient.py

from tkinter import *                             # GUI作成用のtkinterライブラリをインポート
from tkinter import messagebox
import socket                                     # ソケット通信用標準ライブラリ
import threading                                  # スレッド処理用ライブラリ

s = None                                         # ソケットオブジェクト格納用のグローバル変数

def connect_socket():                            # BlackBoardサーバに接続する関数
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)      # TCPソケットを作成
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)    # アドレス再利用オプションを設定
    s.connect(('localhost', 9000))                             # localhost:9000へ接続

    local_ip, local_port = s.getsockname()                     # 自分側のIP/PORTを取得
    name = "Cmd"                                               # クライアント名としてCmdを使用
    init_msg = f"{name};{local_ip}:{local_port}"               # 初期メッセージを作成
    s.send(init_msg.encode())                                  # 初期メッセージを送信
    connection_status_label.config(text=f"Connected: {name} ({local_ip}:{local_port})")  # 接続情報をGUIに表示

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)  # 受信スレッド作成
    recv_thread.start()                                         # スレッドを開始

def receive_from_blackboard():                                # BlackBoardからのメッセージを受信するスレッド
    global s
    while True:
        try:
            msg = s.recv(1024).decode().strip()               # データを受信してデコード
            if msg:
                print(f"[BlackBoard→CmdClient] {msg}")       # 受信メッセージをコンソール表示
                if msg == "EXIT":                            # EXITを受信した場合
                    print("[終了指示] EXITを受信しました。ACKを返して終了します。")
                    try:
                        s.sendall(b"ACK;EXIT_RECEIVED")      # BlackBoardへACKを送信
                        print("[ACK送信] EXIT受領確認を送信しました。")
                    except Exception as e:
                        print(f"[ACK送信失敗] {e}")
                    root.quit()                              # GUIを終了
                    break                                    # スレッドを終了
        except Exception:
            break                                            # エラー発生時はスレッド終了

def send_command(command):                                   # コマンドをBlackBoardへ送信する関数
    if s:
        try:
            s.send(command.encode())                         # コマンド送信
            response_label.config(text=f"Sent: {command}")   # GUIに送信結果を表示
        except Exception as e:
            response_label.config(text=f"[エラー] 送信失敗: {e}")  # 送信エラーをGUIに表示

def send_reset_command():                                   # リセット用コマンドを送信
    send_command("BM;reset")                                # BM宛にresetを送信
    send_command("VM;reset")                                # VM宛にresetを送信
    user_id_menu.config(state=NORMAL)                      # GUIのID選択を再度有効化
    condition1_radio.config(state=NORMAL)                  # 条件1を有効化
    condition2_radio.config(state=NORMAL)                  # 条件2を有効化
    start_button.config(state=NORMAL, text="Start")        # スタートボタンを有効化

def start_pressed():                                       # Startボタン押下時の処理
    # BM宛にID,条件を含むコマンドを送信
    bm_command = f"BM;ID:{user_id.get()},Cond:{condition.get()}"
    send_command(bm_command)

    # VM宛にID,条件を含むコマンドを送信
    vm_command = f"VM;ID:{user_id.get()},Cond:{condition.get()}"
    send_command(vm_command)

    user_id_menu.config(state=DISABLED)                   # ID選択を無効化
    condition1_radio.config(state=DISABLED)               # 条件1を無効化
    condition2_radio.config(state=DISABLED)               # 条件2を無効化
    start_button.config(state=DISABLED, text="Started")   # スタートボタンを無効化し表示変更

def send_exit_all_command():                              # 全システム終了コマンド送信
    confirm = messagebox.askyesno("確認", "本当にすべて終了してよいですか？\nこの操作は元に戻せません。")
    if confirm:
        send_command("CMD;shutdown")                     # BlackBoardに全終了を指示
        root.quit()                                      # GUIを終了

def handle_esc(event):                                   # ESCキー押下時の終了処理
    send_exit_all_command()                             # Exit All処理を呼び出す

# GUI初期化
root = Tk()                                              # Tkinterメインウィンドウ作成
root.title("CmdClient GUI")                              # ウィンドウタイトル設定
root.geometry("400x300")                                 # ウィンドウサイズ設定
root.bind("<Escape>", handle_esc)                       # ESCキーで終了イベントをバインド

user_id = IntVar(value=1)                               # ID選択用変数（初期値1）
condition = StringVar(value="1")                        # 条件選択用変数（初期値1）

Label(root, text="ID (1-30):").pack()                   # IDラベルをGUIに配置
user_id_menu = Spinbox(root, from_=1, to=30, textvariable=user_id, width=5)  # ID選択スピンボックス
user_id_menu.pack(pady=5)                               # スピンボックスを配置

condition1_radio = Radiobutton(root, text="条件1", variable=condition, value="1")  # 条件1ラジオ
condition1_radio.pack()
condition2_radio = Radiobutton(root, text="条件2", variable=condition, value="2")  # 条件2ラジオ
condition2_radio.pack()

start_button = Button(root, text="Start", command=start_pressed, height=2, width=20)  # Startボタン
start_button.pack(pady=5)

reset_button = Button(root, text="Reset", command=send_reset_command, height=2, width=20)  # Resetボタン
reset_button.pack(pady=5)

exit_all_button = Button(root, text="Exit All", command=send_exit_all_command, height=2, width=20)  # Exit Allボタン
exit_all_button.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-10)  # Exit Allボタン配置

connection_status_label = Label(root, text="Not Connected")  # 接続状態表示用ラベル
connection_status_label.pack(pady=10)
response_label = Label(root, text="")                        # コマンド送受信結果表示用ラベル
response_label.pack()

connect_socket()                                             # サーバ接続を開始
root.mainloop()                                              # GUIメインループを開始
