# QuickAnnotator
Quick Annotator is an open-source digital pathology annotation tool.

# Purpose
Machine learning approaches for segmentation of histologic primitives (e.g., cell nuclei) in digital pathology (DP) Whole Slide Images (WSI) require large numbers of exemplars. Unfortunately, annotating each object is laborious and often intractable even in moderately sized cohorts. The purpose of QuickAnnotator is to rapidly bootstrap annotation creation for digital pathology projects. 

QuickAnnotator leverages active learning to suggest annotations which the user may accept as they annotate.

# Installation
## For Developers
### Development Environment
- VS Code with the following extensions:
    - `ms-azuretools.vscode-docker`
    - `ms-vscode-remote.remote-containers`
- Docker
- Access to example data.

### Volumes
Create docker volumes to store your data persistently:
```bash
docker volume create qadb_data  # Will store the database
docker volume create qa_data    # Will store example WSIs
```


### Container
1. Clone the QuickAnnotator repository and checkout the v2.0 branch:
    ```bash
    git clone https://github.com/choosehappy/QuickAnnotator.git
    cd QuickAnnotator
    git checkout v2.0
    ```

2. Within VS Code, open the cloned repository and click on the "Reopen in Container" button to build the devcontainer. This will create a docker container with all the necessary dependencies to run QuickAnnotator.
![image](https://github.com/user-attachments/assets/b776577f-a4c2-4eb8-858c-c603ac20cc6d)


### Usage
1. Once the devcontainer is built, you can run the following command to start the QuickAnnotator server:
    ```
    (venv) root@e4392ecdd8ef:/opt/QuickAnnotator# python3 -m quickannotator
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

2. **(Optional)** Upload example data to QuickAnnotator
    1. Download the `test_ndpi` folder (request access from jackson.jacobs@emory.edu) and copy it to the `qa_data` volume.
    1. Run the `populate_db.ipynb` notebook.


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

4. Use the following URLs:
    1. OpenAPI 3.0 documentation: [http://172.17.0.2:5000/api/v1]()
    2. Client: [http://172.17.0.2:5173/]()

