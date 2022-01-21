cd ../tests
set PYTHONPATH=%PYTHONPATH%;..\src
start python test_main.py
cd ../scripts
start "C:\Program Files\Google\Chrome\Application\chrome.exe" https://127.0.0.1:7080/docs/