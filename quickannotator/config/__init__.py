import configparser

# initialize a new config file:
config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

def get_database_uri():
  return config.get('sqlalchemy', 'database_uri', fallback='sqlite:///quickannotator.db')