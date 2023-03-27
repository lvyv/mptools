**路径规划微服务**
=====================
本项目借用V2V的多进程调度框架，实现对本地的MAPF算法包的调度，并以微服务的方式进行发布，供前端调用。

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
```buildoutcfg
tar zxvf mptools-mapf-scheduler.tar.gz
```
- 在解压目录，运行如下代码。
```buildoutcfg
cd cd mptools-mapf-scheduler
sudo docker build -t cbs_rt:v1 .
```
- 运行docker
```buildoutcfg
docker run -p 7080:7080 cbs_rt:v1 

docker stop et_mapf_v1
docker start et_mapf_v1
```


三、待办事项
--------
- 支持pipeline在程序启动后自动启动。
- 配置数据在客户端重新显示（更换浏览器后）。
- UI美化。 
- 远程调用的输入参数和返回值没有规范化，应该统一为类便于修改。
- 当配置文件出错的时候，程序行为的定义。
- ctrl+c关闭程序的时候，windows和linux有不同的反应，代码还没屏蔽此差异（rest.py）。

致谢
=====================
Cookiecutter。

lvyu
26896225@qq.com

