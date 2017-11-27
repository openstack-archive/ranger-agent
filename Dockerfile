FROM ubuntu:16.04 

ENV DEBIAN_FRONTEND noninteractive
ENV container docker
ENV PORT 9000
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8


RUN apt -qq update && \
apt -y install git \
netbase \
python-minimal \
python-setuptools \
python-pip \
python-dev \
ca-certificates \
openstack-pkg-tools \
python-mysqldb \
gcc \
g++ \
make \
libffi-dev \
libssl-dev --no-install-recommends
RUN pip install wheel

COPY . /tmp/ranger-agent

WORKDIR /tmp/ranger-agent

RUN pip install -r requirements.txt
RUN python setup.py install


