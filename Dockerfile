
FROM redisfab/hugo:latest

ADD . /build
WORKDIR /build

RUN cd website; npm install
RUN make init stack

EXPOSE 1313

CMD ["make", "serve"]
