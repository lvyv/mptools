cd ../tests/vs/ffmpeg-win64-gpl-vulkan/bin
start ffmpeg -re -stream_loop -1 -i ./plc.mp4 -rtsp_transport tcp -vcodec libx264 -f rtsp rtsp://127.0.0.1:7554/plc
start ffmpeg -re -stream_loop -1 -i ./panel.mp4 -rtsp_transport tcp -vcodec libx264 -f rtsp rtsp://127.0.0.1:7554/panel
start ffmpeg -re -stream_loop -1 -i ./person.mp4 -rtsp_transport tcp -vcodec libx264 -f rtsp rtsp://127.0.0.1:7554/person
