
FROM netlify/build:focal as base

ARG PRIVATE_ACCESS_TOKEN
ARG SKIP_STATS
ARG STACK_MODULE
ARG LOGLEVEL

WORKDIR /interwebz
ADD package.json .
ADD package-lock.json .
ADD requirements.txt .

ADD . .

EXPOSE 1313
CMD ["echo", "Website docker image build done."]
