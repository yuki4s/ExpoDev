from tkinter import *                         # GUI作成用ライブラリ tkinter をインポート（すべての要素を直接利用）
import socket                                 # サーバとのソケット通信のためのライブラリ
import time                                   # 時間計測（タイマー用）に使用

s = None                                      # ソケット接続オブジェクト
start_time = None                             # タイマー開始時刻を記録
timer_id = None                               # after() による繰り返しタイマー処理のID

# --- ソケット接続処理 ---
def connect_socket():
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)        # TCPソケットを作成
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)      # アドレス再利用を許可
    s.connect(('localhost', 9000))                                # サーバ（localhost:9000）へ接続

    local_ip, local_port = s.getsockname()                        # クライアント側のIPアドレスとポートを取得
    name = "Cmd"                                                  # クライアント名を設定（固定）
    init_msg = f"{name};{local_ip}:{local_port}"                 # 接続初期メッセージを作成
    s.send(init_msg.encode())                                     # サーバへ初期メッセージを送信
    connection_status_label.config(text=f"Connected: {name} ({local_ip}:{local_port})")  # 接続ステータスを表示

# --- コマンド送信（送りっぱなし） ---
def send_command(command):
    if s:                                                         # ソケットが有効な場合のみ
        try:
            s.send(command.encode())                              # コマンド文字列をサーバへ送信
            response_label.config(text=f"Sent: {command}")        # 送信完了メッセージを表示
        except Exception as e:
            response_label.config(text=f"[エラー] 送信失敗: {e}")  # エラーがあれば表示

# --- タイマー更新関数 ---
def update_timer():
    global timer_id
    if start_time is None:                                        # タイマーが開始されていなければ何もしない
        return
    elapsed = time.time() - start_time                            # 経過時間を計算
    minutes = int(elapsed // 60)                                  # 分に変換
    seconds = int(elapsed % 60)                                   # 秒に変換
    thresh = threshold_var.get()                                  # 閾値（秒）を取得
    color = 'red' if elapsed > thresh else 'black'                # 閾値を超えたら赤、それ以外は黒
    timer_label.config(text=f"Elapsed Time: {minutes:02d}:{seconds:02d}", fg=color)  # タイマー表示を更新
    timer_id = root.after(1000, update_timer)                     # 1秒ごとに再実行をスケジューリング

# --- リセット処理 ---
def send_reset_command():
    global start_time, timer_id
    if timer_id:                                                  # タイマーが動いていれば停止
        root.after_cancel(timer_id)
        timer_id = None
    start_time = None                                             # タイマー開始時刻をリセット
    timer_label.config(text="Elapsed Time: 00:00", fg='black')    # 表示を初期化

    send_command("BM;reset")                                      # サーバへリセットコマンド送信
    user_id_menu.config(state=NORMAL)                             # ユーザID入力を再度有効化
    condition1_radio.config(state=NORMAL)                         # 条件選択ラジオボタンを有効化
    condition2_radio.config(state=NORMAL)
    start_button.config(state=NORMAL, text="Start")               # スタートボタンを有効化
    reset_button.config(state=NORMAL)                             # リセットボタンも有効のまま
    emergency_button.config(state=DISABLED)                       # 緊急停止は無効化

# --- スタート処理 ---
def start_pressed():
    global start_time
    start_time = time.time()                                      # 現在時刻を開始時刻として記録
    update_timer()                                                # タイマー更新処理を開始

    am_command = f"BM;ID:{user_id.get()},Cond:{condition.get()}"  # ユーザIDと条件をコマンド化
    send_command(am_command)                                      # サーバに送信
    user_id_menu.config(state=DISABLED)                           # 入力欄をロック
    condition1_radio.config(state=DISABLED)
    condition2_radio.config(state=DISABLED)
    start_button.config(state=DISABLED)                           # スタートボタンを無効化
    reset_button.config(state=NORMAL)                             # リセットは可能に
    emergency_button.config(state=NORMAL)                         # 緊急停止も可能に

# --- 緊急停止処理 ---
def send_emergency_stop_command():
    global timer_id
    if timer_id:                                                  # タイマーが動いていれば停止（表示はそのまま）
        root.after_cancel(timer_id)
        timer_id = None

    send_command("BM;emergency_stop")                             # 緊急停止コマンドを送信
    user_id_menu.config(state=DISABLED)                           # 入力はすべてロック
    condition1_radio.config(state=DISABLED)
    condition2_radio.config(state=DISABLED)
    start_button.config(state=DISABLED)
    reset_button.config(state=NORMAL)
    emergency_button.config(state=DISABLED)                       # 緊急停止ボタンは押せなくする

# --- ESCキーによる強制終了 ---
def handle_esc(event):
    root.destroy()                                                # ウィンドウを閉じてアプリ終了

# --- GUI 初期化 ---
root = Tk()                                                       # GUIウィンドウの作成
root.title("CmdClient GUI")                                       # ウィンドウタイトルを設定
root.geometry("450x500")                                          # ウィンドウサイズを指定
root.bind("<Escape>", handle_esc)                                 # ESCキーで終了できるようにバインド

threshold_var = IntVar(value=60)                                  # タイマーのアラート閾値を秒で設定（初期60秒）

user_id = IntVar(value=1)                                         # ユーザID（1〜100）
condition = StringVar(value="1")                                  # 条件選択（文字列型）

Label(root, text="ID (1-100):").pack()                            # ユーザID入力ラベル
user_id_menu = Spinbox(root, from_=1, to=100, textvariable=user_id, width=5)  # ID入力スピンボックス
user_id_menu.pack(pady=5)

condition1_radio = Radiobutton(root, text="条件1", variable=condition, value="1")  # 条件1ラジオボタン
condition1_radio.pack()
condition2_radio = Radiobutton(root, text="条件2", variable=condition, value="2")  # 条件2ラジオボタン
condition2_radio.pack()

Label(root, text="Alert Threshold (sec):").pack(pady=(20,0))      # 閾値入力ラベル
threshold_spinbox = Spinbox(root, from_=1, to=3600, textvariable=threshold_var, width=5)  # 閾値スピンボックス
threshold_spinbox.pack(pady=5)

start_button = Button(root, text="Start", command=start_pressed, height=2, width=20)  # Startボタン
start_button.pack(pady=5)

reset_button = Button(root, text="Reset", command=send_reset_command, height=2, width=20)  # Resetボタン
reset_button.pack(pady=5)

emergency_button = Button(                                          # Emergency Stopボタン
    root,
    text="Emergency Stop",
    command=send_emergency_stop_command,
    height=2,
    width=20,
    fg="white",
    bg="red"
)
emergency_button.pack(pady=5)

timer_label = Label(root, text="Elapsed Time: 00:00", font=("Helvetica", 14))  # 経過時間表示ラベル
timer_label.pack(pady=10)

start_button.config(state=NORMAL)                                   # 起動時は Start ボタン有効
reset_button.config(state=NORMAL)                                   # Reset も有効
emergency_button.config(state=DISABLED)                             # Emergency Stop は無効化

connection_status_label = Label(root, text="Not Connected")         # 接続状況表示ラベル
connection_status_label.pack(pady=10)

response_label = Label(root, text="")                               # 応答・ログメッセージ表示ラベル
response_label.pack()

connect_socket()                                                    # ソケット接続を確立
root.mainloop()                                                     # GUIメインループ開始