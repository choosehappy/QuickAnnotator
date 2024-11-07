# QuickAnnotator
Quick Annotator is an open-source digital pathology annotation tool.

# Purpose
Machine learning approaches for segmentation of histologic primitives (e.g., cell nuclei) in digital pathology (DP) Whole Slide Images (WSI) require large numbers of exemplars. Unfortunately, annotating each object is laborious and often intractable even in moderately sized cohorts. The purpose of QuickAnnotator is to rapidly bootstrap annotation creation for digital pathology projects. 

QuickAnnotator leverages active learning to suggest annotations which the user may accept as they annotate.

# Installation
## Using Docker (Recommended)
Docker is now the recommended method for installing and running QuickAnnotator. Containerized runtimes like docker are more portable and avoid issues with python environment management, and ensure reproducible application behavior. Docker is available for Windows, MacOS, and Linux.

>**Note**: These instructions assume you have docker engine installed on your system. If you do not have docker installed, please see the [docker installation instructions](https://docs.docker.com/engine/install/).

1. Begin by pulling the [official QuickAnnotator docker image](https://hub.docker.com/r/histotools/quickannotator/tags) from docker hub. This repository contains the latest stable version of QuickAnnotator and is guaranteed up-to-date.
    ```bash
    docker pull histotools/quickannotator:master
    ```

1. Next, run the docker image with a few options to mount your data directory and expose the web interface on your host machine.

    ```bash
    docker run -v <local-path>:/data --name <container-name> -p <local-port>:5000 -it histotools/quickannotator:master /bin/bash
    # Example:
    # docker run -v /local/datadir:/data --name my_container -p 5000:5000 -it histotools/quickannotator:master /bin/bash
    ```

1. A terminal session will open inside the docker container. You can now run QuickAnnotator as you would on a local machine. 

1. If you exit the shell, the container will stop running but no data/configuration will be lost. You can restart the container and resume your work with the following command:

    ```bash
    docker start -i <container-name>
    # Example:
    # docker start -i my_container
    ```

## Using PyPI
QuickAnnotator has not yet been released on PyPI.