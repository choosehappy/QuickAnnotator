FROM nvidia/cuda:11.0.3-cudnn8-devel-ubuntu20.04
CMD nvidia-smi

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" --no-install-recommends \
         build-essential \
         cmake \
         ca-certificates \
         python3-venv \
         python3-wheel \
         python3-dev \
         python3-setuptools \
         libglib2.0-0 \
         libjpeg-dev \
         libpng-dev \
         gcc gfortran libopenblas-dev liblapack-dev cython \
         sqlite3 \
         libsqlite3-dev \
         libsqlite3-mod-spatialite \
         libtk8.6 \
         procps \
         git \
         libopenslide0 \
         vim

RUN mkdir -p /opt/QuickAnnotator
WORKDIR /opt/QuickAnnotator
COPY . /opt/QuickAnnotator
ENV PATH="/opt/QuickAnnotator/venv/bin:$PATH"


RUN python3 -m venv venv \
    && pip install .

CMD ["python3", "-m", "quickannotator"]