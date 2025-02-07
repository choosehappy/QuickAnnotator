FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

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
         gcc gfortran libopenblas-dev liblapack-dev cython3 \
         sqlite3 \
         libsqlite3-dev \
         libsqlite3-mod-spatialite \
         libtk8.6 \
         procps \
         libopenslide0 \
         curl \
         # development tools
         git \
         vim 

# Install node and npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs

RUN mkdir -p /opt/QuickAnnotator
WORKDIR /opt/QuickAnnotator
COPY . /opt/QuickAnnotator

ENV PATH="/opt/venv/bin:$PATH"

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --upgrade pip \
    && /opt/venv/bin/pip install -e .

# Install development python dependencies
RUN /opt/venv/bin/pip install tqdm \
                            ipykernel

# Install node dependencies
WORKDIR /opt/
RUN npm install QuickAnnotator/quickannotator/client
ENV NODE_PATH=/opt/node_modules

WORKDIR /opt/QuickAnnotator
