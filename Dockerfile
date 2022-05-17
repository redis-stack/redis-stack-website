
FROM netlify/build:focal as base

ARG PRIVATE_ACCESS_TOKEN
ARG SKIP_STATS
ARG STACK_MODULE
ARG LOGLEVEL

WORKDIR /interwebz
ADD package.json .
ADD package-lock.json .
ADD requirements.txt .

USER root

RUN git config --global --add safe.directory /interwebz

RUN curl -fsSL https://deb.nodesource.com/setup_16.x |  /bin/bash

RUN apt-get install -y nodejs && \
    apt-get install -y python3-pip && \
    pip3 install -r requirements.txt && \
    npm install -g postcss-cli && \
    npm install autoprefixer

ADD . .

EXPOSE 1313
CMD ["echo", "Website docker image build done."]
