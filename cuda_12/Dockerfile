FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu20.04
CMD nvidia-smi

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

COPY ./cuda_12/requirements.txt /opt/QuickAnnotator/requirements.txt
WORKDIR /opt/QuickAnnotator
RUN pip3 install -r requirements.txt
COPY . /opt/QuickAnnotator

ADD . /opt/QuickAnnotator
CMD ["python3", "QA.py"]
