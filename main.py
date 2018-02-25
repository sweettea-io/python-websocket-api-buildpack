import os
import importlib
import redis
import yaml
from restful_redis.server import RestfulRedisServer
from time import sleep


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


def create_socket_url(envs):
  # return 'redis://{}:{}@{}:6379'.format(envs.CLIENT_ID, envs.CLIENT_SECRET, envs.DOMAIN)
  return 'redis://{}:6379'.format(envs.DOMAIN)


def ensure_connected(server):
  connected = attempt_connection(server)

  if not connected:
    sleep(3)
    return ensure_connected()

  return True


def attempt_connection(server):
  try:
    server.redis.blpop('connection_test', 1)
  except redis.exceptions.ConnectionError:
    return False

  return True


def perform():
  # Get exported internal src modules
  envs = get_src_mod('envs').envs
  definitions = get_src_mod('definitions')
  model_fetcher = get_src_mod('model_fetcher')

  # Read the project's config file
  config = read_config(definitions.config_path)

  # Get exported config methods
  predict = get_exported_method(config, key='predict')

  # Download trained model from S3
  model_fetcher.download_model(config.get('model'))

  # Create socket server
  socket_url = create_socket_url(envs)
  server = RestfulRedisServer(url=socket_url)

  # Wait for socket to connect
  ensure_connected(server)

  # Register socket handlers
  server.register_handler('predict', predict)

  # Start socket server (run forever)
  server.run()


if __name__ == '__main__':
  perform()