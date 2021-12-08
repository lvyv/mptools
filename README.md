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
如果是windows的命令行环境，则通过如下方式设置环境变量。
```
(venv) E:\_proj\odoo-14.0.post20201231\v2v\tests>set PYTHONPATH=%PYTHONPATH%;..\src
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

v2v运行监控
--------
【注意】v2v支持prometheus和jaeger指标监测，需要提前安装Prometheus和Jaeger。
1.Prometheus的配置
需要配置Prometheus的prometheus.yml文件（docker通过volume映射在外部，targets的地方ip地址要配置为v2v的运行地址和端口）。
```
scrape_configs:
  # The job name is added as a label `job=<job_name>` to any timeseries scraped from this config.
  - job_name: 'v2v'
    scrape_interval: 1s
    metrics_path: /metrics
    scheme: https
    tls_config:
        insecure_skip_verify: true
    static_configs:
    - targets: ['192.168.43.175:7080']
    params:
        v2v: ['rest','rtsp']

```
2.Jaeger配置
需要配置v2v的tests目录的v2v.cfg配置文件，jaeger配置项的agent_ip和agent_port要配置正确。
```
  "mqtt_svrs": [
    {
      "mqtt_svr": "103.81.5.77",
      "mqtt_port": 7091,
      "mqtt_cid": "zbyw",
      "mqtt_pwd": "test123456",
      "mqtt_tp": "/adaptor/09ZiqYFlkTKTUmSP6og0/v2v",
      "fsvr_url": "https://127.0.0.1:7180/fssvr",
      "jaeger": {
        "agent_ip": "192.168.47.144",
        "agent_port": 6831,
        "enable": true
      }
    }
  ],
```
3.启动v2v主进程，如果一切正常，将从Prometheus查询到cpu_rate，mem_rate，up_time三个v2v指标。

prometheus的主界面访问接口如下示例。

http://192.168.47.144:9090

4.启动v2v的管道操作，如果一切正常，将会在jaeger主控制台看到v2v的mqtt进程上报的数据。

1）访问v2v的7080的api调试端口如下示例。

https://192.168.43.175:7080/docs

执行post /api/v1/v2v/pipeline调用，Request body的命令为{"cmd":"start"}。
该接口调用将启动v2v的视频解码、ai识别、mqtt数据上报任务流水线，如果传入{"cmd":"stop"}将停止流水线操作。

2）jaeger的主界面访问接口如下示例。

http://192.168.47.144:16686

在Service下拉列表中，过几秒时间就可以看到MQTT(0)-10908这样的服务项，10908是流水线的进程号。
选择下拉列表的MQTT(0)-xxxxx，点击Find Trace绿色按钮，右侧图形就会显示MQTT发起的链路调用。

特性
--------

- 支持标注。
- 支持取流并存为背景进行标注。
- 支持mqtt上报，并提供jaeger通信追踪上报。

代办事项
--------

- UI美化。 
- 当配置文件出错的时候，程序行为的定义。
- 识别结果以图片上传文件服务器。
- 文档内容和安装发布的完善。
- config配置文件读取需要重构。
- 前端ui部分的js代码视需重构。
- ctrl+c关闭程序的时候，windows和linux有不同的反应，代码还没屏蔽此差异（rest.py）。

致谢
-------

Cookiecutter。

