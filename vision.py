import pyrealsense2 as rs
import mediapipe as mp
import cv2
import numpy as np
import time

# --- MediaPipe ハンドモジュールの初期化 ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# --- RealSense パイプラインの初期化 ---
pipeline = rs.pipeline()
config = rs.config()

config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

# パイプラインの開始
print("RealSense カメラを起動中...")
try:
    profile = pipeline.start(config)
    print("RealSense カメラが起動しました。")
except Exception as e:
    print("RealSense カメラの起動に失敗しました:", e)
    exit(1)

# --- フレーム取得関数（タイムアウト対応） ---
def safe_wait_for_frames(pipeline, max_retries=5):
    for i in range(max_retries):
        try:
            return pipeline.wait_for_frames()
        except RuntimeError as e:
            print(f"[警告] フレームの取得に失敗しました（{i+1}/{max_retries} 回目）: {e}")
            time.sleep(0.5)
    raise RuntimeError("フレーム取得に連続で失敗したため、プログラムを終了します。")

try:
    with mp_hands.Hands(
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        max_num_hands=2) as hands:

        while True:
            # フレーム取得
            try:
                frames = safe_wait_for_frames(pipeline)
            except RuntimeError as e:
                print("[エラー]", e)
                break

            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()

            if not color_frame or not depth_frame:
                print("[警告] 有効なカラーフレームまたは深度フレームが得られませんでした。")
                continue

            image = np.asanyarray(color_frame.get_data())
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            depth_image = np.asanyarray(depth_frame.get_data())
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

            image_rgb.flags.writeable = False
            results = hands.process(image_rgb)
            image.flags.writeable = True

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        image,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style())

                    depth_values = []
                    h, w, _ = image.shape

                    for lm in hand_landmarks.landmark:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        if 0 <= cx < w and 0 <= cy < h:
                            depth_at_landmark = depth_image[cy, cx]
                            if depth_at_landmark > 0:
                                depth_values.append(depth_at_landmark)

                    if depth_values:
                        avg_depth = np.mean(depth_values)
                        text = f"Avg. Depth: {avg_depth:.1f}mm"
                        center_x = int(np.mean([lm.x for lm in hand_landmarks.landmark]) * w)
                        center_y = int(np.mean([lm.y for lm in hand_landmarks.landmark]) * h)
                        cv2.putText(image, text, (center_x - 70, center_y - 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                    else:
                        cv2.putText(image, "Avg. Depth: N/A", (50, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

            cv2.imshow('RealSense D415 with MediaPipe Hands (Color)', image)
            cv2.imshow('RealSense D415 Depth', depth_colormap)

            if cv2.waitKey(5) & 0xFF == 27:  # ESCキーで終了
                break

finally:
    print("RealSense カメラを停止中...")
    pipeline.stop()
    print("RealSense カメラが停止しました。")
    cv2.destroyAllWindows()