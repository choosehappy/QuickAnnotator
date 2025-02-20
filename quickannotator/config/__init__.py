import configparser
import sys

# initialize a new config file:
config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

config.read("quickannotator/config/config.ini")

def get_database_uri():
  if "pytest" in sys.modules:
    return config.get('sqlalchemy', 'test_database_uri', fallback='sqlite:///:memory:')
  else:
    return config.get('sqlalchemy', 'database_uri', fallback='sqlite:////opt/QuickAnnotator/quickannotator/instance/quickannotator.db')

def get_database_path():
  return config.get('sqlalchemy', 'database_path', fallback='quickannotator/instance')

def get_ray_dashboard_host():
  return config.get('ray', 'dashboard_host', fallback='0.0.0.0')

def get_ray_dashboard_port():
  return config.getint('ray', 'dashboard_port', fallback=8265)

def get_api_version():
  return config.get('api', 'version', fallback='v1')