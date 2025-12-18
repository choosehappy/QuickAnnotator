# Developer Guide

## Connect to the Postgres Database
### Via URL
The URL to connect to the QA database depends on whether you are connecting from inside the Docker network or from your host machine.
- External connection URL: `jdbc:postgresql://localhost:5432/qa_postgis_db`
- Internal connection URL: `jdbc:postgresql://qa_postgis:5432/qa_postgis_db`

### Parameters
The following parameters can be used to connect to the Postgres database from a client (e.g., DataGrip):

| **Parameter** | **Value**                              |
|---------------|----------------------------------------|
| **Host**      | `localhost` (or `qa_postgis` if connecting from within Docker) |
| **Port**      | `5432` (default Postgres port)         |
| **Database**  | `qa_postgis_db`                        |
| **User**      | `admin`                                |
| **Password**  | `admin`                                |


