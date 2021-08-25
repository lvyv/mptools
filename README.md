V2V测试联调指南
=====================

快速开始
--------

1.下载代码到本地，安装requirments.txt的包，冒烟测试基本功能。

```
(v2v) bda@c3daace9a16d:~/work$ git clone https://gitee.com/iovVis/v2v.git v2v
(v2v) bda@c3daace9a16d:~/work$ cd v2v
(v2v) bda@c3daace9a16d:~/work$ pip install -r requirments.txt
(v2v) bda@c3daace9a16d:~/work$ export PYTHONPATH=$PYTHONPATH:/home/bda/work/v2v/src/
(v2v) bda@c3daace9a16d:~/work$ cd tests
(v2v) bda@c3daace9a16d:~/work/tests$ python test_bus.py
```
2.在命令行终端界面上，进行功能测试。

第一、启动仿真接口
```
(v2v) bda@c3daace9a16d:~/work/tests$ cd ../src/mock
(v2v) bda@c3daace9a16d:~/work/v2v/src/mock$ python exif.py
```
第二、启动推流
```
$ ffmpeg.exe -re -i /stream/main.ts -rtsp_transport tcp -vcodec copy -f rtsp rtsp://10.128.19.91:7554/meter
$ ffmpeg.exe -re -i /stream/plc.ts -rtsp_transport tcp -vcodec copy -f rtsp rtsp://10.128.19.91:7554/plc
```
第三、配置tests目录下的v2v.cfg，设置对应的流媒体路径与上面的推流地址匹配

3.缺省通过浏览器访问
https://127.0.0.1:7080/ui/index.html

特性
--------

- 支持标注。
- 支持取流并存为背景进行标注。

代办事项
--------

- UI美化。 
- 文档内容和安装发布的完善。


致谢
-------

Cookiecutter。

