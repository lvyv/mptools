cd ../tests/vs/ffmpeg-win64-gpl-vulkan/bin
start /b ffmpeg -re -stream_loop -1 -i ./plc.mp4 -rtsp_transport tcp -vcodec libx264 -f rtsp rtsp://192.168.101.19:7554/plc
start /b ffmpeg -re -stream_loop -1 -i ./panel.mp4 -rtsp_transport tcp -vcodec libx264 -f rtsp rtsp://192.168.101.19:7554/panel
start /b ffmpeg -re -stream_loop -1 -i ./person.mp4 -rtsp_transport tcp -vcodec libx264 -f rtsp rtsp://192.168.101.19:7554/person
