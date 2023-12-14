#!/bin/bash

sudo DEBIAN_FRONTEND=noninteractive apt-get update -y 
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y
# https://stackoverflow.com/questions/70896701/no-module-named-distutils-util
sudo DEBIAN_FRONTEND=noninteractive apt install -y software-properties-common
sudo DEBIAN_FRONTEND=noninteractive add-apt-repository -y ppa:deadsnakes/ppa
sudo DEBIAN_FRONTEND=noninteractive apt update
sudo DEBIAN_FRONTEND=noninteractive apt-get install python3.10 -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install python3.10-dev -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install python3.10-tk -y
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 2
sudo DEBIAN_FRONTEND=noninteractive apt-get install python3.10-distutils -y
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

sudo DEBIAN_FRONTEND=noninteractive apt update
# Our Compiler needs these
sudo DEBIAN_FRONTEND=noninteractive apt install -y graphviz
# MOTION Deps
sudo DEBIAN_FRONTEND=noninteractive apt install -y build-essential make git cmake libssl-dev libboost-program-options-dev
# MP-SPDZ Deps
sudo DEBIAN_FRONTEND=noninteractive apt install -y automake build-essential clang cmake git libboost-dev libboost-thread-dev libntl-dev libsodium-dev libssl-dev libtool m4 texinfo yasm


git config --global user.name = "Muhammad Ishaq"
git config --global user.email = "ishaq@ishaq.pk"

#sudo tc qdisc add dev lo root tbf rate 10gbit burst 250mbit latency 500us
#sudo tc qdisc add dev lo root tbf rate 500mbit burst 2.5mbit latency 1000ms

cd /mydata
sudo chown -R ishaq .

git clone --recursive https://github.com/milana2/ParallelizationForMPC.git
cd ParallelizationForMPC/compiler
python3.10 -m pip install -r requirements.txt
#git checkout -b 3-party-benchmarks --track origin/3-party-benchmarks
