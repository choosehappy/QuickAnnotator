FROM rayproject/ray-ml:2.49.1.3fe06a-py310-gpu
SHELL ["/bin/bash", "-c"]

USER root

CMD nvidia-smi

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" --no-install-recommends \
         build-essential \
         cmake \
         ca-certificates \
         # python3-venv \  # likely included in rayproject/ray:2.49.1-py310-cu124
         # python3-wheel \ # likely included
         # python3-dev \   # likely included
         # python3-pip \   # likely included
         # python3-setuptools \ # likely included
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
         ffmpeg \
         libsm6 \
         libxext6 \
         memcached \
         # development tools
         git \
         vim \
         graphviz \
         libgraphviz-dev \
         libgdal-dev \
         gdal-bin \
         python3-gdal

# Install node and npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs

RUN mkdir -p /opt/QuickAnnotator
WORKDIR /opt/QuickAnnotator

# Copy the dependencies files and install python dependencies
COPY ./pyproject.toml /opt/QuickAnnotator/pyproject.toml
COPY ./uv.lock /opt/QuickAnnotator/uv.lock
RUN uv sync --frozen

# Install node dependencies
COPY ./quickannotator/client/package.json /opt/package.json
COPY ./quickannotator/client/package-lock.json /opt/package-lock.json
ENV NODE_PATH=/opt/node_modules
WORKDIR /opt
RUN npm ci

WORKDIR /opt/QuickAnnotator
