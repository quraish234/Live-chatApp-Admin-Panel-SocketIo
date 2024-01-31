@echo off
echo Starting live chat server...

REM Assuming Activate.ps1 is in the specified location and can be executed
call e:/LiveChatVersionControlled/livechat/Scripts/Activate

REM Change to the directory where your Python script is located
cd E:\LiveChatVersionControlled\Live-chatApp-Admin-Panel-SocketIo

REM Assuming 'python' is in the system's PATH
python app.py
