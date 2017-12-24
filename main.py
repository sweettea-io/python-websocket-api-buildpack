import os
import importlib
import yaml
from flask import Flask, request
from flask_restplus import Api, Resource


def validate_envs():
  required_envs = [
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'AWS_REGION_NAME',
    'S3_BUCKET_NAME',
    'DATASET_DB_URL',
    'DATASET_TABLE_NAME',
    'PREDICTION',
    'PREDICTION_UID',
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
  return importlib.import_module('{}.{}'.format(os.environ.get('PREDICTION_UID'), name))


def validate_client(body, headers):
  return body.get('client_id') == os.environ.get('CLIENT_ID') and \
         headers.get('TensorCI-Api-Secret') == os.environ.get('CLIENT_SECRET')


def validate_core(headers):
  return headers.get('TensorCI-Internal-Msg-Token') != os.environ.get('INTERNAL_MSG_TOKEN')


def define_routes(api, namespace, 
               predict_method=None, reload_model_method=None, 
               model_fetcher=None, model_path=None):

  # Get predictions
  @namespace.route('/predict')
  class Prediction(Resource):

    def post(self):
      try:
        payload = api.payload or {}
      except BaseException:
        payload = {}

      if not validate_client(payload, request.headers):
        return {'ok': False, 'error': 'unauthorized'}, 401

      try:
        result = predict_method(payload)
      except BaseException as e:
        print('Error making prediction: {}'.format(e))
        return {'ok': False, 'error': 'prediction_error'}, 500

      return {'ok': True, 'prediction': result}, 200

  
  # Update the dataset
  @namespace.route('/dataset')
  class Dataset(Resource):

    def put(self):
      try:
        payload = api.payload or {}
      except BaseException:
        payload = {}

      if not validate_client(payload, request.headers):
        return {'ok': False, 'error': 'unauthorized'}, 401

      # Ensure new records were provided
      records = payload.get('records') or []

      if not records:
        return {'ok': False, 'error': 'no_records_provided'}, 500

      # Get the JSON data schema for the dataset table
      table_name = os.environ.get('DATASET_TABLE_NAME')
      dataset_schema = dataset_db.data_schema(table_name)

      if not dataset_schema:
        return {'ok': False, 'error': 'empty_dataset'}

      # Validate the schema of the provided records matches that of the dataset
      for r in records:
        rset = set(r)

        if rset != dataset_schema:
          print('Invalid data schema when updating dataset.\nActual: {}\nExpected: {}'.format(rset, dataset_schema))
          return {'ok': False, 'error': 'invalid_data_schema'}, 500

      # Insert the new records
      dataset_db.populate_records(records, table=table_name)

      return {'ok': True, 'message': 'Successfully updated dataset'}, 200

  if reload_model_method:
    # Notification to fetch the latest model
    @namespace.route('/model')
    class Model(Resource):
  
      def put(self):
        if not validate_core(request.headers):
          return {'ok': False, 'error': 'forbidden'}, 403
  
        try:
          # Update model file with latest from S3
          model_fetcher.download_model(model_path)
        except BaseException as e:
          print('Error fetching latest model with error, {}.'.format(e))
          return {'ok': False, 'error': 'unknown_error'}
  
        # Reload model into project
        try:
          reload_model_method()
        except BaseException as e:
          print('Error reloading model with error, {}.'.format(e))
          return {'ok': False, 'error': 'reload_model_error'}
  
        return {'ok': True}, 200


# Validate required env vars
validate_envs()

# Get exported src modules
dataset_db = get_src_mod('dataset_db')
definitions = get_src_mod('definitions')
model_fetcher = get_src_mod('model_fetcher')

# Read the project's config file
config = read_config(definitions.config_path)

# Get exported config file info ('predict', 'reload_model', 'model')
predict = get_exported_method(config, key='predict')
reload_model = None

if 'reload_model' in config:
  reload_model = get_exported_method(config, key='reload_model')

model_path = config.get('model')

# Fetch the latest model file from S3
model_fetcher.download_model(model_path)

# Create Flask app and API
app = Flask(__name__)
api = Api(version='0.0.1', title='API')
namespace = api.namespace('api')

# Define the API's routes
define_routes(api, namespace,
              predict_method=predict,
              reload_model_method=reload_model,
              model_fetcher=model_fetcher,
              model_path=model_path)

# Attach Flask app to the API
api.init_app(app)

# app will be imported by uwsgi on prod


# Run built-in Flask server on dev
if __name__ == '__main__':
  port = int(os.environ.get('PORT', 80))
  app.run(host='0.0.0.0', port=port, debug=True)