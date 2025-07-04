# EXPO開発

RGBDカメラ([Intel Realsense D435](https://www.intelrealsense.com/depth-camera-d435/))と[Arduino UNO R4 Minima](https://docs.arduino.cc/hardware/uno-r4-minima/)を組み合わせたビジョン処理システム

## セットアップ手順

Windows 11 + PowerShell 環境で以下の手順を実行

1. このリポジトリをクローン.    
   ※ `Git`をインストールしていない場合は`ZIP`でダウンロードして解凍してください。
   ```
   git clone https://github.com/yuki4s/Expo.git
   cd クローン先ディレクトリ/Expo
   ```    

2. 仮想環境を作成.
   ```
   python -m venv VE
   ```

3. PowerShellの実行ポリシーを一時的に変更して仮想環境を有効化.
   ```
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   .\VE\Scripts\activate
   ```

4. 依存パッケージをインストール（`requirements.txt`からまとめてインストール）.
   ```
   pip install -r requirements.txt
   ```

5. RealSenseカメラを接続.    
   ケーブルや端子の相性があるので、カメラ認識が安定しない場合はUSBポートやケーブルを変えて試してみる.

6. Arduino を接続.    

7. `RunAll.bat`で一括して動作させることができる.


## 開発者用
1. 上記のセットアップを終わらせる.

2. [Arduino IDE](https://www.arduino.cc/en/software/) をインストール.    
   - Arduino 用のスクリプトをコンパイルする（Arduino に書き込む）歳は、Arduino 側面の白いスイッチを電源ボタン側にセットした状態でUSBケーブルで接続する.    
   - 実行する際は、スイッチを逆側にセットする.


# 補足事項
- `logging_config.json`で各種ログデータを保存するかどうかを設定できる. ログデータは`Log`フォルダ内に保存される.    
- 仮想環境や実行時のログデータやキャッシュデータなどは`.gitignore`で管理対象外に設定されている.    
- プロジェクトは Conventional Commits および Git Flow ルールに従って管理されている.