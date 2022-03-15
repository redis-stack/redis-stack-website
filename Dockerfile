
FROM node as base

ARG PRIVATE_REPOS_PAT
ENV HUGO_VER=0.88.1

RUN apt-get update -qq
RUN apt-get install -y ca-certificates wget curl git rsync python3 python3-pip

RUN wget -q -O /tmp/hugo.deb https://github.com/gohugoio/hugo/releases/download/v${HUGO_VER}/hugo_extended_${HUGO_VER}_Linux-64bit.deb
RUN dpkg -i /tmp/hugo.deb

WORKDIR /build
ADD Makefile .
ADD package*.json .
ADD ./build ./build
ADD ./data ./data
RUN npm install
RUN pip install -r build/requirements.txt

FROM base
ADD . .
RUN make all

EXPOSE 1313
CMD ["echo", "Docker image build done."]