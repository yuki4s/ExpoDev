import pyrealsense2 as rs                 # RealSense SDKのPythonラッパーをインポート
import mediapipe as mp                    # MediaPipeライブラリをインポート
import cv2                                # OpenCVライブラリをインポート
import numpy as np                        # NumPyライブラリをインポート
import time                               # 時間操作用の標準ライブラリをインポート

# --- MediaPipe ハンドモジュールの初期化 ---
mp_hands = mp.solutions.hands             # MediaPipe Handsソリューション
mp_drawing = mp.solutions.drawing_utils   # 描画ユーティリティ
mp_drawing_styles = mp.solutions.drawing_styles  # 描画スタイル

# --- RealSense パイプラインの初期化 ---
pipeline = rs.pipeline()                  # RealSenseパイプラインオブジェクトを作成
config = rs.config()                      # パイプライン設定オブジェクトを作成

config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)    # カラーストリームを設定
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)     # 深度ストリームを設定

# パイプラインの開始
print("RealSense カメラを起動中...")
try:
    profile = pipeline.start(config)      # 設定を使ってパイプラインを開始
    print("RealSense カメラが起動しました。")
except Exception as e:
    print("RealSense カメラの起動に失敗しました:", e)  # エラー処理
    exit(1)

# --- フレーム取得関数（タイムアウト対応） ---
def safe_wait_for_frames(pipeline, max_retries=5):  # フレーム取得をリトライする関数
    for i in range(max_retries):
        try:
            return pipeline.wait_for_frames()       # フレーム取得を試行
        except RuntimeError as e:
            print(f"[警告] フレームの取得に失敗しました（{i+1}/{max_retries} 回目）: {e}")
            time.sleep(0.5)                         # 失敗時は0.5秒待機
    raise RuntimeError("フレーム取得に連続で失敗したため、プログラムを終了します。")

try:
    with mp_hands.Hands(                           # MediaPipe Handsを初期化
        model_complexity=1,                        # ハンドモデルの複雑度
        min_detection_confidence=0.5,              # 検出信頼度の閾値
        min_tracking_confidence=0.5,               # トラッキング信頼度の閾値
        max_num_hands=2) as hands:                 # 検出する最大手数

        while True:                                # メインループ開始
            # フレーム取得
            try:
                frames = safe_wait_for_frames(pipeline)  # カメラからフレームを取得
            except RuntimeError as e:
                print("[エラー]", e)
                break

            color_frame = frames.get_color_frame()       # カラーフレームを取得
            depth_frame = frames.get_depth_frame()       # 深度フレームを取得

            if not color_frame or not depth_frame:       # フレームが有効でない場合
                print("[警告] 有効なカラーフレームまたは深度フレームが得られませんでした。")
                continue

            image = np.asanyarray(color_frame.get_data())                 # カラーフレームをNumPy配列に変換
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)            # BGRからRGBに変換
            depth_image = np.asanyarray(depth_frame.get_data())           # 深度フレームをNumPy配列に変換
            depth_colormap = cv2.applyColorMap(                           # 深度データをカラー化
                cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

            image_rgb.flags.writeable = False                             # 処理速度向上のためイメージを書き込み不可に設定
            results = hands.process(image_rgb)                            # MediaPipeで手の検出を実行
            image.flags.writeable = True                                  # イメージを再び書き込み可に設定

            if results.multi_hand_landmarks:                              # 検出された手があれば
                for hand_landmarks in results.multi_hand_landmarks:       # 検出された各手について処理
                    mp_drawing.draw_landmarks(                            # カラーフレーム上にランドマークを描画
                        image,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style())

                    depth_values = []                                     # ランドマーク位置の深度値を格納するリスト
                    h, w, _ = image.shape                                 # 画像サイズを取得

                    for lm in hand_landmarks.landmark:                    # 各ランドマークごとに
                        cx, cy = int(lm.x * w), int(lm.y * h)             # 画像座標系に変換
                        if 0 <= cx < w and 0 <= cy < h:                   # 画像範囲内かチェック
                            depth_at_landmark = depth_image[cy, cx]       # 対応する深度を取得
                            if depth_at_landmark > 0:                     # 有効な深度値なら
                                depth_values.append(depth_at_landmark)    # リストに追加

                    if depth_values:                                      # 有効な深度値があれば
                        avg_depth = np.mean(depth_values)                 # 平均深度を計算
                        text = f"Avg. Depth: {avg_depth:.1f}mm"           # 表示用テキスト作成
                        center_x = int(np.mean([lm.x for lm in hand_landmarks.landmark]) * w)  # 手の中心X座標
                        center_y = int(np.mean([lm.y for lm in hand_landmarks.landmark]) * h)  # 手の中心Y座標
                        cv2.putText(image, text, (center_x - 70, center_y - 50),  # 平均深度を描画
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                    else:
                        cv2.putText(image, "Avg. Depth: N/A", (50, 50),   # 深度が取得できない場合の表示
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

            cv2.imshow('RealSense D415 with MediaPipe Hands (Color)', image)        # カラーフレームを表示
            cv2.imshow('RealSense D415 Depth', depth_colormap)                     # 深度フレームを表示

            if cv2.waitKey(5) & 0xFF == 27:  # ESCキーで終了判定
                break

finally:
    print("RealSense カメラを停止中...")
    pipeline.stop()                         # パイプラインを停止
    print("RealSense カメラが停止しました。")
    cv2.destroyAllWindows()                 # OpenCVのウィンドウを閉じる
