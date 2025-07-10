from tkinter import *                          # Tkinter GUIモジュールの全機能をインポート
import socket                                  # ソケット通信を行うための標準ライブラリ
import time                                    # 時間計測用の標準ライブラリ

s = None                                       # ソケットオブジェクトの初期化
start_time = None                              # タイマーの開始時間を記録する変数
timer_id = None                                # Tkinterのafter()用ID（タイマー更新用）

# --- ソケット接続処理 ---
def connect_socket():
    global s
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)                   # TCPソケットを作成
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)                # アドレス再利用オプションを設定
        s.connect(('localhost', 9000))                                          # ローカルホストのポート9000に接続
        local_ip, local_port = s.getsockname()                                 # 自分のIPとポートを取得
        name = "Cmd"                                                           # クライアント名を設定
        init_msg = f"{name};{local_ip}:{local_port}"                          # 初期化メッセージを作成
        s.send(init_msg.encode())                                              # メッセージをエンコードして送信
        connection_status_label.config(text=f"Connected: {name} ({local_ip}:{local_port})")  # GUIに接続情報を表示
    except Exception as e:
        connection_status_label.config(text=f"Socket Error: {e}")             # エラー発生時にステータスに表示

# --- コマンド送信（送りっぱなし） ---
def send_command(command):
    if s:
        try:
            s.send((command + "\n").encode())                                           # 文字列をエンコードしてソケットに送信
            response_label.config(text=f"Sent: {command}")                     # GUIに送信内容を表示
        except Exception as e:
            response_label.config(text=f"[エラー] 送信失敗: {e}")              # 送信エラーを表示

# --- タイマー更新関数 ---
def update_timer():
    global timer_id
    if start_time is None:                                                     # 開始時間が未設定なら終了
        return
    elapsed = time.time() - start_time                                         # 経過時間を計算
    minutes = int(elapsed // 60)                                               # 分を整数に変換
    seconds = int(elapsed % 60)                                                # 秒を整数に変換
    thresh = threshold_var.get()                                               # 閾値（秒）を取得
    color = 'red' if elapsed > thresh else 'black'                             # 閾値を超えたら赤にする
    timer_label.config(text=f"Elapsed Time: {minutes:02d}:{seconds:02d}", fg=color)  # タイマー表示を更新
    timer_id = root.after(1000, update_timer)                                  # 1秒後に再実行

# --- リセット処理 ---
def send_reset_command():
    global timer_id, start_time
    if timer_id is not None:
        root.after_cancel(timer_id)                                            # タイマーをキャンセル
        timer_id = None
    start_time = None                                                          # 開始時間を初期化
    timer_label.config(text="Elapsed Time: 00:00", fg='black')                 # タイマー表示をリセット

    send_command("BM;reset")                                                   # BlackBoardにリセットコマンド送信
    send_command("VM;stop_log_recording")                                       # VisionManagerにログ記録終了コマンドを送信                     
    user_id_menu.config(state=NORMAL)                                          # ユーザIDの入力を有効化
    for rb in (condition1_radio, condition2_radio, condition3_radio):          # 条件選択を有効化
        rb.config(state=NORMAL)
    start_button.config(state=NORMAL, text="Start")                            # スタートボタンを有効化
    reset_button.config(state=NORMAL)                                          # リセットボタンも有効化

# --- スタート処理 ---
def start_pressed():
    global start_time
    start_time = time.time()                                                   # 現在時刻を開始時間として記録
    update_timer()                                                             # タイマー開始

    bm_command = f"BM;ID:{user_id.get()},Cond:{condition.get()}"              # IDと条件を含むコマンド文字列を生成
    send_command(bm_command)                                                  # コマンドを送信
    vm_command = f"VM;ID:{user_id.get()},Cond:{condition.get()}"              # IDと条件を含むコマンド文字列を生成
    send_command(vm_command)                                                  # コマンドを送信
    send_command("VM;start_log_recording")                                    # VisionManagerにログ記録開始コマンドを送信
    send_command("SM;AM2_00_ShogoNomura_SoundCloud")
    user_id_menu.config(state=DISABLED)                                        # 入力UIを無効化
    for rb in (condition1_radio, condition2_radio, condition3_radio):          # 条件選択を無効化
        rb.config(state=DISABLED)
    start_button.config(state=DISABLED)                                        # スタートボタンを無効化
    reset_button.config(state=NORMAL)                                          # リセットボタンは有効化

# --- ESCキーによる強制終了 ---
def handle_esc(event):
    root.destroy()                                                             # ウィンドウを閉じてアプリ終了

# --- GUI 初期化 ---
root = Tk()                                                                    # メインウィンドウの作成
root.title("CmdClient GUI")                                                    # ウィンドウタイトルを設定
root.geometry("450x500")                                                       # ウィンドウサイズを指定
root.bind("<Escape>", handle_esc)                                              # ESCキーで終了できるようにバインド

threshold_var = IntVar(value=40)                                               # 閾値（秒）の初期値を40に設定

# ユーザID & 条件選択
user_id    = IntVar(value=1)                                                   # ユーザID（整数）の初期値を1
condition  = StringVar(value="1")                                              # 条件（文字列）の初期値を"1"

Label(root, text="ID (1-100):").pack()                                         # ID入力用ラベルを配置
user_id_menu = Spinbox(root, from_=1, to=100, textvariable=user_id, width=5)  # ID入力用スピンボックス
user_id_menu.pack(pady=5)

condition1_radio = Radiobutton(root, text="条件1", variable=condition, value="1")  # 条件1ラジオボタン
condition1_radio.pack()
condition2_radio = Radiobutton(root, text="条件2", variable=condition, value="2")  # 条件2ラジオボタン
condition2_radio.pack()
condition3_radio = Radiobutton(root, text="条件3", variable=condition, value="3")  # 条件3ラジオボタン
condition3_radio.pack()

# 閾値設定用スピンボックス
Label(root, text="Alert Threshold (sec):").pack(pady=(20,0))                   # 閾値用ラベル
threshold_spinbox = Spinbox(root, from_=1, to=3600, textvariable=threshold_var, width=5)  # 閾値設定
threshold_spinbox.pack(pady=5)

# 操作ボタン
start_button = Button(root, text="Start", command=start_pressed, height=2, width=20)  # スタートボタン
start_button.pack(pady=5)

reset_button = Button(root, text="Reset", command=send_reset_command, height=2, width=20)  # リセットボタン
reset_button.pack(pady=5)

# タイマー表示用ラベル
timer_label = Label(root, text="Elapsed Time: 00:00", font=("Helvetica", 14)) # 経過時間表示ラベル
timer_label.pack(pady=10)

# ステータス表示
connection_status_label = Label(root, text="Not Connected")                   # 接続状態ラベル
connection_status_label.pack(pady=10)

response_label = Label(root, text="")                                          # 送信結果表示用ラベル
response_label.pack()

# 初期状態設定
start_button.config(state=NORMAL)                                              # スタートボタン初期状態（有効）
reset_button.config(state=NORMAL)                                              # リセットボタン初期状態（有効）

connect_socket()                                                               # ソケット接続を試みる
root.mainloop()                                                                # GUIのメインループ開始
