import configparser
import sys
import os

# initialize a new config file:
config = configparser.ConfigParser()

config.read(os.path.join(os.path.dirname(__file__), "config.ini"))

def get_database_uri():
  if "pytest" in sys.modules:
    return config.get('sqlalchemy', 'test_database_uri', fallback='sqlite:///:memory:')
  else:
    postgres_uri = f"postgresql+psycopg2://{get_postgres_username()}:{get_postgres_password()}@{get_postgres_host()}:{get_postgres_port()}/{get_postgres_db()}"
    return postgres_uri
  
def get_postgres_host():
    return os.environ.get('POSTGRES_HOST', 'qa_postgis')

def get_postgres_port():
    return config.getint('sqlalchemy', 'postgres_port', fallback=5432)

def get_postgres_username():
    return config.get('sqlalchemy', 'postgres_username', fallback='admin')

def get_postgres_password():
    return config.get('sqlalchemy', 'postgres_password', fallback='admin')

def get_postgres_db():
    return config.get('sqlalchemy', 'postgres_db', fallback='qa_postgis_db')

def get_database_path():
  return config.get('sqlalchemy', 'database_path', fallback='quickannotator/instance')

def get_ray_dashboard_host():
  return config.get('ray', 'dashboard_host', fallback='0.0.0.0')

def get_ray_dashboard_port():
  return config.getint('ray', 'dashboard_port', fallback=8265)

def get_api_version():
  return config.get('api', 'version', fallback='v1')

def get_grafana_host():
    return config.get('grafana', 'host', fallback='http://grafana:3000')

def get_grafana_username():
    return config.get('grafana', 'username', fallback='admin')

def get_grafana_password():
    return config.get('grafana', 'password', fallback='admin')
