**路径规划微服务**
=====================

本项目借用V2V的多进程调度框架，实现对本地的MAPF算法包的调度，并以微服务的方式进行发布，供前端调用。

发布路径规划微服务需要先确定在windows还是linux上发布。然后在对应的操作系统上编译最新的cbs可执行文件，将其拷贝到本工程的src\mapf文件夹下。然后按下面步骤执行。

一、Windows快速体验
--------

### 预装环境

- Windows10系统。
- 已经安装Miniconda3。
- 创建python 3.7.8虚拟环境，安装依赖包（requirements.txt）。

### 运行步骤

Windows10环境下代码演示如下。

1.打开Pycharm，用Pycharm打开根目录创建工程，并如下配置运行参数。
![img.png](docs\images\envi.png)
2.运行工程，访问[本地服务](http://127.0.0.1:7080/docs)。

二、Linux快速体验
--------

### 预装环境

- linux环境
- docker可用

### 运行步骤

发布文件包只涉及到src、Dockerfile、requirements.txt。
包中含有cbs和boost可执行。

- 解压文件包。

```
tar zxvf mptools-mapf-scheduler.tar.gz
```

- 在解压目录，运行如下代码。

```
cd mptools-mapf-scheduler
sudo docker build -t cbs_rt:v1 .
```

- 运行docker

```
docker run -p 7080:7080 cbs_rt:v1 
```

致谢
=====================

Cookiecutter。

lvyu
26896225@qq.com

```

```
