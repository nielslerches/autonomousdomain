FROM python:3

ADD . /mnt
WORKDIR /mnt

RUN pip install -r requirements.txt
