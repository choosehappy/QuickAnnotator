# Installation

## 1. Quick Start
The following instructions detail how to install QuickAnnotator on a single node (e.g., a laptop with GPU support).
#### 1.1.1. Prerequisites
Ensure the following prerequisites are met on your machine:
- [Docker](https://docs.docker.com/get-docker/) Install Docker desktop for Windows, MacOS or Linux. For Linux, you can alternatively install [docker engine](https://docs.docker.com/engine/install/).
- [NVIDIA Driver](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

#### Installation Steps
1. Install Ray
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install ray~=2.49.1
    ```

2. Run QuickAnnotator using ray up
    ```bash
    ray up deployment/local_cluster_config.yaml -vy
    ```

## 2. For Developers
### 2.1. Volumes


### 2.2. Database


### 2.3. Container
1. Clone the QuickAnnotator repository and checkout the v2.0 branch:
    ```bash
    git clone https://github.com/choosehappy/QuickAnnotator.git
    cd QuickAnnotator
    git checkout v2.0
    ```

2. Within VS Code, open the cloned repository and click on the "Reopen in Container" button to build the devcontainer. This will create a docker container with all the necessary dependencies to run QuickAnnotator.
![image](https://github.com/user-attachments/assets/b776577f-a4c2-4eb8-858c-c603ac20cc6d)


## 3. Usage
1. Connect to a Ray cluster. Ray is used to run operations which require asyncronous processing. There are three ways to connect to a Ray cluster:
    - **Default**: By default QA will initialize a local Ray cluster within the docker container. 
        - Note: The default ray cluster does not host the Ray dashboard.
    - **Manual local cluster**: Run the following command to start a Ray cluster with the Ray dashboard:
        ```bash
        ray start --head --dashboard-host 0.0.0.0
        ```
    - **Pre-existing cluster**: If you would like QA to connect to an existing Ray cluster, use the `--cluster_address` argument.

2. Once the devcontainer is built, you can run the following command to start the QuickAnnotator server:
    ```
    (venv) root@e4392ecdd8ef:/opt/QuickAnnotator# quickannotator
    * Serving Flask app '__main__'
    * Debug mode: on
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
    * Running on all addresses (0.0.0.0)
    * Running on http://127.0.0.1:5000
    * Running on http://172.17.0.2:5000
    Press CTRL+C to quit
    * Restarting with stat
    * Debugger is active!
    * Debugger PIN: 581-630-257
    ``` 

3. Then in a second terminal, run the QuickAnnotator client:
    ```
    (venv) root@e4392ecdd8ef:/opt/QuickAnnotator# cd quickannotator/client
    (venv) root@e4392ecdd8ef:/opt/QuickAnnotator/quickannotator/client# npm run dev -- --host 0.0.0.0

    > client@0.0.0 dev
    > vite --host 0.0.0.0


    VITE v5.4.8  ready in 595 ms

    ➜  Local:   http://localhost:5173/
    ➜  Network: http://172.17.0.2:5173/
    ➜  press h + enter to show help
    ```

5. Use the following URLs:
    1. OpenAPI 3.0 documentation: [http://172.17.0.2:5000/api/v1]()
    2. Client: [http://172.17.0.2:5173/]()

# Logs
Logs are stored within the QuickAnnotator database and may be visualized using Grafana. The following instructions detail how to set up Grafana to connect to a sqlite database.

1. Run the Grafana docker container
    > Note: The following command assumes your sqlite database is contained in the base directory of the qadb_data volume.

    ```bash
    docker run -d \
    --name=grafana \
    -p 3000:3000 \
    -v qadb_data:/var/lib/grafana/sqlite \
    --network quickannotator-net \
    grafana/grafana 
    ```

2. If working with sqlite, install the sqlite datasource plugin within the grafana container.
    ```bash
    docker exec -it grafana grafana-cli plugins install frser-sqlite-datasource
    docker restart grafana
    ```

3. Set up the datasource within Grafana [http://localhost:3000/connections/datasources](). 
    - If you have to log in, use the default grafana credentials:
        - Username: admin
        - Password: admin
    - If you are adding a postgres datasource, set TSL/SSL mode to "disable".


4. Open the grafana import page [http://localhost:3000/dashboard/import]()

5. Drop a dashboard configuration file (e.g., [logs_sqlite.json](./quickannotator/grafana/logs_sqlite.json)) into the upload box and click "Import".
    > Note: Dashboard configuration files are located in the `quickannotator/grafana` directory. 

