ARG PYTHON_VERSION=3.7
FROM ubuntu:18.04 AS client
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

ARG ORACLE_VERSION=19.3.0.0.0
ARG ORACLE_ZIP_INTERNAL_FOLDER=instantclient_19_3
WORKDIR /root
ENV CLIENT_ZIP=instantclient-basiclite-linux.x64-${ORACLE_VERSION}dbru.zip
ENV SDK_ZIP=instantclient-sdk-linux.x64-${ORACLE_VERSION}dbru.zip

RUN apt-get update && apt-get -yq install unzip
COPY ${CLIENT_ZIP} .
COPY ${SDK_ZIP} .
RUN unzip ${CLIENT_ZIP}
RUN unzip ${SDK_ZIP}
RUN mv ${ORACLE_ZIP_INTERNAL_FOLDER} oracle

FROM python:${PYTHON_VERSION}
ARG ORACLE_VERSION=19.3.0.0.0
ENV HOME /root
ENV ORACLE_HOME /opt/oracle
ENV TNS_ADMIN ${ORACLE_HOME}/network/admin
VOLUME ["${TNS_ADMIN}"]

ADD . /app
WORKDIR /app
ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt 
EXPOSE 8000 
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

CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]
