# VisionManager.py

import socket                                    # ソケット通信用ライブラリ
import threading                                 # スレッド処理用ライブラリ
import pyrealsense2 as rs                        # Intel RealSense用Pythonラッパー
import mediapipe as mp                           # MediaPipeライブラリ
import cv2                                       # OpenCVライブラリ
import numpy as np                               # NumPyライブラリ
import time                                      # 時間操作用標準ライブラリ
import os
import glob
import re
import json

# --- ログ設定読み込み ---
try:
    with open("logging_config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)
    SAVE_VIDEO_LOGS = config_data.get("save_video_logs", False)  # 設定が無ければFalse
    print(f"[設定] SAVE_VIDEO_LOGS={SAVE_VIDEO_LOGS}")
except Exception as e:
    print(f"[設定エラー] logging_config.json の読み込みに失敗しました: {e}")
    SAVE_VIDEO_LOGS = False

# --- BlackBoard通信設定 ---
HOST = 'localhost'                              # BlackBoardサーバホスト
PORT = 9000                                     # BlackBoardサーバポート
CLIENT_NAME = 'VM'                              # クライアント名（VisionManager）
s = None                                        # ソケット接続オブジェクト

# --- 解像度・フレームレート設定 ---
frame_width = 640          # 横解像度
frame_height = 480         # 縦解像度
frame_rate = 30            # フレームレート

# --- MediaPipe ハンドモジュールの初期化 ---
mp_hands = mp.solutions.hands                  # MediaPipeのHandsソリューション
mp_drawing = mp.solutions.drawing_utils       # MediaPipeの描画ユーティリティ
mp_drawing_styles = mp.solutions.drawing_styles  # MediaPipeの描画スタイル

# --- RealSense パイプラインの初期化 ---
pipeline = rs.pipeline()                      # RealSense用パイプライン作成
config = rs.config()                          # RealSense用設定作成
config.enable_stream(rs.stream.color, frame_width, frame_height, rs.format.bgr8, frame_rate)  # カラーストリーム設定
config.enable_stream(rs.stream.depth, frame_width, frame_height, rs.format.z16, frame_rate)   # 深度ストリーム設定

# --- 映像ログ記録用関数 ---
def initialize_video_logging():
    """
    Log/BlackBoardLog 内の最大番号を探して、
    次のログ番号を VideoLog にlogN_colorVideo.mp4, logN_depthVideo.mp4 として用意し、
    VideoWriterを返す
    """
    blackboard_log_dir = "Log/BlackBoardLog"
    video_log_dir = "Log/VideoLog"

    os.makedirs(blackboard_log_dir, exist_ok=True)  # 念のためBlackBoardLog作成
    os.makedirs(video_log_dir, exist_ok=True)       # VideoLog作成

    existing_logs = glob.glob(os.path.join(blackboard_log_dir, "log*_blackBoard.log"))

    max_index = 0
    for log_file in existing_logs:
        match = re.match(r".*log(\d+)_blackBoard\.log$", log_file)
        if match:
            idx = int(match.group(1))
            if idx > max_index:
                max_index = idx

    next_index = max_index + 1
    print(f"[ログ初期化] 次のログ番号: {next_index}")

    color_video_filename = os.path.join(video_log_dir, f"log{next_index}_colorVideo.mp4")
    depth_video_filename = os.path.join(video_log_dir, f"log{next_index}_depthVideo.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    log_color_writer = cv2.VideoWriter(color_video_filename, fourcc, frame_rate, (frame_width, frame_height))
    log_depth_writer = cv2.VideoWriter(depth_video_filename, fourcc, frame_rate, (frame_width, frame_height))

    return log_color_writer, log_depth_writer


# --- フレーム取得関数 ---
def safe_wait_for_frames(pipeline, max_retries=5):  # フレーム取得をリトライ付きで行う関数
    for i in range(max_retries):
        try:
            return pipeline.wait_for_frames()       # フレームを取得
        except RuntimeError as e:
            print(f"[警告] フレームの取得に失敗（{i+1}/{max_retries}）: {e}")
            time.sleep(0.5)
    raise RuntimeError("フレーム取得に連続で失敗しました。")  # 最大リトライを超えた場合

# --- BlackBoardからのコマンド受信用スレッド ---
def receive_from_blackboard():                     # BlackBoardからのコマンドを受信するスレッド
    global s
    while True:
        try:
            msg = s.recv(1024).decode()            # BlackBoardからデータ受信
            if msg:
                print(f"[BlackBoard→VM] {msg}")   # 受信メッセージを表示
        except Exception:
            break                                  # エラー発生時はループを終了

# --- ソケット接続処理 ---
def connect_to_blackboard():                      # BlackBoardサーバへ接続する関数
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPソケット作成
    s.connect((HOST, PORT))                                # BlackBoardに接続

    local_ip, local_port = s.getsockname()                # 自分側のIP/ポート取得
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"   # 初期メッセージ作成
    s.sendall(init_msg.encode())                          # 初期メッセージ送信

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)  # BlackBoard受信用スレッド
    recv_thread.start()                                # スレッド開始

# --- メイン処理 ---
def main():                                           # メインエントリポイント
    connect_to_blackboard()                          # BlackBoardへ接続

    log_color_writer, log_depth_writer = initialize_video_logging()  # ログ用VideoWriterを初期化

    print("RealSense カメラを起動中...")
    try:
        pipeline.start(config)                       # RealSenseパイプライン開始
        print("RealSense カメラが起動しました。")
    except Exception as e:
        print("RealSense カメラの起動に失敗しました:", e)  # 起動失敗時のエラー表示
        return

    try:
        with mp_hands.Hands(                        # MediaPipe Handsを初期化
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            max_num_hands=2) as hands:

            while True:                             # メインループ開始
                try:
                    frames = safe_wait_for_frames(pipeline)  # フレーム取得
                except RuntimeError as e:
                    print("[エラー]", e)
                    break

                color_frame = frames.get_color_frame()      # カラーフレーム取得
                depth_frame = frames.get_depth_frame()      # 深度フレーム取得
                if not color_frame or not depth_frame:      # フレーム有効性確認
                    continue

                image = np.asanyarray(color_frame.get_data())       # カラーフレームをNumPy配列へ
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # RGBへ変換
                depth_image = np.asanyarray(depth_frame.get_data()) # 深度フレームをNumPy配列へ
                depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)  # 深度カラー化

                image_rgb.flags.writeable = False                   # 処理速度向上のため書き込み禁止に
                results = hands.process(image_rgb)                  # 手の検出
                image.flags.writeable = True                        # 書き込みを再び許可

                min_avg_depth = None                                # 最小平均深度格納用

                if results.multi_hand_landmarks:                    # 手を検出した場合
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(                  # 手のランドマークを描画
                            image,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style())

                        depth_values = []                           # 各ランドマーク位置の深度を格納
                        h, w, _ = image.shape                       # 画像サイズ取得
                        for lm in hand_landmarks.landmark:
                            cx, cy = int(lm.x * w), int(lm.y * h)   # ピクセル座標に変換
                            if 0 <= cx < w and 0 <= cy < h:
                                d = depth_image[cy, cx]             # 深度値取得
                                if d > 0:
                                    depth_values.append(d)

                        if depth_values:                            # 深度値が有効なら
                            avg_depth = np.mean(depth_values)       # 平均深度計算
                            if min_avg_depth is None or avg_depth < min_avg_depth:  # 最小平均深度更新
                                min_avg_depth = avg_depth

                            text = f"Avg. Depth: {avg_depth:.1f}mm"  # 表示用テキスト作成
                            cx = int(np.mean([lm.x for lm in hand_landmarks.landmark]) * w)  # 手中心X
                            cy = int(np.mean([lm.y for lm in hand_landmarks.landmark]) * h)  # 手中心Y
                            cv2.putText(image, text, (cx - 70, cy - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                        else:
                            cv2.putText(image, "Avg. Depth: N/A", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

                if min_avg_depth is not None:                       # 最小平均深度が計算できたら
                    try:
                        message = f"BM;Depth:{min_avg_depth:.1f}"   # BM宛に深度値を送信
                        s.sendall(message.encode())
                        print(f"[送信] {message}")
                    except Exception as e:
                        print(f"[送信エラー] {e}")

                # --- ここで映像ログ保存を行う ---
                if SAVE_VIDEO_LOGS:                                # 設定ONなら
                    log_color_writer.write(image)                      # カラー映像保存
                    log_depth_writer.write(depth_colormap)             # 深度映像保存

                cv2.imshow('RealSense D415 with MediaPipe Hands (Color)', image)         # カラー映像表示
                cv2.imshow('RealSense D415 Depth', depth_colormap)                      # 深度映像表示

                if cv2.waitKey(5) & 0xFF == 27:  # ESCキー押下時
                    break

    finally:
        print("RealSense カメラを停止中...")
        pipeline.stop()                         # RealSenseパイプライン停止
        print("RealSense カメラが停止しました。")
        cv2.destroyAllWindows()                 # 全OpenCVウィンドウを閉じる
        if s:
            s.close()                           # BlackBoard接続を閉じる
            print("[切断] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":                     # スクリプトが直接実行されたときのみ
    main()                                     # メイン処理開始
