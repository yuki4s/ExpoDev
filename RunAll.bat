@echo off
:: バッチファイルのあるディレクトリを取得
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

:: /c は終了後自動的にcmdウインドウが閉じる
:: /k は終了後もcmdウィンドウは開いたまま

:: BlackBoard.py を新しいウィンドウで起動
start cmd /c "call .\VE\Scripts\activate && python BlackBoard.py"

:: CmdClient.py を新しいウィンドウで起動
start cmd /c "call .\VE\Scripts\activate && python CmdClient.py"

:: VisionManager.py を新しいウィンドウで起動
start cmd /c "call .\VE\Scripts\activate && python VisionManager.py"

:: BehaviorManager.py を新しいウィンドウで起動
start cmd /c "call .\VE\Scripts\activate && python BehaviorManager.py"
