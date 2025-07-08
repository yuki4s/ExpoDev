from tkinter import *
import socket
import time

s = None
start_time = None
timer_id = None

# --- ソケット接続処理 ---
def connect_socket():
    global s
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect(('localhost', 9000))
        local_ip, local_port = s.getsockname()
        name = "Cmd"
        init_msg = f"{name};{local_ip}:{local_port}"
        s.send(init_msg.encode())
        connection_status_label.config(text=f"Connected: {name} ({local_ip}:{local_port})")
    except Exception as e:
        connection_status_label.config(text=f"Socket Error: {e}")

# --- コマンド送信（送りっぱなし） ---
def send_command(command):
    if s:
        try:
            s.send(command.encode())
            response_label.config(text=f"Sent: {command}")
        except Exception as e:
            response_label.config(text=f"[エラー] 送信失敗: {e}")

# --- タイマー更新関数 ---
def update_timer():
    global timer_id
    if start_time is None:
        return
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    thresh = threshold_var.get()
    color = 'red' if elapsed > thresh else 'black'
    timer_label.config(text=f"Elapsed Time: {minutes:02d}:{seconds:02d}", fg=color)
    timer_id = root.after(1000, update_timer)

# --- リセット処理 ---
def send_reset_command():
    global timer_id, start_time
    if timer_id is not None:
        root.after_cancel(timer_id)
        timer_id = None
    start_time = None
    timer_label.config(text="Elapsed Time: 00:00", fg='black')

    send_command("BM;reset")
    user_id_menu.config(state=NORMAL)
    for rb in (condition1_radio, condition2_radio, condition3_radio):
        rb.config(state=NORMAL)
    start_button.config(state=NORMAL, text="Start")
    reset_button.config(state=NORMAL)

# --- スタート処理 ---
def start_pressed():
    global start_time
    start_time = time.time()
    update_timer()

    am_command = f"BM;ID:{user_id.get()},Cond:{condition.get()}"
    send_command(am_command)
    user_id_menu.config(state=DISABLED)
    for rb in (condition1_radio, condition2_radio, condition3_radio):
        rb.config(state=DISABLED)
    start_button.config(state=DISABLED)
    reset_button.config(state=NORMAL)

# --- ESCキーによる強制終了 ---
def handle_esc(event):
    root.destroy()

# --- GUI 初期化 ---
root = Tk()
root.title("CmdClient GUI")
root.geometry("450x500")
root.bind("<Escape>", handle_esc)

# Threshold 変数は root のあとに作成
threshold_var = IntVar(value=40)

# ユーザID & 条件選択
user_id    = IntVar(value=1)
condition  = StringVar(value="1")

Label(root, text="ID (1-100):").pack()
user_id_menu = Spinbox(root, from_=1, to=100, textvariable=user_id, width=5)
user_id_menu.pack(pady=5)

condition1_radio = Radiobutton(root, text="条件1", variable=condition, value="1")
condition1_radio.pack()
condition2_radio = Radiobutton(root, text="条件2", variable=condition, value="2")
condition2_radio.pack()
condition3_radio = Radiobutton(root, text="条件3", variable=condition, value="3")
condition3_radio.pack()

# 閾値設定用スピンボックス
Label(root, text="Alert Threshold (sec):").pack(pady=(20,0))
threshold_spinbox = Spinbox(root, from_=1, to=3600, textvariable=threshold_var, width=5)
threshold_spinbox.pack(pady=5)

# 操作ボタン
start_button = Button(root, text="Start", command=start_pressed, height=2, width=20)
start_button.pack(pady=5)

reset_button = Button(root, text="Reset", command=send_reset_command, height=2, width=20)
reset_button.pack(pady=5)

# タイマー表示用ラベル
timer_label = Label(root, text="Elapsed Time: 00:00", font=("Helvetica", 14))
timer_label.pack(pady=10)

# ステータス表示
connection_status_label = Label(root, text="Not Connected")
connection_status_label.pack(pady=10)

response_label = Label(root, text="")
response_label.pack()

# 初期状態設定
start_button.config(state=NORMAL)
reset_button.config(state=NORMAL)

connect_socket()
root.mainloop()
