# https://github.com/iminders/services/blob/master/docker-images/aiminders/bazel/latest.Dockerfile
FROM registry.cn-hangzhou.aliyuncs.com/aiminders/bazel:latest

RUN apt-get -y update --fix-missing && \
    apt-get -y upgrade --fix-missing && \
    DEBIAN_FRONTEND=noninteractive apt-get -y install --fix-missing \
        gcc \
        g++ \
        zlibc \
        zlib1g-dev \
        libssl-dev \
        libbz2-dev \
        libsqlite3-dev \
        libncurses5-dev \
        libgdbm-dev \
        libgdbm-compat-dev \
        liblzma-dev \
        libreadline-dev \
        uuid-dev \
        libffi-dev \
        tk-dev \
        wget \
        curl \
        git \
        make \
        sudo \
        bash-completion \
        tree \
        vim \
        software-properties-common && \
    mv /usr/bin/lsb_release /usr/bin/lsb_release.bak && \
    apt-get -y autoclean && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt-get/lists/*

ENV CODE_DIR /root/trade

ARG BUILD_TIME
ENV BUILD_TIME=${BUILD_TIME}

# install tgym
WORKDIR  $CODE_DIR
RUN cd $CODE_DIR
RUN rm -rf tgym
RUN git clone https://github.com/iminders/tgym.git
# Clean up pycache and pyc files
RUN cd $CODE_DIR/tgym && rm -rf __pycache__ && \
    find . -name "*.pyc" -delete && \
    pip install -r requirements.txt && \
    pip install -e .

RUN rm -rf /root/.cache/pip \
    && find / -type d -name __pycache__ -exec rm -r {} \+

WORKDIR $CODE_DIR/tgym

ARG TUSHARE_TOKEN
ENV TUSHARE_TOKEN=${TUSHARE_TOKEN}
RUN export TUSHARE_TOKEN=$TUSHARE_TOKEN

CMD /bin/bash
