FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel

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
         ffmpeg \
         libsm6 \
         libxext6 \
         memcached \
         # development tools
         git \
         vim 

# Install node and npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs

RUN mkdir -p /opt/QuickAnnotator
WORKDIR /opt/QuickAnnotator
COPY ./pyproject.toml /opt/QuickAnnotator/pyproject.toml

# Install uv
RUN pip install uv

# Create a virtual environment for uv and install all dependencies
ENV UV_VENV_PATH="/opt/uv_venv"
RUN source $UV_VENV_PATH/bin/activate
RUN uv pip install -r <(uv pip compile pyproject.toml)

# # Install node dependencies
# WORKDIR /opt/
# RUN npm install QuickAnnotator/quickannotator/client
# ENV NODE_PATH=/opt/node_modules

WORKDIR /opt/QuickAnnotator
