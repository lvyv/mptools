V2V测试联调指南
=====================

快速开始
--------
【注意】下面的所有命令都需要运行在python 3.6.8及以上的虚拟环境下。

通过pip安装虚拟环境（virtualenv）不赘述，主要过程是先要yum或apt-get安装python3.x的版本。
在用安装好的python3.x版本的对应pip3.x来安装一个virtualenv包，再用python运行virtualenv包创建虚拟环境。
最后在虚拟环境的bin目录，source activate，激活虚拟环境。之后在这个虚拟环境下pip安装各种包即可。

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
第二、启动推流（本地自己调建议自建一个RTSP流媒体服务器OBS+RTSP Server插件，模仿NVR提供流）
```
$ ffmpeg.exe -re -i /stream/main.ts -rtsp_transport tcp -vcodec copy -f rtsp rtsp://10.128.19.91:7554/meter
$ ffmpeg.exe -re -i /stream/plc.ts -rtsp_transport tcp -vcodec copy -f rtsp rtsp://10.128.19.91:7554/plc
```
第三、配置tests目录下的v2v.cfg，设置对应的流媒体路径与上面的推流地址匹配


第四、在代码的tests路径下启动v2v服务
```
(v2v) bda@c3daace9a16d:~/work/tests$ python test_main.py
```

3.缺省通过浏览器访问
https://127.0.0.1:7080/ui/index.html

特性
--------

- 支持标注。
- 支持取流并存为背景进行标注。
- 支持mqtt上报，并提供jaeger通信追踪上报。

代办事项
--------

- UI美化。 
- 文档内容和安装发布的完善。
- config配置文件读取需要重构。
- 前端ui部分的js代码视需重构。
- ctrl+c关闭程序的时候，windows和linux有不同的反应，代码还没屏蔽此差异（rest.py）。

致谢
-------

Cookiecutter。

