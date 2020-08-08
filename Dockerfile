ARG PYTHON_VERSION=3.8

FROM python:${PYTHON_VERSION}

ADD . /app
WORKDIR /app
ADD requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --user --no-cache-dir -r /tmp/requirements.txt
EXPOSE 8003
