ARG PYTHON_VERSION=3.8

FROM debian:buster AS client

ARG ORACLE_HOST
ARG ORACLE_PORT
ARG ORACLE_SERVNAME
ARG ORACLE_PASS
ARG ORACLE_USER

ENV ORACLE_HOST=${ORACLE_HOST}
ENV ORACLE_PORT=${ORACLE_PORT}
ENV ORACLE_SERVNAME=${ORACLE_SERVNAME}
ENV ORACLE_PASS=${ORACLE_PASS}
ENV ORACLE_USER=${ORACLE_USER}

ARG ORACLE_VERSION=19.8.0.0.0
ARG OR_SHORT_VER=19800
WORKDIR /root
ARG ORACLE_ZIP_INTERNAL_FOLDER=instantclient_19_8
ENV CLIENT_ZIP=instantclient-basiclite-linux.x64-${ORACLE_VERSION}dbru.zip
ENV SDK_ZIP=instantclient-sdk-linux.x64-${ORACLE_VERSION}dbru.zip

RUN apt-get update && apt-get -yq install unzip curl

RUN curl -LJO "https://download.oracle.com/otn_software/linux/instantclient/${OR_SHORT_VER}/${CLIENT_ZIP}"\
	&& curl -LJO "https://download.oracle.com/otn_software/linux/instantclient/${OR_SHORT_VER}/${SDK_ZIP}"

RUN unzip ${CLIENT_ZIP} && unzip ${SDK_ZIP}
RUN mv ${ORACLE_ZIP_INTERNAL_FOLDER} oracle

FROM python:${PYTHON_VERSION}
ENV HOME /root
ENV ORACLE_HOME /opt/oracle
ENV TNS_ADMIN ${ORACLE_HOME}/network/admin
VOLUME ["${TNS_ADMIN}"]

ADD . /app
WORKDIR /app
ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
EXPOSE 8003
COPY --from=client /root/oracle ${ORACLE_HOME}
RUN apt-get update \
	&& apt-get -yq install libaio1 \
	&& apt-get -yq autoremove \
	&& apt-get clean \
	# Install Oracle Instant Client
	&& echo ${ORACLE_HOME} > /etc/ld.so.conf.d/oracle.conf \
	&& mkdir -p ${TNS_ADMIN} \
	&& ldconfig \
	&& rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
