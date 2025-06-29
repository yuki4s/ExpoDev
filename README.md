# EXPO開発

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

4. 依存パッケージをインストール（`requirements.txt`からまとめてインストール）
   ```
   pip install -r requirements.txt
   ```

5. RealSenseカメラを接続    
   ケーブルや端子の相性があるので、カメラ認識が安定しない場合はUSBポートやケーブルを変えて試してみる。

6. Arduino を接続    


## 開発者用
1. 上記のセットアップを終わらせる

2. [Arduino IDE](https://www.arduino.cc/en/software/) をインストール    
   - Arduino 用のスクリプトをコンパイルする（Arduino に書き込む）歳は、Arduino 側面の白いスイッチを電源ボタン側にセットした状態でUSBケーブルで接続する。    
   - 実行する際は、スイッチを逆側にセットする。


# 注意事項
- 仮想環境やPythonキャッシュは`.gitignore`で管理対象外に設定されている。
- プロジェクトは Conventional Commits および Git Flow ルールに従って管理されている。