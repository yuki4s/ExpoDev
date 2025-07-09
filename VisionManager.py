import socket  # BlackBoardとの通信に用いるソケット通信モジュール
import threading  # 通信を非同期で処理するためのスレッド制御モジュール
import pyrealsense2 as rs  # RealSenseカメラ制御用のライブラリ
import mediapipe as mp  # 手の検出・追跡に用いるMediaPipeライブラリ
import cv2  # 画像処理および表示に用いるOpenCVライブラリ
import numpy as np  # 配列や数値計算を扱うNumPyライブラリ
import time  # 時間待ち処理などに使用

# --- BlackBoard通信設定 ---
HOST = 'localhost'  # BlackBoardのホスト名（ローカル）
PORT = 9000  # BlackBoardのポート番号
CLIENT_NAME = 'VM'  # このクライアント（VisionManager）の名前
s = None  # ソケットオブジェクトを格納する変数（後で初期化）

# --- MediaPipe ハンドモジュールの初期化 ---
mp_hands = mp.solutions.hands  # 手検出用モジュール
mp_drawing = mp.solutions.drawing_utils  # ランドマーク描画ユーティリティ
mp_drawing_styles = mp.solutions.drawing_styles  # 描画スタイル設定

# --- RealSense パイプラインの初期化 ---
pipeline = rs.pipeline()  # RealSenseのデータ取得用パイプラインを作成
config = rs.config()  # ストリーム設定オブジェクトを作成
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)  # カラーストリーム設定（解像度・fps）
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)  # 深度ストリーム設定（解像度・fps）

# --- フレーム取得関数 ---
def safe_wait_for_frames(pipeline, max_retries=5):  # フレーム取得を試みる関数（最大5回までリトライ）
    for i in range(max_retries):
        try:
            return pipeline.wait_for_frames()  # フレーム取得に成功したら返す
        except RuntimeError as e:
            print(f"[警告] フレームの取得に失敗（{i+1}/{max_retries}）: {e}")  # 失敗時に警告を表示
            time.sleep(0.5)  # 少し待ってリトライ
    raise RuntimeError("フレーム取得に連続で失敗しました。")  # 最大リトライ回数を超えたら例外を送出

# --- BlackBoardからのコマンド受信用スレッド ---
def receive_from_blackboard():  # 非同期でBlackBoardからの受信を行う関数
    global s
    while True:
        try:
            msg = s.recv(1024).decode()  # ソケットからのメッセージ受信
            if msg:
                print(f"[BlackBoard→VM] {msg}")  # コンソールに出力
        except Exception:
            break  # 受信エラーが起きたらスレッド終了

# --- ソケット接続処理 ---
def connect_to_blackboard():  # BlackBoardへの接続処理
    global s
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCPソケットを作成
    s.connect((HOST, PORT))  # 指定ホスト・ポートに接続

    local_ip, local_port = s.getsockname()  # 自分のIPとポートを取得
    init_msg = f"{CLIENT_NAME};{local_ip}:{local_port}"  # 初期化メッセージを生成
    s.sendall(init_msg.encode())  # 初期化メッセージを送信

    print(f"[接続] BlackBoardに '{CLIENT_NAME}'（{local_ip}:{local_port}）として接続済み")

    recv_thread = threading.Thread(target=receive_from_blackboard, daemon=True)  # 受信スレッドを生成（デーモンモード）
    recv_thread.start()  # スレッドを開始

# --- メイン処理 ---
def main():
    connect_to_blackboard()  # BlackBoardに接続

    print("RealSense カメラを起動中...")
    try:
        pipeline.start(config)  # RealSenseストリームを開始
        print("RealSense カメラが起動しました。")
    except Exception as e:
        print("RealSense カメラの起動に失敗しました:", e)  # 起動失敗時はエラー表示して終了
        return

    try:
        with mp_hands.Hands(  # MediaPipeの手検出インスタンスを初期化
            model_complexity=1,  # モデルの複雑度（高）
            min_detection_confidence=0.5,  # 手検出の信頼度閾値
            min_tracking_confidence=0.5,  # 追跡の信頼度閾値
            max_num_hands=2  # 検出する手の最大数
        ) as hands:

            while True:  # メインループ
                try:
                    frames = safe_wait_for_frames(pipeline)  # カメラからフレームを取得
                except RuntimeError as e:
                    print("[エラー]", e)
                    break  # 取得に失敗したらループを抜ける

                color_frame = frames.get_color_frame()  # カラーフレーム取得
                depth_frame = frames.get_depth_frame()  # 深度フレーム取得
                if not color_frame or not depth_frame:
                    continue  # どちらかが欠けていればスキップ

                image = np.asanyarray(color_frame.get_data())  # カラー画像をnumpy配列に変換
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # RGBに変換（MediaPipe用）
                depth_image = np.asanyarray(depth_frame.get_data())  # 深度画像をnumpy配列に変換
                depth_colormap = cv2.applyColorMap(  # 深度画像をカラーマップで可視化
                    cv2.convertScaleAbs(depth_image, alpha=0.03),
                    cv2.COLORMAP_JET
                )

                image_rgb.flags.writeable = False  # MediaPipe処理中は書き込み禁止に設定
                results = hands.process(image_rgb)  # 手検出・ランドマーク推定
                image.flags.writeable = True  # 書き込み可能に戻す

                min_depth = None  # フレーム全体での最小深度を初期化

                if results.multi_hand_landmarks:  # 手が検出された場合
                    for hand_landmarks in results.multi_hand_landmarks:  # 各手について
                        mp_drawing.draw_landmarks(  # ランドマークと接続線を描画
                            image,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            mp_drawing_styles.get_default_hand_landmarks_style(),
                            mp_drawing_styles.get_default_hand_connections_style()
                        )

                        depth_values = []  # 各ランドマークの深度値を保存
                        h, w, _ = image.shape  # 画像のサイズを取得
                        for lm in hand_landmarks.landmark:  # 各ランドマークについて
                            cx, cy = int(lm.x * w), int(lm.y * h)  # ピクセル座標に変換
                            if 0 <= cx < w and 0 <= cy < h:  # 範囲内か確認
                                d = depth_image[cy, cx]  # 対応する深度値を取得
                                if d > 0:
                                    depth_values.append(d)  # 有効な値のみ追加

                        if depth_values:
                            local_min_depth = float(np.min(depth_values))  # この手における最小深度
                            if min_depth is None or local_min_depth < min_depth:
                                min_depth = local_min_depth  # フレーム全体の最小深度を更新

                            text = f"Min. Depth: {local_min_depth:.1f}mm"  # 表示用の深度テキスト
                            cx = int(np.mean([lm.x for lm in hand_landmarks.landmark]) * w)
                            cy = int(np.mean([lm.y for lm in hand_landmarks.landmark]) * h)
                            cv2.putText(  # 深度を画像に表示
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
                            cv2.putText(  # 深度が取得できなかった場合
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
                        message = f"BM;Depth:{min_depth:.1f}\n"  # 最小深度をBlackBoardに送信
                        s.sendall(message.encode())
                        print(f"[送信] {message}")
                    except Exception as e:
                        print(f"[送信エラー] {e}")  # 通信失敗時の表示

                # 表示ウィンドウ
                cv2.imshow('RealSense D415 with MediaPipe Hands (Color)', image)  # カラー画像
                cv2.imshow('RealSense D415 Depth', depth_colormap)  # 深度画像（カラーマップ）

                if cv2.waitKey(5) & 0xFF == 27:  # ESCキーでループ終了
                    break

    finally:
        print("RealSense カメラを停止中...")
        pipeline.stop()  # RealSenseストリームを停止
        print("RealSense カメラが停止しました。")
        cv2.destroyAllWindows()  # OpenCVのウィンドウを閉じる
        if s:
            s.close()  # ソケットを閉じる
            print("[切断] BlackBoardとの接続を閉じました。")

if __name__ == "__main__":
    main()  # スクリプトが直接実行されたときのみ main() を呼び出す
