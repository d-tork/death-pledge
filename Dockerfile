FROM ubuntu:20.04

ARG GIT_HASH
ENV GIT_HAS=${GIT_HASH:-dev}

RUN apt-get update -y && DEBIAN_FRONTEND=noninteractive apt-get install python3.7 python3-pip firefox -y

WORKDIR ./death-pledge

COPY requirements.txt ./
RUN pip3 install -r requirements.txt

COPY . .
RUN pip3 install -e .

# CMD to run should be a script which runs deathpledge on a schedule!
ENTRYPOINT ["/usr/bin/python3", "deathpledge"]
CMD ["--help"]
