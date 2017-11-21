import os
import importlib
import yaml
from flask import Flask
from flask_restplus import Api, Resource


def get_envs():
  # {key: <is_param>}
  required_envs = {
    'AWS_ACCESS_KEY_ID': False,
    'AWS_SECRET_ACCESS_KEY': False,
    'AWS_REGION_NAME': False,
    'DATASET_DB_URL': False,
    'TEAM': True,
    'TEAM_UID': True,
    'PREDICTION': True,
    'PREDICTION_UID': True
  }

  missing = [k for k in required_envs if k not in os.environ]

  if missing:
    print('Not starting API. The following env vars not provided: {}'.format(', '.join(missing)))
    exit(1)

  # Only return the envs that we need as params
  return {k.lower(): os.environ.get(k) for k in required_envs if required_envs[k]}


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
      try:
        prediction = predict(api.payload or {})
      except BaseException as e:
        print('Error making prediction: {}'.format(e))
        return '', 500

      return prediction, 200


def perform(team=None, team_uid=None, prediction=None, prediction_uid=None):
  # We need to use importlib.import_module to access our src/ files since src/ will
  # be renamed to <prediction_uid>/ to avoid conflicts with user's project files

  # Get refs to the modules inside our src directory
  model_fetcher = get_src_mod(prediction_uid, 'model_fetcher')
  definitions = get_src_mod(prediction_uid, 'definitions')

  # Read the config file in the project
  config_path = getattr(definitions, 'config_path')
  config = read_config(config_path)

  # Get ref to the exported predict method
  predict_method = get_predict_method(config)

  # Fetch the latest model from S3
  model_fetcher.fetch(config.get('model'), team, team_uid, prediction)

  # Create API
  app = Flask(__name__)
  api = Api(app=app, version='0.0.1', title='{} API'.format(prediction))
  namespace = api.namespace('api')

  # Force SSL if on prod and requested
  if os.environ.get('ENVIRON') == 'prod' and os.environ.get('REQUIRE_SSL') == 'true':
    from flask_sslify import SSLify
    SSLify(app)

  # Define endpoints for api
  define_endpoints(api, namespace, predict=predict_method)

  # Start Flask app
  port = int(os.environ.get('PORT', 80))
  app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
  params = get_envs()
  perform(**params)