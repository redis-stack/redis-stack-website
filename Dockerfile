
FROM redisfab/hugo:latest

ADD . /build
WORKDIR /build

RUN cd website; npm install
RUN make init build

EXPOSE 1313

CMD ["make", "up"]
