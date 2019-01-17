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

ARG user

# Create user for ranger-agent
RUN useradd -u 1000 -ms /bin/false ${user:-ranger_agent}

# Change permissions
RUN chown -R ${user:-ranger_agent}: /home/${user:-ranger_agent} \
    && chown -R ${user:-ranger_agent}: /etc/ranger-agent \
    && mkdir /var/log/ranger-agent \
    && chown -R ${user:-ranger_agent}: /var/log/ranger-agent \
    && cd ~/ \
    && rm -fr /tmp/ranger-agent

# Set work directory
USER ${user:-ranger_agent}
WORKDIR /home/${user:-ranger_agent}/
