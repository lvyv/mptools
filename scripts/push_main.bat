cd ../tests/vs/ffmpeg-win64-gpl-vulkan/bin
start ffmpeg -re -stream_loop -1 -i ./main.ts -rtsp_transport tcp -vcodec libx264 -f rtsp rtsp://127.0.0.1:7554/main
cd ../../../../scripts