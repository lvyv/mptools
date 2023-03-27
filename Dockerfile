FROM ubuntu:18.04
LABEL maintainer="lvyu <26896225@qq.com>"
#3.Build-time metadata as defined at http://label-schema.org
SHELL ["/bin/bash", "-c"]
#4.Install dependencies and python
RUN apt-get update && \
    apt-get install -y \
    python3 python3-dev python3-pip curl \
    git dpkg-dev cmake g++ gcc binutils libx11-dev \
    libxpm-dev libxft-dev libxext-dev sudo && \
    rm -rf /var/lib/apt/lists/* && \
    pip3 install --upgrade pip setuptools && \
    # make some useful symlinks that are expected to exist
    if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
    if [[ ! -e /usr/bin/python-config ]]; then ln -sf /usr/bin/python3-config /usr/bin/python-config; fi && \
    if [[ ! -e /usr/bin/pip ]]; then ln -sf /usr/bin/pip3 /usr/bin/pip; fi
#5.Create ROOT user
RUN groupadd -g 1000 rootusr && adduser --disabled-password --gecos "" -u 1000 --gid 1000 rootusr && \
    echo "rootusr ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers
USER    rootusr
ENV HOME /home/rootusr

WORKDIR $HOME
ADD requirements.txt requirements.txt
ADD src src
RUN sudo chmod 755 src/mapf/cbs
RUN sudo mv src/mapf/libboost_program_options.so.1.65.1 /usr/lib/
RUN sudo ldconfig
RUN sudo chown -R rootusr:rootusr *
# RUN pip install -r requirements.txt
RUN pip install -r requirements.txt  -i http://mirrors.aliyun.com/pypi/simple/  --trusted-host mirrors.aliyun.com
#16.

WORKDIR $HOME/src
CMD python main.py