
FROM node

ENV HUGO_VER=0.88.1

RUN apt-get update -qq
RUN apt-get install -y ca-certificates wget curl rsync
RUN apt-get install -y python3-yaml

RUN wget -q -O /tmp/hugo.deb https://github.com/gohugoio/hugo/releases/download/v${HUGO_VER}/hugo_extended_${HUGO_VER}_Linux-64bit.deb
RUN dpkg -i /tmp/hugo.deb

ADD . /build
WORKDIR /build

RUN cd website; npm install
RUN make init build

EXPOSE 1313

CMD ["make", "up"]
