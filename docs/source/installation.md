# Installation
**General Prerequisites**

Ensure the following prerequisites are met on your machine:
- [Docker](https://docs.docker.com/get-docker/) Install Docker desktop for Windows, MacOS or Linux. For Linux, you can alternatively install [docker engine](https://docs.docker.com/engine/install/).
- [NVIDIA Driver](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
  
## 1. Quick Start
The following instructions detail how to install QuickAnnotator on a single node (e.g., a laptop with GPU support).



### 1.1. Installation Steps
1. Download the docker compose file from the QuickAnnotator repository:
    ```bash
    curl -O https://raw.githubusercontent.com/choosehappy/QuickAnnotator/main/deployment/docker-compose.yaml
    ```

2. Run the docker compose file:
    ```bash
    docker compose -f docker-compose.yaml up -d
    ```

## 2. Multi-node Deployment
Ray cluster launcher is used for multi-node deployments.
### 2.1. Additional Prerequisites
- Each worker node must match the general prerequisites listed above.
- The machine running `ray up` must have passwordless SSH access to all cluster nodes.
- All machines must have a two NAS shares mounted within the `Quickannotator/quickannotator/mounts` directory:
   1. `nas_read`: A share with at least read access.
   2. `nas_write`: A share with read and write access.

### 2.2. Installation Steps
1. Clone the git repository and checkout the v2.0 branch:
    ```bash
    git clone https://github.com/choosehappy/QuickAnnotator.git
    cd QuickAnnotator
    git checkout v2.0
    ```

2. Configure the `deployment/multi_node_cluster_config.yaml` file to specify the head and worker nodes of your ray cluster. See the [ray cluster launcher documentation](https://docs.ray.io/en/latest/cluster/vms/user-guides/launching.html) for more details. 
    > All lines with the comment `CHANGE ME` must be configured.

3. Install ray cluster launcher
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r deployment/requirements.txt
    ```


4. Run ray cluster launcher to start a ray cluster and deploy QuickAnnotator:
    ```bash
    ray up -y deployment/multi_node_cluster_config.yaml
    ```


## 3. For Developers
### 3.1. Additional Prerequisites
- VS Code with the devcontainers extension installed.

### 3.2. Installation Steps
1. Clone the git repository and checkout the v2.0 branch:
    ```bash
    git clone https://github.com/choosehappy/QuickAnnotator.git
    cd QuickAnnotator
    git checkout v2.0
    chmod -R g+rw .
    ```

```{note}
The command `chmod -R g+rw .` ensures that both the host and the docker container users have access to the repository files.
```

2. Set your env variables in the `deployment/dev.env` file.
3. Within VS Code, open the cloned repository and click on the "Reopen in Container" button to build the devcontainer. This will create a docker container with all the necessary dependencies to run QuickAnnotator.
![image](https://github.com/user-attachments/assets/b776577f-a4c2-4eb8-858c-c603ac20cc6d)