import configparser

# initialize a new config file:
config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

config.read("quickannotator/config/config.ini")

def get_database_uri():
  return config.get('sqlalchemy', 'database_uri', fallback='sqlite:///quickannotator.db')

def get_database_path():
  return config.get('sqlalchemy', 'database_path', fallback='quickannotator/instance')