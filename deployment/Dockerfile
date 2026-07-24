FROM rayproject/ray:2.49.1-py310-cu121
SHELL ["/bin/bash", "-c"]

USER root

CMD nvidia-smi

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" --no-install-recommends \
        build-essential \
        cmake \
        ca-certificates \
        libglib2.0-0 \
        libjpeg-dev \
        libpng-dev \
        gcc gfortran libopenblas-dev liblapack-dev cython3 \
        sqlite3 \
        libsqlite3-dev \
        libsqlite3-mod-spatialite \
        libtk8.6 \
        procps \
        curl \
        ffmpeg \
        libsm6 \
        libxext6 \
        memcached \
        graphviz \
        libgraphviz-dev \
        libgdal-dev \
        gdal-bin \
        python3-gdal \
        tmux \
        software-properties-common \
        # development tools
        git \
        vim 

# Add the OpenSlide PPA for the latest OpenSlide release, then install just the library
RUN add-apt-repository -y ppa:openslide/openslide && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libopenslide1

# Install node and npm
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

RUN chown ray:users /opt

USER ray
RUN mkdir -p /opt/QuickAnnotator
WORKDIR /opt/QuickAnnotator

# Copy the dependencies files and install python dependencies.
# --chown is needed because USER ray only affects run commands, not copy commands.
# --mount is a feature that allows caching of pip downloads between builds.
COPY --chown=ray:users ../pyproject.toml /opt/QuickAnnotator/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r pyproject.toml --system \
    --index-url https://download.pytorch.org/whl/cu121 \
    --extra-index-url https://pypi.org/simple
COPY --chown=ray:users ./ /opt/QuickAnnotator/
# Install QuickAnnotator to the uv-managed environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install . --system


# Install node dependencies
COPY --chown=ray:users ../quickannotator/client/package.json ../quickannotator/client/package-lock.json /opt/
ENV NODE_PATH=/opt/node_modules
WORKDIR /opt
RUN npm ci

WORKDIR /opt/QuickAnnotator
ENV PYTHONPYCACHEPREFIX=/opt/qa_pycache