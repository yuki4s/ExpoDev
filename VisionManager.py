# VisionManager.py

# 仮想環境の有効化 .\VE\Scripts\activate

running = True  # VisionManager全体の稼働フラグをTrueに設定する

import socket                                    # ソケット通信を行うためのライブラリをインポート
import threading                                 # スレッド処理用のライブラリをインポート
import pyrealsense2 as rs                        # Intel RealSense用Pythonラッパーをインポート
import mediapipe as mp                           # MediaPipeライブラリをインポート
import cv2                                       # OpenCVライブラリをインポート
import numpy as np                               # NumPyライブラリをインポート
import time                                      # 時間操作用標準ライブラリをインポート
import os                                       # OS操作用ライブラリをインポート
import glob                                     # ファイルパスの検索に使用するライブラリをインポート
import re                                       # 正規表現操作用ライブラリをインポート
import json                                     # JSONファイル読み書き用ライブラリをインポート

# --- ログ設定読み込み ---
try:
    with open("logging_config.json", "r", encoding="utf-8") as f:  # ログ設定ファイルを読み込み
        config_data = json.load(f)                                  # JSONデータとして読み込む
    SAVE_VIDEO_LOGS = config_data.get("save_video_logs", False)     # 映像ログ記録設定を取得（無ければFalse）
    SAVE_HANDLANDMARK_LOGS = config_data.get("save_handLandmark_logs", False) # 手ランドマークログ設定を取得（無ければFalse）
    print(f"[設定] SAVE_VIDEO_LOGS={SAVE_VIDEO_LOGS}, SAVE_HANDLANDMARK_LOGS={SAVE_HANDLANDMARK_LOGS}")  # 設定内容を表示
except Exception as e:
    print(f"[設定エラー] logging_config.json の読み込みに失敗しました: {e}")  # 設定読み込み失敗時にエラーメッセージを表示
    SAVE_VIDEO_LOGS = False                                       # 設定失敗時はFalseに設定
    SAVE_HANDLANDMARK_LOGS = False                               # 設定失敗時はFalseに設定

# --- BlackBoard通信設定 ---
HOST = 'localhost'                              # BlackBoardサーバのホストアドレス
PORT = 9000                                     # BlackBoardサーバのポート番号
CLIENT_NAME = 'VM'                              # クライアント名を設定（VisionManagerを意味する）
s = None                                        # ソケット接続オブジェクトの初期化

# --- 解像度・フレームレート設定 ---
#frame_width = 640          # （コメントアウト）横解像度
#frame_height = 480         # （コメントアウト）縦解像度
frame_width = 1280                                # 横解像度を1280ピクセルに設定
frame_height = 720                                # 縦解像度を720ピクセルに設定
frame_rate = 30                                   # フレームレートを30FPSに設定

# --- MediaPipe ハンドモジュールの初期化 ---
mp_hands = mp.solutions.hands                  # MediaPipeの手検出モジュールを初期化
mp_drawing = mp.solutions.drawing_utils       # MediaPipeの描画ユーティリティを初期化
mp_drawing_styles = mp.solutions.drawing_styles  # MediaPipeの描画スタイルを初期化

# --- RealSense パイプラインの初期化 ---
pipeline = rs.pipeline()                      # RealSense用のパイプラインを作成
config = rs.config()                          # RealSense用設定オブジェクトを作成
config.enable_stream(rs.stream.color, frame_width, frame_height, rs.format.bgr8, frame_rate)  # カラーストリーム設定
config.enable_stream(rs.stream.depth, frame_width, frame_height, rs.format.z16, frame_rate)   # 深度ストリーム設定

# --- 映像ログ記録用関数 ---
def initialize_video_logging():
    """
    BlackBoardログ番号に合わせてカラー/深度のビデオログファイルを用意し、
    OpenCVのVideoWriterを返す。
    """
    blackboard_log_dir = "Log/BlackBoardLog"           # BlackBoardログ保存ディレクトリ
    video_log_dir = "Log/VideoLog"                     # 映像ログ保存ディレクトリ

    os.makedirs(blackboard_log_dir, exist_ok=True)     # ログフォルダが存在しない場合は作成
    os.makedirs(video_log_dir, exist_ok=True)          # 映像ログフォルダが存在しない場合は作成

    existing_logs = glob.glob(os.path.join(blackboard_log_dir, "log*_blackBoard.log"))  # 既存BlackBoardログを検索

    max_index = 0                                      # 最大ログ番号の初期値
    for log_file in existing_logs:                     # 既存ログを走査
        match = re.match(r".*log(\d+)_blackBoard\.log$", log_file)  # ログ番号を正規表現で抽出
        if match:
            idx = int(match.group(1))                  # ログ番号を整数に変換
            if idx > max_index:                        # 最大値を更新
                max_index = idx

    log_index = max_index                              # RunAll.bat実行時、先に作成されるBlackBoardログ番号を基準にする
    print(f"[ログ初期化] ログ番号: {log_index}")

    color_video_filename = os.path.join(video_log_dir, f"log{log_index}_colorVideo.mp4")  # カラーログファイル名
    depth_video_filename = os.path.join(video_log_dir, f"log{log_index}_depthVideo.mp4")  # 深度ログファイル名

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')           # MP4形式用のコーデックを取得
    log_color_writer = cv2.VideoWriter(color_video_filename, fourcc, frame_rate, (frame_width, frame_height))  # カラー映像用VideoWriter
    log_depth_writer = cv2.VideoWriter(depth_video_filename, fourcc, frame_rate, (frame_width, frame_height))  # 深度映像用VideoWriter

    return log_color_writer, log_depth_writer          # 生成したVideoWriterを返す

# --- フレームごとの手ランドマークデータ記録関数 ---
frame_logs = []  # フレームごとのランドマークログを蓄積するリスト
def record_frame_data(frame_idx, timestamp, hands_data, processing_time_ms):
    """
    フレームごとの手ランドマーク情報を辞書形式でframe_logsに追加する。
    """
    frame_log = {
        "frame_index": frame_idx,                     # フレーム番号
        "timestamp": timestamp,                       # フレームのタイムスタンプ
        "hands": hands_data                           # 検出された手のデータ
    }
    frame_logs.append(frame_log)                      # ログに追加

# --- ログファイル保存関数 ---
def save_all_frame_logs():
    """
    frame_logsに蓄積した全データをJSONファイルとして保存する。
    ログ形式は最上位に解像度情報、次にフレームごとのデータを格納する。
    """
    if not SAVE_HANDLANDMARK_LOGS or not frame_logs:  # ログ設定が無効またはデータ無しなら終了
        return

    landmark_log_dir = "Log/HandLandmarkLog"          # 手ランドマークログ保存用ディレクトリ
    os.makedirs(landmark_log_dir, exist_ok=True)      # フォルダがなければ作成

    blackboard_log_dir = "Log/BlackBoardLog"          # BlackBoardログディレクトリ
    existing_logs = glob.glob(os.path.join(blackboard_log_dir, "log*_blackBoard.log"))  # ログファイル検索
    max_index = 0
    for log_file in existing_logs:
        match = re.match(r".*log(\d+)_blackBoard\.log$", log_file)  # ログ番号を抽出
        if match:
            idx = int(match.group(1))
            if idx > max_index:
                max_index = idx

    log_index = max_index                             # BlackBoardログ番号に合わせる
    landmark_log_filename = os.path.join(landmark_log_dir, f"log{log_index}_handLandmarks.json")  # 出力ファイル名生成

    logs_to_save = {                                  # ログデータ構造を作成
        "image_resolution": {"width": frame_width, "height": frame_height},  # 解像度情報
        "frames": frame_logs                         # フレームごとのデータ
    }

    try:
        with open(landmark_log_filename, "w", encoding="utf-8") as f:  # JSONファイルを開く
            json.dump(logs_to_save, f, indent=2, ensure_ascii=False)   # データをJSON形式で保存
        print(f"[保存] 手ランドマークログを保存しました: {landmark_log_filename}")
    except Exception as e:
        print(f"[保存エラー] 手ランドマークログ保存中に例外発生: {e}")  # 保存エラー時にメッセージを表示

# --- フレーム取得関数 ---
def safe_wait_for_frames(pipeline, max_retries=5):  # フレーム取得をリトライ付きで行う関数
    for i in range(max_retries):                    # 最大max_retries回までリトライ
        try:
            return pipeline.wait_for_frames()       # フレームを取得
        except RuntimeError as e:                   # 取得に失敗した場合
            print(f"[警告] フレームの取得に失敗（{i+1}/{max_retries}）: {e}")  # 警告を表示
            time.sleep(0.5)                         # 0.5秒待って再試行
    raise RuntimeError("フレーム取得に連続で失敗しました。")  # 最大リトライを超えた場合は例外を送出

# --- BlackBoardからのコマンド受信用スレッド ---
def receive_from_blackboard():                     # BlackBoardからのコマンドを受信するスレッド
    global s, running
    while True:                                    # 無限ループで受信を監視
        try:
            msg = s.recv(1024).decode()            # BlackBoardからデータを受信
            if msg:
                print(f"[BlackBoard→VM] {msg}")   # 受信したメッセージを表示

                if msg.strip() == "EXIT":          # EXITコマンドが届いた場合
                    print("[終了指示] EXITコマンドを受信しました。VisionManagerを終了します。")
                    try:
                        s.sendall(b"ACK;EXIT_RECEIVED")      # EXIT受領確認のACKを送信
                        print("[ACK送信] EXIT受領確認を送信しました。")
                    except Exception as e:
                        print(f"[ACK送信失敗] {e}")          # ACK送信失敗時のエラーメッセージ
                    running = False                          # メインループ終了フラグをFalseに設定
                    break                                    # スレッドループを終了

        except Exception:                                   # ソケットエラー時
            break                                           # スレッドループを終了

# --- ソケット接続処理 ---
def connect_to_blackboard():                      # BlackBoardサーバへ接続する関数
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPソケットを作成
    s.connect((HOST, PORT))                                # BlackBoardに接続

    local_ip, local_port = s.getsockname()                # 自分のIPとポート番号を取得
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"   # 初期メッセージを作成
    s.sendall(init_msg.encode())                          # 初期メッセージを送信

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)  # BlackBoard受信用スレッドを作成
    recv_thread.start()                                # スレッドを開始

# --- フレーム内のすべての手のランドマーク情報を整理する ---
def extract_all_hands_landmarks(results, depth_image, image_shape):
    """
    検出結果から全手の21ランドマーク座標と深度を整理し、
    各手のhand_id, handedness, confidence, landmarks情報を含む辞書リストを返す。
    """
    h, w, _ = image_shape                           # 入力画像の高さ・幅を取得
    all_hands_data = []                            # 全ての手データを格納するリスト

    if results.multi_hand_landmarks and results.multi_handedness:  # ランドマークと左右判定情報がある場合
        for i, (hand_landmarks, handedness) in enumerate(zip(results.multi_hand_landmarks, results.multi_handedness)):  # 各手ごとに処理
            landmarks_list = []                    # この手のランドマーク情報リスト
            depth_values = []                      # 有効な深度値を格納するリスト

            for idx, lm in enumerate(hand_landmarks.landmark):  # 各ランドマークを処理
                cx, cy = int(lm.x * w), int(lm.y * h)           # 正規化座標をピクセル座標に変換
                if 0 <= cx < w and 0 <= cy < h:                 # 画像範囲内の場合
                    d = depth_image[cy, cx]                     # 深度値を取得
                    if d > 0:                                   # 有効な深度なら
                        depth_values.append(d)                  # 有効深度をリストに追加
                    depth_val = float(d)                        # 深度値をfloat型に変換
                else:
                    depth_val = None                           # 範囲外の場合はNone

                landmarks_list.append({                         # ランドマーク情報を辞書にして追加
                    "landmark_id": idx,
                    "pixel_x": cx,
                    "pixel_y": cy,
                    "depth": depth_val
                })

            min_depth = np.min(depth_values) if depth_values else None  # 有効深度があれば最小値を計算

            single_hand_data = {                               # 手情報を辞書にまとめる
                "hand_id": i,
                "handedness": handedness.classification[0].label,
                "hand_confidence": handedness.classification[0].score,
                "min_depth": float(min_depth) if min_depth is not None else None,
                "landmarks": landmarks_list
            }
            all_hands_data.append(single_hand_data)            # 手情報を全体リストに追加

    return all_hands_data, results.multi_hand_landmarks if results.multi_hand_landmarks else []  # 全手情報とランドマークそのものを返す

# --- メイン処理 ---
def main():                                           # メイン関数（プログラムのエントリポイント）
    connect_to_blackboard()                          # BlackBoardに接続し、受信用スレッドを開始する

    start_time = time.time()                         # メイン処理開始時刻を記録する

    log_color_writer, log_depth_writer = initialize_video_logging()  # ログ用のVideoWriterを初期化する

    print("RealSense カメラを起動中...")
    try:
        pipeline.start(config)                       # RealSenseパイプラインを開始する
        print("RealSense カメラが起動しました。")
    except Exception as e:
        print("RealSense カメラの起動に失敗しました:", e)  # カメラ起動失敗時にエラーメッセージを表示
        return

    try:
        with mp_hands.Hands(                        # MediaPipe Handsを初期化
            model_complexity=1,                      # モデルの複雑さ（1:標準）
            min_detection_confidence=0.5,            # 検出の最低信頼度
            min_tracking_confidence=0.5,             # トラッキングの最低信頼度
            max_num_hands=2) as hands:               # 最大検出する手は2つ

            frame_idx = 0                           # フレーム番号の初期化

            while running:                          # runningフラグがTrueの間ループを継続
                try:
                    frames = safe_wait_for_frames(pipeline)  # RealSenseからフレームを取得
                except RuntimeError as e:
                    print("[エラー]", e)            # フレーム取得失敗時のエラーメッセージ
                    break                           # メインループを終了

                color_frame = frames.get_color_frame()       # カラーフレームを取得
                depth_frame = frames.get_depth_frame()       # 深度フレームを取得
                if not color_frame or not depth_frame:       # いずれかのフレームが無効な場合はスキップ
                    continue

                image = np.asanyarray(color_frame.get_data())       # カラーフレームをNumPy配列に変換
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # RGB形式に変換
                depth_image = np.asanyarray(depth_frame.get_data()) # 深度フレームをNumPy配列に変換
                depth_colormap = cv2.applyColorMap(                 # 深度をカラーマップ化
                    cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

                image_rgb.flags.writeable = False                   # 画像を読み取り専用にして処理を高速化
                results = hands.process(image_rgb)                  # MediaPipeで手検出を実行
                image.flags.writeable = True                        # 処理後に書き込み可能に戻す

                # --- ランドマーク抽出と結果取得 ---
                hands_data, multi_hand_landmarks = extract_all_hands_landmarks(results, depth_image, image.shape)

                # --- 検出したすべての手のうち、最も近い手の深度を取得 ---
                min_depths = [hand["min_depth"] for hand in hands_data if hand["min_depth"] is not None]
                min_depth_overall = min(min_depths) if min_depths else None

                # --- 最小深度をBlackBoardに送信 ---
                if min_depth_overall is not None:
                    try:
                        message = f"BM;Depth:{min_depth_overall:.1f}"  # メッセージを作成
                        s.sendall(message.encode())                   # メッセージを送信
                        print(f"[送信] {message}")
                    except Exception as e:
                        print(f"[送信エラー] {e}")                    # 送信失敗時に表示

                # --- 検出した各手のランドマークを描画 ---
                for hand, hand_landmarks in zip(hands_data, multi_hand_landmarks):
                    mp_drawing.draw_landmarks(                        # MediaPipeのランドマークを描画
                        image,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style()
                    )
                    # 手の中心に最小深度をテキストで描画
                    if hand["landmarks"]:
                        lm_points = hand["landmarks"]
                        center_x = int(np.mean([lm["pixel_x"] for lm in lm_points]))
                        center_y = int(np.mean([lm["pixel_y"] for lm in lm_points]))
                        if hand["min_depth"] is not None:
                            text = f"Min Depth: {hand['min_depth']:.1f}mm"
                            cv2.putText(image, text, (center_x - 70, center_y - 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                        else:
                            cv2.putText(image, "Min Depth: N/A", (50, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

                # --- 現在日時を文字列化 ---
                now = time.localtime()
                datetime_text = time.strftime("%Y-%m-%d %H:%M:%S", now)

                # --- カラー映像に日時を右上に描画 ---
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale, color, thickness = 0.5, (255, 255, 255), 1
                (text_width, _), _ = cv2.getTextSize(datetime_text, font, font_scale, thickness)
                cv2.putText(image, datetime_text, (image.shape[1]-text_width-10, 20), font, font_scale, color, thickness, cv2.LINE_AA)

                # --- 深度映像にも日時を右上に描画 ---
                (depth_text_width, _), _ = cv2.getTextSize(datetime_text, font, font_scale, thickness)
                cv2.putText(depth_colormap, datetime_text, (depth_colormap.shape[1]-depth_text_width-10, 20), font, font_scale, color, thickness, cv2.LINE_AA)

                # --- frame番号を描画 ---
                frame_text = f"Frame: {frame_idx}"                                  # 表示用文字列を作成
                (frame_text_width, _), _ = cv2.getTextSize(frame_text, font, font_scale, thickness)  # テキストサイズ取得
                cv2.putText(image, frame_text, (image.shape[1]-frame_text_width-10, 45),  # 右上に表示（日時の少し下）
                            font, font_scale, color, thickness, cv2.LINE_AA)

                # --- 映像ログ保存 ---
                if SAVE_VIDEO_LOGS:
                    log_color_writer.write(image)                      # カラー映像を保存
                    log_depth_writer.write(depth_colormap)             # 深度映像を保存

                # --- 手ランドマークのログ保存 ---
                if SAVE_HANDLANDMARK_LOGS:
                    frame_timestamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())  # ISO形式の時刻文字列
                    elapsed_ms = (time.time() - start_time) * 1000      # 処理開始からの経過時間を計算
                    record_frame_data(frame_idx, frame_timestamp, hands_data, elapsed_ms)  # フレーム情報を記録

                frame_idx += 1  # フレーム番号を更新

                # --- 映像を画面に表示 ---
                cv2.imshow('RealSense D415 with MediaPipe Hands (Color)', image)         # カラー映像を表示
                cv2.imshow('RealSense D415 Depth', depth_colormap)                      # 深度映像を表示

                if cv2.waitKey(5) & 0xFF == 27:  # ESCキーが押されたらループを抜ける
                    break

    finally:
        print("RealSense カメラを停止中...")
        pipeline.stop()                         # RealSenseパイプラインを停止する
        print("RealSense カメラが停止しました。")

        save_all_frame_logs()                   # フレームごとのランドマークデータをJSONに保存する

        cv2.destroyAllWindows()                 # OpenCVのウィンドウを全て閉じる
        if s:
            s.close()                           # BlackBoardへのソケット接続を閉じる
            print("[切断] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":                     # スクリプトが直接実行されたときのみ
    main()                                     # メイン処理を実行する
