# Expo開発

RealSenseカメラとMediapipeを組み合わせたビジョン処理システム

## セットアップ手順

Windows 11 + PowerShell 環境で以下の手順を実行

1. このリポジトリをクローン
   ```
   git clone https://github.com/yuki4s/Expo.git
   cd Expo
   ```

2. 仮想環境を作成
   ```
   python -m venv VE
   ```

3. PowerShellの実行ポリシーを一時的に変更して仮想環境を有効化
   ```
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   .\VE\Scripts\activate
   ```

4. 依存パッケージをインストール（requirements.txtからまとめてインストール）
   ```
   pip install -r requirements.txt
   ```

5. RealSenseカメラを接続    
   ケーブルや端子の相性があるので、カメラ認識が安定しない場合はUSBポートやケーブルを変えて試してみる。


# 注意事項
- 仮想環境やPythonキャッシュは.gitignoreで管理対象外に設定されている。
- プロジェクトは Conventional Commits および Git Flow ルールに従って管理されている。