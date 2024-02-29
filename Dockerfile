FROM ubuntu:20.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" --no-install-recommends \
         build-essential \
         libtinfo5 \
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
COPY ./requirements_cpuonly.txt /opt/QuickAnnotator/requirements_cpuonly.txt

WORKDIR /opt/QuickAnnotator

RUN pip3 install -r requirements_cpuonly.txt

ADD . /opt/QuickAnnotator

CMD ["python3", "QA.py"]
