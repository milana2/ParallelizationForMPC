FROM ubuntu:focal

RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get -y install cmake g++-10 make libboost-all-dev libssl-dev python3.9 python3-pip git
RUN python3.9 -m pip install z3-solver networkx pydot jinja2

WORKDIR /mpc
VOLUME /mpc
