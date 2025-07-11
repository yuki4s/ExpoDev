@echo off
:: バッチファイルのあるディレクトリを取得
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

:: /c は終了後自動的にcmdウインドウが閉じる
:: /k は終了後もcmdウィンドウは開いたまま

:: BlackBoard.py を新しいウィンドウで起動
start "BlackBoard" cmd /c "call .\VE\Scripts\activate && python BlackBoard.py"

:: BlackBoardが安定するまで5秒待機
timeout /t 3 /nobreak >nul

:: BehaviorManager.py を新しいウィンドウで起動
start "BehaviorManager" cmd /c "call .\VE\Scripts\activate && python BehaviorManager.py"

:: VisionManager.py を新しいウィンドウで起動
start "VisionManager" cmd /c "call .\VE\Scripts\activate && python VisionManager.py"

:: SoundManager.py を新しいウィンドウで起動
:: start "SoundManager" cmd /c "call .\VE\Scripts\activate && python SoundManager.py"

:: CmdClient.py を新しいウィンドウで起動
start  "CmdClient" cmd /c "call .\VE\Scripts\activate && python CmdClient.py"