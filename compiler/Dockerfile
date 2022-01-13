FROM alpine:3.15

RUN apk add --no-cache \
    # Build tools \
    cmake \
    g++\
    make \
    # MOTION dependencies \
    boost-dev \
    flatbuffers-dev \
    fmt-dev \
    openssl-dev \
    # Dependencies for our compiler \
    python3 \
    py3-jinja2 \
    py3-networkx \
    py3-pydot \
    # All of the below dependencies are for z3 \
    z3-dev \
    py3-z3 \
    py3-setuptools

WORKDIR /mpc
VOLUME /mpc
