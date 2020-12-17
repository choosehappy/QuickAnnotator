FROM nvidia/cuda:10.2-cudnn7-devel-ubuntu18.04
RUN apt-get update && apt-get install -y --no-install-recommends \
         build-essential \
         cmake \
         ca-certificates \
         libglib2.0-0 \
         libjpeg-dev \
         libpng-dev \
         python3.6 \
         python3-pip \
         python3-wheel \
         python3-setuptools \
         sqlite3 \
         libsqlite3-dev


ADD . /opt/quick_annotator

WORKDIR /opt/quick_annotator

RUN pip3 install -r requirements.txt

CMD ["python3.6", "QA.py"]

