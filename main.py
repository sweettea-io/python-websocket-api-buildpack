import os
import importlib
import redis
from time import sleep
import yaml
from restful_redis.server import RestfulRedisServer


def validate_envs():
  required_envs = [
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'AWS_REGION_NAME',
    'S3_BUCKET_NAME',
    'DATASET_DB_URL',
    'REPO_SLUG',
    'REPO_UID',
    'DOMAIN',
    'CLIENT_ID',
    'CLIENT_SECRET',
    'INTERNAL_MSG_TOKEN'
  ]

  missing = [k for k in required_envs if k not in os.environ]

  if missing:
    print('Not starting API. The following env vars not provided: {}'.format(', '.join(missing)))
    exit(1)


def read_config(config_path):
  with open(config_path) as f:
    config = yaml.load(f)

  if type(config) != dict or 'predict' not in config or 'model' not in config:
    print('Not starting API. Invalid config file: {}'.format(config))
    exit(1)

  return config


def get_exported_method(config, key=None):
  module_str, function_str = config.get(key).split(':')

  if not module_str:
    print('No module specified for config method({}={}).'.format(key, config.get(key)))
    exit(1)

  module = importlib.import_module(module_str)

  if not module:
    print('No module to import at destination: {}'.format(module_str))
    exit(1)

  if not hasattr(module, function_str):
    print('No function named {} exists on module {}'.format(function_str, module_str))
    exit(1)

  return getattr(module, function_str)


def get_src_mod(name):
  return importlib.import_module('{}.{}'.format(os.environ.get('REPO_UID'), name))


def create_socket_url():
  username = os.environ['CLIENT_ID']
  pw = os.environ['CLIENT_SECRET']
  host = os.environ['DOMAIN']

  # return 'redis://{}:{}@{}:6379'.format(username, pw, host)
  return 'redis://{}:6379'.format(host)


def ensure_connected(server):
  connected = attempt_connection(server)

  if not connected:
    return ensure_connected()

  return True


def attempt_connection(server):
  try:
    server.redis.blpop('connection_test', 1)
  except redis.exceptions.ConnectionError:
    return False

  return True


def perform():
  # Ensure all required environment variables exist
  validate_envs()

  # Get exported internal src modules
  definitions = get_src_mod('definitions')
  model_fetcher = get_src_mod('model_fetcher')

  # Read the project's config file
  config = read_config(definitions.config_path)

  # Get exported config methods
  predict = get_exported_method(config, key='predict')

  # Download trained model from S3
  model_fetcher.download_model(config.get('model'))

  # Create socket server
  socket_url = create_socket_url()
  server = RestfulRedisServer(url=socket_url)

  # Wait for socket to connect
  ensure_connected(server)

  # Register socket handlers
  server.register_handler('predict', predict)

  # Start socket server (run forever)
  server.run()


if __name__ == '__main__':
  perform()