FROM ubuntu:16.04

ENV DEBIAN_FRONTEND noninteractive
ENV container docker
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8


RUN apt -qq update && \
apt -y install git \
netcat \
netbase \
openssh-server \
python-minimal \
python-setuptools \
python-pip \
python-dev \
python-dateutil \
ca-certificates \
openstack-pkg-tools \
gcc \
g++ \
libffi-dev \
libssl-dev --no-install-recommends \
&& apt-get clean \
&& rm -rf \
     /var/lib/apt/lists/* \
     /tmp/* \
     /var/tmp/* \
     /usr/share/man \
     /usr/share/doc \
     /usr/share/doc-base

RUN pip install wheel

COPY . /tmp/ranger-agent

WORKDIR /tmp/ranger-agent

RUN pip install --default-timeout=100 -r requirements.txt

RUN python setup.py install

# Create user ranger_agent
RUN useradd -u 1000 -ms /bin/bash ranger_agent

# Change permissions
RUN chown -R ranger_agent: /home/ranger_agent \
    && chown -R ranger_agent: /etc/ranger-agent \
    && mkdir /var/log/ranger-agent \
    && chown -R ranger_agent: /var/log/ranger-agent \
    && cp -fr tools/.ssh  /home/ranger_agent/ \
    && chown -R ranger_agent: /home/ranger_agent/.ssh \
    && chmod 700 -R /home/ranger_agent/.ssh \
    && chmod 644 /home/ranger_agent/.ssh/config \
    && chmod 600 /home/ranger_agent/.ssh/ranger_agent \
    && cd ~/ \
    && rm -fr /tmp/ranger-agent

# Set work directory
USER ranger_agent
WORKDIR /home/ranger_agent/
