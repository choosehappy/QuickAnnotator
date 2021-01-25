FROM nvidia/cuda:11.0.3-cudnn8-devel-ubuntu20.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" --no-install-recommends \
         build-essential \
         cmake \
         ca-certificates \
         libglib2.0-0 \
         libjpeg-dev \
         libpng-dev \
         python3.8 \
         python3.8-dev \
         python3-pip \
         python3-wheel \
         python3-setuptools \
         gcc gfortran libopenblas-dev liblapack-dev cython \
         sqlite3 \
         libsqlite3-dev

# selective copy before ADD: don't rebuild pip-packages for any .py source change
COPY ./requirements.txt /opt/quick_annotator/requirements.txt

WORKDIR /opt/quick_annotator

RUN pip3 install numpy==1.17.3 && pip3 install -r requirements.txt

ADD . /opt/quick_annotator

CMD ["python3", "QA.py"]
