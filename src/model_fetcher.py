import os
import boto3
import shutil
from boto3.s3.transfer import TransferConfig, S3Transfer


def download_model(model_path):
  # Construct cloud model path by combining prediction slug
  # with file extension used in provided model_path.
  prediction_slug = os.environ.get('PREDICTION')
  cloud_path = prediction_slug
  tmp_path = 'tmp/model-{}'.format(prediction_slug)

  if '.' in model_path:
    ext = model_path.split('.').pop()
    cloud_path += '.{}'.format(ext)
    tmp_path += '.{}'.format(ext)

  # Construct absolute paths from relative ones
  abs_tmp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', tmp_path))
  abs_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', model_path))

  # Ensure all directories exist in each of our absolute paths
  makedirs(abs_tmp_path)
  makedirs(abs_model_path)

  # Download model file from S3 to abs_tmp_path
  fetch(cloud_path=cloud_path,
        bucket=os.environ.get('S3_BUCKET_NAME'),
        save_to=abs_tmp_path)

  # Replace the active model file with the new one
  shutil.move(abs_tmp_path, abs_model_path)


def fetch(cloud_path=None, bucket=None, save_to=None):
  client = boto3.client('s3', os.environ.get('AWS_REGION_NAME'))
  config = TransferConfig(use_threads=False)
  transfer = S3Transfer(client, config)
  transfer.download_file(bucket, cloud_path, save_to)


def makedirs(filepath):
  comps = filepath.split('/')
  comps.pop()
  dir = '/'.join(comps)
  os.makedirs(dir)