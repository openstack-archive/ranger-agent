FROM ubuntu:16.04 

ENV DEBIAN_FRONTEND noninteractive
ENV container docker
ENV PORT 9000
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8


RUN apt -qq update && \
apt -y install git \
netcat \
netbase \
curl \
openssh-server \
python-minimal \
python-setuptools \
python-pip \
python-dev \
python-dateutil \
ca-certificates \
openstack-pkg-tools \
python-mysqldb \
gcc \
g++ \
make \
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

RUN cd ~/ \
    && rm /etc/ranger-agent/* \
    && rm -fr /tmp/ranger-agent \
    && mkdir /var/log/ranger-agent

# Create user ranger_agent
RUN useradd -u 1000 -ms /bin/bash ranger_agent 

# Change permissions
RUN chown -R ranger_agent: /home/ranger_agent \
    && chown -R ranger_agent: /etc/ranger-agent \
    && chown -R ranger_agent: /var/log/ranger-agent

# Set work directory
USER ranger_agent
WORKDIR /home/ranger_agent/
