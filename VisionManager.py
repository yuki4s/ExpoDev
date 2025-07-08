import socket                              # ソケット通信のための標準ライブラリ
import threading                           # 並列処理用スレッドライブラリ
import pyrealsense2 as rs                  # Intel RealSense SDK用Pythonバインディング
import mediapipe as mp                     # MediaPipeライブラリ（手の検出など）
import cv2                                 # OpenCVライブラリ（画像処理）
import numpy as np                         # NumPyライブラリ（数値計算）
import time                                # 時間制御用標準ライブラリ

# --- BlackBoard通信設定 ---
HOST = 'localhost'                         # 接続先のホスト名（ローカル）
PORT = 9000                                # BlackBoardが待ち受けているポート番号
CLIENT_NAME = 'VM'                         # このクライアントの名前（Vision Manager）
s = None                                   # ソケット接続オブジェクト（後で代入）

# --- MediaPipe ハンドモジュールの初期化 ---
mp_hands = mp.solutions.hands             # Handsモジュールのクラス
mp_drawing = mp.solutions.drawing_utils   # ランドマーク描画ユーティリティ
mp_drawing_styles = mp.solutions.drawing_styles  # 描画スタイル設定

# --- RealSense パイプラインの初期化 ---
pipeline = rs.pipeline()                   # RealSenseのパイプラインオブジェクト作成
config = rs.config()                       # ストリーミング設定オブジェクト作成
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)  # カラーストリーム設定
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)  # 深度ストリーム設定

# --- フレーム取得関数 ---
def safe_wait_for_frames(pipeline, max_retries=5):  # 安全にフレームを取得する関数（リトライ付き）
    for i in range(max_retries):
        try:
            return pipeline.wait_for_frames()       # フレーム取得に成功したら返す
        except RuntimeError as e:
            print(f"[警告] フレームの取得に失敗（{i+1}/{max_retries}）: {e}")  # エラー表示
            time.sleep(0.5)                          # 少し待って再試行
    raise RuntimeError("フレーム取得に連続で失敗しました。")  # 5回失敗したら例外

# --- BlackBoardからのコマンド受信用スレッド ---
def receive_from_blackboard():                      # 受信専用スレッド関数
    global s
    while True:
        try:
            msg = s.recv(1024).decode()             # メッセージを受信してデコード
            if msg:
                print(f"[BlackBoard→VM] {msg}")     # メッセージ内容を表示
        except Exception:
            break                                   # エラー発生時はループを抜ける

# --- ソケット接続処理 ---
def connect_to_blackboard():                        # BlackBoardに接続する関数
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # ソケット作成
    s.connect((HOST, PORT))                          # 指定ホストとポートに接続

    local_ip, local_port = s.getsockname()           # 自分のIPとポートを取得
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"  # 初期接続メッセージ作成
    s.sendall(init_msg.encode())                     # 初期メッセージを送信

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)  # 受信スレッド開始
    recv_thread.start()

# --- メイン処理 ---
def main():
    connect_to_blackboard()                          # BlackBoardとの接続を確立

    print("RealSense カメラを起動中...")
    try:
        pipeline.start(config)                       # RealSenseのストリーム開始
        print("RealSense カメラが起動しました。")
    except Exception as e:
        print("RealSense カメラの起動に失敗しました:", e)
        return

    try:
        with mp_hands.Hands(                          # MediaPipeのHandsモジュールを起動
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            max_num_hands=2
        ) as hands:

            while True:                               # 無限ループで映像処理
                try:
                    frames = safe_wait_for_frames(pipeline)  # フレーム取得（リトライ付き）
                except RuntimeError as e:
                    print("[エラー]", e)
                    break

                color_frame = frames.get_color_frame()       # カラーフレーム取得
                depth_frame = frames.get_depth_frame()       # 深度フレーム取得
                if not color_frame or not depth_frame:
                    continue                                # どちらか欠けていたらスキップ

                image = np.asanyarray(color_frame.get_data())       # カラーフレームをNumPy配列に変換
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # RGB形式に変換
                depth_image = np.asanyarray(depth_frame.get_data()) # 深度フレームもNumPy配列に変換
                depth_colormap = cv2.applyColorMap(                 # 深度マップにカラーマップ適用
                    cv2.convertScaleAbs(depth_image, alpha=0.03),
                    cv2.COLORMAP_JET
                )

                image_rgb.flags.writeable = False                   # MediaPipe処理用に読み取り専用化
                results = hands.process(image_rgb)                 # 手のランドマーク検出
                image.flags.writeable = True                       # 再び書き込み可能に戻す

                min_depth = None                                    # 最小深度初期化

                if results.multi_hand_landmarks:                   # 検出された手がある場合
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(                 # 手のランドマークを描画
                            image,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style()
                        )

                        depth_values = []                          # 深度値リスト
                        h, w, _ = image.shape
                        for lm in hand_landmarks.landmark:         # 各ランドマークごとに処理
                            cx, cy = int(lm.x * w), int(lm.y * h)  # 画像上のピクセル座標に変換
                            if 0 <= cx < w and 0 <= cy < h:
                                d = depth_image[cy, cx]            # 深度値を取得
                                if d > 0:
                                    depth_values.append(d)

                        if depth_values:
                            local_min_depth = float(np.min(depth_values))  # 最小深度を計算
                            if min_depth is None or local_min_depth < min_depth:
                                min_depth = local_min_depth        # フレーム全体の最小深度を更新

                            text = f"Min. Depth: {local_min_depth:.1f}mm"  # 表示テキスト作成
                            cx = int(np.mean([lm.x for lm in hand_landmarks.landmark]) * w)
                            cy = int(np.mean([lm.y for lm in hand_landmarks.landmark]) * h)
                            cv2.putText(                          # 最小深度を画面に表示
                                image,
                                text,
                                (cx - 70, cy - 50),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (0, 255, 0),
                                2,
                                cv2.LINE_AA
                            )
                        else:
                            cv2.putText(                          # 深度取得失敗時の表示
                                image,
                                "Min. Depth: N/A",
                                (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (0, 0, 255),
                                2,
                                cv2.LINE_AA
                            )

                if min_depth is not None:
                    try:
                        message = f"BM;Depth:{min_depth:.1f}\n"   # 最小深度をBlackBoard形式に整形
                        s.sendall(message.encode())               # メッセージをBlackBoardに送信
                        print(f"[送信] {message}")
                    except Exception as e:
                        print(f"[送信エラー] {e}")               # エラー時に表示

                cv2.imshow('RealSense D415 with MediaPipe Hands (Color)', image)      # カラー画像表示
                cv2.imshow('RealSense D415 Depth', depth_colormap)                    # 深度画像表示

                if cv2.waitKey(5) & 0xFF == 27:     # ESCキーで終了
                    break

    finally:
        print("RealSense カメラを停止中...")
        pipeline.stop()                            # RealSenseのストリーム停止
        print("RealSense カメラが停止しました。")
        cv2.destroyAllWindows()                    # すべてのウィンドウを閉じる
        if s:
            s.close()                              # ソケットをクローズ
            print("[切断] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":                         # このファイルが直接実行された場合
    main()                                         # メイン関数を呼び出す