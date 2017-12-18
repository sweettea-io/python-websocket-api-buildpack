import os
import importlib
import yaml
from flask import Flask, request
from flask_restplus import Api, Resource


def get_envs():
  # {key: <is_param>}
  required_envs = {
    'AWS_ACCESS_KEY_ID': False,
    'AWS_SECRET_ACCESS_KEY': False,
    'AWS_REGION_NAME': False,
    'S3_BUCKET_NAME': True,
    'DATASET_DB_URL': False,
    'DATASET_TABLE_NAME': False,
    'PREDICTION': True,
    'PREDICTION_UID': False,
    'CLIENT_ID': False,
    'CLIENT_SECRET': False
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
  predict_mod_str, predict_func_str = config.get('predict').split(':')

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


def get_src_mod(name):
  return importlib.import_module('{}.{}'.format(os.environ.get('PREDICTION_UID'), name))


def perform(prediction=None, s3_bucket_name=None):
  # Get refs to the modules inside our src directory
  model_fetcher = get_src_mod('model_fetcher')
  definitions = get_src_mod('definitions')

  # Read the config file in the project
  config_path = getattr(definitions, 'config_path')
  config = read_config(config_path)

  # Get ref to the exported predict method
  predict_method = get_predict_method(config)

  # # Fetch the latest model from S3
  model_path = config.get('model')

  if '.' in model_path:
    model_file_type = model_path.split('.').pop()
    cloud_path = prediction + '.' + model_file_type
  else:
    cloud_path = prediction

  save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), model_path))

  model_fetcher.fetch(cloud_path=cloud_path,
                      bucket=s3_bucket_name,
                      save_to=save_path)

  return predict_method


def client_valid(body, headers):
  return body.get('client_id') == os.environ.get('CLIENT_ID') and \
         headers.get('TensorCI-Api-Secret') == os.environ.get('CLIENT_SECRET')


params = get_envs()
predict = perform(**params)

app = Flask(__name__)
api = Api(version='0.0.1', title='API')
namespace = api.namespace('api')

dataset_db = get_src_mod('dataset_db')


@namespace.route('/predict')
class Predict(Resource):
  def post(self):
    # Get payload
    try:
      payload = api.payload or {}
    except BaseException:
      payload = {}

    # Ensure valid client id and secret
    if not client_valid(payload, request.headers):
      return {'ok': False, 'error': 'unauthorized'}, 401

    # Get prediction
    try:
      prediction = predict(payload)
    except BaseException as e:
      print('Error making prediction: {}'.format(e))
      return {'ok': False, 'error': 'prediction_error'}, 500

    return prediction, 200


@namespace.route('/dataset')
class Predict(Resource):
  def put(self):
    try:
      # Parse payload
      payload = api.payload or {}
    except BaseException:
      payload = {}

    # Ensure valid client id and secret
    if not client_valid(payload, request.headers):
      return {'ok': False, 'error': 'unauthorized'}, 401

    # Ensure new records were even provided
    records = payload.get('records') or []

    if not records:
      return {'ok': False, 'error': 'no_records_provided'}, 500

    # Get the JSON data schema for the dataset table
    table_name = os.environ.get('DATASET_TABLE_NAME')
    dataset_schema = dataset_db.data_schema(table_name)

    if not dataset_schema:
      return {'ok': False, 'error': 'empty_dataset'}

    dataset_schema = set(dataset_schema)

    # Validate the schema of the provided records matches that of the dataset
    for r in records:
      rset = set(r)

      if rset != dataset_schema:
        print('Invalid data schema when updating dataset.\nActual: {}\nExpected: {}'.format(rset, dataset_schema))
        return {'ok': False, 'error': 'invalid_data_schema'}, 500

    # Insert the new records (TODO: Batch this)
    dataset_db.populate_records(records, table=table_name)

    return {'ok': True, 'message': 'Successfully updated dataset'}, 200


api.init_app(app)


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 80))
  app.run(host='0.0.0.0', port=port, debug=True)