# EXPO開発

RGBDカメラ([Intel Realsense D435](https://www.intelrealsense.com/depth-camera-d435/))と[Arduino UNO R4 Minima](https://docs.arduino.cc/hardware/uno-r4-minima/)を組み合わせたビジョン処理システム

## 環境構築
`Git`はインストール済みの前提で説明する。
参考として僕の環境は    
- `Windows 11`
- `Python3.11.9`

1. [`Python3.11.9`](https://www.python.org/downloads/release/python-3119/)をインストール。    
   インストーラをダウンロードして実行。    
   インストールの際、"Add Python 3.x to PATH" にチェックを入れるのを忘れずに。

2. このリポジトリをクローンする。    
   ※ `Git`をインストールしていない場合は`ZIP`でダウンロードして解凍してください。    
   
   エクスプローラでセットアップしたいディレクトリに移動し、「右クリック」→「ターミナルで開く」    
   以下を実行してクローンし、`ExpoDev`に移動する。
   ```
   git clone https://github.com/yuki4s/ExpoDev.git
   cd クローン先ディレクトリ/ExpoDev
   ```    

3. 仮想環境の作成。    
   以下で`Python`のバージョンを確認。`Python 3.11.9` と表示されればおけ。
   ```
   python --version
   ```
   以下を実行して、仮想環境を構築。これにより、以降仮想環境で実行する際は、`Python 3.11.9`で実行される。

   ```
   python -m venv VE
   ```

4. PowerShellの実行ポリシーを一時的に変更して仮想環境を有効化。
   ```
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   .\VE\Scripts\activate
   ```

5. 依存パッケージをインストール（`requirements.txt`からまとめてインストールされる）。
   ```
   pip install -r requirements.txt
   ```

6. これで環境構築は完了。    
   

## ログ設定と実行方法
1. ログの設定。
   `logging_config.json`で各種ログデータを保存するかどうかを設定する。初期値は`True`だが、設定変更等で記述漏れになった際は`False`として処理される。    
   ログデータは`Log`フォルダ内に保存される。   
   - `"save_video_logs"`: RGB映像と深度映像    
   - `"save_handLandmark_logs"`: 手のランドマークの座標と深度    
   - `"save_blackboard_logs"`: クライアントとの通信に関連するイベントログ    

2. RealSenseカメラを接続。    
   ケーブルや端子の相性があるので、カメラ認識が安定しない場合はUSBポートやケーブルを変えて試してみる。

2. Arduino を接続。    

3. 実行。    
   `RunAll.bat`で一括して動作させることができる。終了する際は GUI で「Exit All」を選択し、確認画面で「はい」を押すと自動で終了する。


## 開発者用
1. 上記のセットアップを終わらせる。

2. [Arduino IDE](https://www.arduino.cc/en/software/) をインストール。    
   - Arduino 用のスクリプトをコンパイルする（Arduino に書き込む）歳は、Arduino 側面の白いスイッチを電源ボタン側にセットした状態でUSBケーブルで接続する。    
   - 実行する際は、スイッチを逆側にセットする。


# 補足事項
- `logging_config.json`で各種ログデータを保存するかどうかを設定できる。ログデータは`Log`フォルダ内に保存される。    
- 仮想環境や実行時のログデータやキャッシュデータなどは`.gitignore`で管理対象外に設定されている。    
- プロジェクトは Conventional Commits および Git Flow ルールに従って管理されている。