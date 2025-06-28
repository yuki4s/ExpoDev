# Expo開発ログ

RealSenseカメラとMediapipeを組み合わせたビジョン処理システム

## 環境構築

Windows 11 + PowerShell 環境で以下の手順を実行

1. 作業ディレクトリを作成
   ```powershell
   mkdir Expo
   cd Expo

2. 仮想環境を作成
   ```powershell
   python -m venv VE

3. PowerShellの実行ポリシーを一時的に変更して仮想環境を有効化
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   .\VE\Scripts\activate

4. 必要なパッケージをインストール
   ```powershell
   pip install mediapipe pyrealsense2 opencv-python numpy

5. RealSenseカメラを接続（ケーブルや端子の相性があり、複数試す必要があるかもしれない）

