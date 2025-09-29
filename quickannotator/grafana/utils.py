from grafana_client import GrafanaApi
from quickannotator import constants
import quickannotator.config as config
from quickannotator.db.logging import LoggingManager
import json



class GrafanaClient:
    def __init__(self, base_url, username, password):
        self.api = GrafanaApi.from_url(url=base_url, credential=(username, password))
        self.logger = LoggingManager.init_logger(constants.LoggerNames.FLASK.value)


    def add_postgres_datasource(self, host, port, db, username, password) -> str:
        name = "PostgreSQL"
        try:    # NOTE: api client does not have a datasource search method, so we just have to try getting the datasource by name.
            existing_datasource = self.api.datasource.get_datasource_by_name(name)
            self.logger.info(f"Grafana datasource '{name}' already exists. Skipping creation.")
            return existing_datasource["uid"]
        except Exception as e:
            self.logger.error(f"Datasource does not exist. Creating datasource...")

        datasource = {
            "name": name,
            "type": "postgres",
            "access": "proxy",
            "url": f"{host}:{port}",
            "database": db,
            "user": username,
            "jsonData": {
                "sslmode": "disable",
            },
            "secureJsonData": {
                "password": password
            }
        }

        resp = self.api.datasource.create_datasource(datasource)
        self.logger.info(f"Grafana datasource '{name}' created successfully.")
        return resp['datasource']["uid"]


    def add_logs_dashboard(self, path, datasource_uid) -> str:
        with open(path, "r") as f:
            dashboard = json.load(f)
            # Force the creation of a new dashboard
            dashboard['id'] = None
            dashboard['uid'] = None
            dashboard['panels'][0]['datasource']["uid"] = datasource_uid
            title = dashboard['title']
            if self.api.search.search_dashboards(title):
                self.logger.info(f"Dashboard '{title}' already exists. Skipping creation.")
                return
            
            config = {
                "dashboard": dashboard,
                "overwrite": False
            }

            new_dashboard = self.api.dashboard.update_dashboard(dashboard=config)
            self.logger.info(f"Dashboard '{title}' created successfully.")
            return new_dashboard["uid"]


def initialize_grafana():
    client = GrafanaClient(
        base_url=config.get_grafana_host(),
        username=config.get_grafana_username(),
        password=config.get_grafana_password()
    )

    uid = client.add_postgres_datasource(
        host=config.get_postgres_host(),
        port=config.get_postgres_port(),
        db=config.get_postgres_db(),
        username=config.get_postgres_username(),
        password=config.get_postgres_password()
    )

    client.add_logs_dashboard(
        path=config.get_logs_dashboard_config_path(),
        datasource_uid=uid
    )