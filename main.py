import os
import importlib
import yaml
from flask import Flask
from flask_restplus import Api, Resource


def get_envs():
  print('Validating envs...')
  env = os.environ

  # Required ENV vars
  required = ['TEAM', 'TEAM_UID', 'PREDICTION', 'PREDICTION_UID']
  missing = [k for k in required if k not in env]

  if missing:
    print('Not starting API. The following env vars not provided: {}'.format(', '.join(missing)))
    exit(1)

  return {k.lower(): env.get(k) for k in required}


def read_config(config_path):
  with open(config_path) as f:
    config = yaml.load(f)

  if type(config) != dict or 'predict' not in config or 'model' not in config:
    print('Not starting API. Invalid config file: {}'.format(config))
    exit(1)

  return config


def get_predict_method(config):
  split_path_info = config.get('predict').split('.')
  predict_func_str = split_path_info.pop()
  predict_mod_str = '.'.join(split_path_info)

  if not predict_mod_str:
    print('No module specified for predicting. Only the function was specified.')
    exit(1)

  predict_mod = importlib.import_module(predict_mod_str)

  if not predict_mod:
    print('No module to import at destination: {}'.format(predict_mod_str))
    exit(1)

  if not hasattr(predict_mod, predict_func_str):
    print('No function named {} exists on module {}'.format(predict_func_str, predict_mod_str))
    exit(1)

  return getattr(predict_mod, predict_func_str)


def get_src_mod(src, name):
  return importlib.import_module('{}.{}'.format(src, name))


def define_endpoints(api, namespace, predict=None):
  @namespace.route('/predict')
  class Predict(Resource):
    def post(self):
      predict(api.payload)
      return '', 200


def perform(team=None, team_uid=None, prediction=None, prediction_uid=None):
  # Get refs to the modules inside our src directory
  model_fetcher = get_src_mod(prediction_uid, 'model_fetcher')
  definitions = get_src_mod(prediction_uid, 'definitions')

  # Read the provided config file
  print('Reading config info...')
  config = read_config(getattr(definitions, 'config_path'))

  # Get ref to the exported predict method
  print('Finding predict method...')
  predict_method = get_predict_method(config)

  # Fetch the latest model from S3
  print('Fetching lastest model from S3...')
  model_fetcher.fetch(config.get('model'), team, team_uid, prediction)

  # Create API
  print('Creating API...')
  app = Flask(__name__)
  api = Api(app=app, version='0.0.1', title='{} api'.format(prediction))
  namespace = api.namespace('api')

  # Force SSL if on prod and that's desired
  if os.environ.get('ENVIRON') == 'prod' and os.environ.get('REQUIRE_SSL') == 'true':
    from flask_sslify import SSLify
    SSLify(app)

  # Define endpoints for api
  print('Adding endpoints...')
  define_endpoints(api, namespace, predict=predict_method)

  # Start Flask app
  print('Starting API...')
  port = int(os.environ.get('PORT', 80))
  app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
  params = get_envs()
  perform(**params)