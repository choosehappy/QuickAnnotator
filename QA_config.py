import configparser

# initialize a new config file:
config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())

# read the options from disk:
config.read("config.ini")

# display:
print(f'Config sections = {config.sections()}')

def get_database_uri():
  return config.get('sqlalchemy', 'database_uri', fallback='sqlite:///data.db')
