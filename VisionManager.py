# import socket
# import threading
# import pyrealsense2 as rs
# import mediapipe as mp
# import cv2
# import numpy as np
# import time

# # --- BlackBoard通信設定 ---
# HOST = 'localhost'
# PORT = 9000
# CLIENT_NAME = 'VM'
# s = None

# # --- MediaPipe ハンドモジュールの初期化 ---
# mp_hands = mp.solutions.hands
# mp_drawing = mp.solutions.drawing_utils
# mp_drawing_styles = mp.solutions.drawing_styles

# # --- RealSense パイプラインの初期化 ---
# pipeline = rs.pipeline()
# config = rs.config()
# config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
# config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

# # --- フレーム取得関数 ---
# def safe_wait_for_frames(pipeline, max_retries=5):
#     for i in range(max_retries):
#         try:
#             return pipeline.wait_for_frames()
#         except RuntimeError as e:
#             print(f"[警告] フレームの取得に失敗（{i+1}/{max_retries}）: {e}")
#             time.sleep(0.5)
#     raise RuntimeError("フレーム取得に連続で失敗しました。")

# # --- BlackBoardからのコマンド受信用スレッド ---
# def receive_from_blackboard():
#     global s
#     while True:
#         try:
#             msg = s.recv(1024).decode()
#             if msg:
#                 print(f"[BlackBoard→VM] {msg}")
#         except Exception:
#             break

# # --- ソケット接続処理 ---
# def connect_to_blackboard():
#     global s
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.connect((HOST, PORT))

#     local_ip, local_port = s.getsockname()
#     init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"
#     s.sendall(init_msg.encode())

#     print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")

#     recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)
#     recv_thread.start()

# # --- メイン処理 ---
# def main():
#     connect_to_blackboard()

#     print("RealSense カメラを起動中...")
#     try:
#         pipeline.start(config)
#         print("RealSense カメラが起動しました。")
#     except Exception as e:
#         print("RealSense カメラの起動に失敗しました:", e)
#         return

#     try:
#         with mp_hands.Hands(
#             model_complexity=1,
#             min_detection_confidence=0.5,
#             min_tracking_confidence=0.5,
#             max_num_hands=2) as hands:

#             while True:
#                 try:
#                     frames = safe_wait_for_frames(pipeline)
#                 except RuntimeError as e:
#                     print("[エラー]", e)
#                     break

#                 color_frame = frames.get_color_frame()
#                 depth_frame = frames.get_depth_frame()
#                 if not color_frame or not depth_frame:
#                     continue

#                 image = np.asanyarray(color_frame.get_data())
#                 image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
#                 depth_image = np.asanyarray(depth_frame.get_data())
#                 depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

#                 image_rgb.flags.writeable = False
#                 results = hands.process(image_rgb)
#                 image.flags.writeable = True

#                 min_avg_depth = None

#                 if results.multi_hand_landmarks:
#                     for hand_landmarks in results.multi_hand_landmarks:
#                         mp_drawing.draw_landmarks(
#                             image,
#                             hand_landmarks,
#                             mp_hands.HAND_CONNECTIONS,
#                             mp_drawing_styles.get_default_hand_landmarks_style(),
#                             mp_drawing_styles.get_default_hand_connections_style())

#                         depth_values = []
#                         h, w, _ = image.shape
#                         for lm in hand_landmarks.landmark:
#                             cx, cy = int(lm.x * w), int(lm.y * h)
#                             if 0 <= cx < w and 0 <= cy < h:
#                                 d = depth_image[cy, cx]
#                                 if d > 0:
#                                     depth_values.append(d)

#                         if depth_values:
#                             avg_depth = np.mean(depth_values)
#                             if min_avg_depth is None or avg_depth < min_avg_depth:
#                                 min_avg_depth = avg_depth

#                             text = f"Avg. Depth: {avg_depth:.1f}mm"
#                             cx = int(np.mean([lm.x for lm in hand_landmarks.landmark]) * w)
#                             cy = int(np.mean([lm.y for lm in hand_landmarks.landmark]) * h)
#                             cv2.putText(image, text, (cx - 70, cy - 50),
#                                         cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
#                         else:
#                             cv2.putText(image, "Avg. Depth: N/A", (50, 50),
#                                         cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

#                 if min_avg_depth is not None:
#                     try:
#                         message = f"BM;Depth:{min_avg_depth:.1f}"
#                         s.sendall(message.encode())
#                         print(f"[送信] {message}")
#                     except Exception as e:
#                         print(f"[送信エラー] {e}")

#                 cv2.imshow('RealSense D415 with MediaPipe Hands (Color)', image)
#                 cv2.imshow('RealSense D415 Depth', depth_colormap)

#                 if cv2.waitKey(5) & 0xFF == 27:  # ESCキー
#                     break

#     finally:
#         print("RealSense カメラを停止中...")
#         pipeline.stop()
#         print("RealSense カメラが停止しました。")
#         cv2.destroyAllWindows()
#         if s:
#             s.close()
#             print("[切断] BlackBoardとの接続を閉じました。")

# if __name__ == "__main__":
#     main()


import socket
import threading
import pyrealsense2 as rs
import mediapipe as mp
import cv2
import numpy as np
import time

# --- BlackBoard通信設定 ---
HOST = 'localhost'
PORT = 9000
CLIENT_NAME = 'VM'
s = None

# --- MediaPipe ハンドモジュールの初期化 ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# --- RealSense パイプラインの初期化 ---
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

# --- フレーム取得関数 ---
def safe_wait_for_frames(pipeline, max_retries=5):
    for i in range(max_retries):
        try:
            return pipeline.wait_for_frames()
        except RuntimeError as e:
            print(f"[警告] フレームの取得に失敗（{i+1}/{max_retries}）: {e}")
            time.sleep(0.5)
    raise RuntimeError("フレーム取得に連続で失敗しました。")

# --- BlackBoardからのコマンド受信用スレッド ---
def receive_from_blackboard():
    global s
    while True:
        try:
            msg = s.recv(1024).decode()
            if msg:
                print(f"[BlackBoard→VM] {msg}")
        except Exception:
            break

# --- ソケット接続処理 ---
def connect_to_blackboard():
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))

    local_ip, local_port = s.getsockname()
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"
    s.sendall(init_msg.encode())

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)
    recv_thread.start()

# --- メイン処理 ---
def main():
    connect_to_blackboard()

    print("RealSense カメラを起動中...")
    try:
        pipeline.start(config)
        print("RealSense カメラが起動しました。")
    except Exception as e:
        print("RealSense カメラの起動に失敗しました:", e)
        return

    try:
        with mp_hands.Hands(
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            max_num_hands=2
        ) as hands:

            while True:
                try:
                    frames = safe_wait_for_frames(pipeline)
                except RuntimeError as e:
                    print("[エラー]", e)
                    break

                color_frame = frames.get_color_frame()
                depth_frame = frames.get_depth_frame()
                if not color_frame or not depth_frame:
                    continue

                image = np.asanyarray(color_frame.get_data())
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                depth_image = np.asanyarray(depth_frame.get_data())
                depth_colormap = cv2.applyColorMap(
                    cv2.convertScaleAbs(depth_image, alpha=0.03),
                    cv2.COLORMAP_JET
                )

                image_rgb.flags.writeable = False
                results = hands.process(image_rgb)
                image.flags.writeable = True

                # フレーム内の最小深度を保持する変数
                min_depth = None

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        # ランドマークを描画
                        mp_drawing.draw_landmarks(
                            image,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style()
                        )

                        # 各ランドマークの深度を収集
                        depth_values = []
                        h, w, _ = image.shape
                        for lm in hand_landmarks.landmark:
                            cx, cy = int(lm.x * w), int(lm.y * h)
                            if 0 <= cx < w and 0 <= cy < h:
                                d = depth_image[cy, cx]
                                if d > 0:
                                    depth_values.append(d)

                        if depth_values:
                            # この手のランドマークの最小深度を計算
                            local_min_depth = float(np.min(depth_values))
                            # フレーム内での最小値を更新
                            if min_depth is None or local_min_depth < min_depth:
                                min_depth = local_min_depth

                            # 画面表示用テキスト
                            text = f"Min. Depth: {local_min_depth:.1f}mm"
                            cx = int(np.mean([lm.x for lm in hand_landmarks.landmark]) * w)
                            cy = int(np.mean([lm.y for lm in hand_landmarks.landmark]) * h)
                            cv2.putText(
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
                            cv2.putText(
                                image,
                                "Min. Depth: N/A",
                                (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (0, 0, 255),
                                2,
                                cv2.LINE_AA
                            )

                # 最小深度を BlackBoard に送信
                if min_depth is not None:
                    try:
                        message = f"BM;Depth:{min_depth:.1f}\n"
                        s.sendall(message.encode())
                        print(f"[送信] {message}")
                    except Exception as e:
                        print(f"[送信エラー] {e}")

                # 画面表示
                cv2.imshow('RealSense D415 with MediaPipe Hands (Color)', image)
                cv2.imshow('RealSense D415 Depth', depth_colormap)

                # ESCキーでループ終了
                if cv2.waitKey(5) & 0xFF == 27:
                    break

    finally:
        print("RealSense カメラを停止中...")
        pipeline.stop()
        print("RealSense カメラが停止しました。")
        cv2.destroyAllWindows()
        if s:
            s.close()
            print("[切断] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":
    main()
