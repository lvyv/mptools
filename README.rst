=====================
V2V测试联调指南
=====================
rootbdahtyw!@#bda

1.首先需要easyconnect，通过vpn连接到测试环境

2.在Chrome浏览器中输入以下地址，密码是缺省密码
http://10.128.19.91:7888/lab/workspaces/work

3.在界面上创建一个Terminal终端，进行单元测试(本步骤在集成时，可以忽略)

(base) bda@c3daace9a16d:~$ cd work
(base) bda@c3daace9a16d:~/work$ conda activate v2v
(v2v) bda@c3daace9a16d:~/work$ cd v2v (如果是第一次，需要下载代码，git clone https://gitee.com/iovVis/v2v.git v2v)
(v2v) bda@c3daace9a16d:~/work$ git pull
(v2v) bda@c3daace9a16d:~/work$ export PYTHONPATH=$PYTHONPATH:/home/bda/work/v2v/src/
(v2v) bda@c3daace9a16d:~/work$ cd tests
(v2v) bda@c3daace9a16d:~/work/tests$ python test_bus.py
2021-08-23 08:58:39,125 - v2v - INFO -   0:00.024 A1-2149              Entering startup.
2021-08-23 08:58:39,126 - v2v - INFO -   0:00.025 A1-2149              {'reply': 'No corresponding method handler.'}(0)
2021-08-23 08:58:39,127 - v2v - INFO -   0:00.025 A1-2149              {'reply': 'No corresponding method handler.'}(1)
2021-08-23 08:58:39,127 - v2v - INFO -   0:00.026 A1-2149              {'reply': 'No corresponding method handler.'}(2)
2021-08-23 08:58:39,127 - v2v - INFO -   0:00.026 A1-2149              Leaving main_loop.
2021-08-23 08:58:39,127 - v2v - INFO -   0:00.026 A1-2149              Entering shutdown.
.2021-08-23 08:58:39,243 - v2v - INFO -   0:00.141 C3-2168              startup called.
2021-08-23 08:58:39,243 - v2v - INFO -   0:00.142 C2-2167              startup called.
2021-08-23 08:58:39,243 - v2v - INFO -   0:00.142 C1-2166              startup called.
2021-08-23 08:58:39,245 - v2v - INFO -   0:00.143 TestBus              {'up': True}
2021-08-23 08:58:39,245 - v2v - INFO -   0:00.144 TestBus              {'up': True}
2021-08-23 08:58:39,245 - v2v - INFO -   0:00.144 TestBus              {'up': True}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.144 C1-2166              subscribed msg:{'msg': 1}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.144 C1-2166              subscribed msg:{'msg': 2}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C1-2166              subscribed msg:{'msg': 3}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C3-2168              subscribed msg:{'msg': 1}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C1-2166              Leaving main_loop.
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C1-2166              shutdown called.
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C2-2167              subscribed msg:{'msg': 1}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C3-2168              subscribed msg:{'msg': 2}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C3-2168              subscribed msg:{'msg': 3}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C2-2167              subscribed msg:{'msg': 2}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C3-2168              Leaving main_loop.
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C3-2168              shutdown called.
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C2-2167              subscribed msg:{'msg': 3}
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C2-2167              Leaving main_loop.
2021-08-23 08:58:39,246 - v2v - INFO -   0:00.145 C2-2167              shutdown called.
.2021-08-23 08:58:39,359 - v2v - INFO -   0:00.258 TestBus              {'p1': 0, 'p2': 'hello'}
2021-08-23 08:58:39,360 - v2v - INFO -   0:00.259 TestBus              {'p1': 0, 'p2': 'hello'}
2021-08-23 08:58:39,360 - v2v - INFO -   0:00.259 TestBus              {'p1': 0, 'p2': 'hello'}
2021-08-23 08:58:39,360 - v2v - INFO -   0:00.259 TestBus              {'p1': 0, 'p2': 'hello'}
2021-08-23 08:58:39,361 - v2v - INFO -   0:00.259 TestBus              {'p1': 0, 'p2': 'hello'}
2021-08-23 08:58:39,361 - v2v - INFO -   0:00.259 TestBus              {'p1': 0, 'p2': 'hello'}
.2021-08-23 08:58:39,476 - v2v - INFO -   0:00.374 TestBus              {'p1': 0, 'p2': 'hello'}
2021-08-23 08:58:39,477 - v2v - INFO -   0:00.375 TestBus              {'p1': 0, 'p2': 'hello'}
2021-08-23 08:58:39,477 - v2v - INFO -   0:00.376 TestBus              {'p1': 0, 'p2': 'hello'}
.
----------------------------------------------------------------------
Ran 4 tests in 0.473s

OK
(v2v) bda@c3daace9a16d:~/work/tests$

4.在界面上，进行功能测试
第一、启动仿真接口
(v2v) bda@c3daace9a16d:~/work/tests$ cd ../src/mock
(v2v) bda@c3daace9a16d:~/work/v2v/src/mock$ python exif.py
第二、启动推流
(v2v) bda@c3daace9a16d:~/work/v2v/src/mock$ .\ffmpeg.exe -re -i D:\ffmpeg-win64-gpl-vulkan\bin\main.ts -rtsp_transport tcp -vcodec copy -f rtsp rtsp://10.128.19.91:7554/meter
(v2v) bda@c3daace9a16d:~/work/v2v/src/mock$ .\ffmpeg.exe -re -i D:\ffmpeg-win64-gpl-vulkan\bin\plc.ts -rtsp_transport tcp -vcodec copy -f rtsp rtsp://10.128.19.91:7554/plc






系统相关
--------

* 如果需要安装其它工具，需要如下操作，此前修改了ubuntu 20.04的源
$ su
# apt install xxx
$ exit
$ . /opt/dev_pkgs/bin/activate



特性
--------

* 代办事项


路线图
--------

 * Write up proper docs and get them up on Readthedocs


致谢
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
