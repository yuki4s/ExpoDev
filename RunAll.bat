@echo off
:: バッチファイルのあるディレクトリを取得
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

:: BlackBoard.py を新しいウィンドウで起動
start cmd /k "call .\VE\Scripts\activate && python BlackBoard.py"

:: CmdClient.py を新しいウィンドウで起動
start cmd /k "call .\VE\Scripts\activate && python CmdClient.py"

:: VisionManager.py を新しいウィンドウで起動
start cmd /k "call .\VE\Scripts\activate && python VisionManager.py"

:: BehaviorManager.py を新しいウィンドウで起動
start cmd /k "call .\VE\Scripts\activate && python BehaviorManager.py"
