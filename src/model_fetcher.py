import os
import boto3
import file_helper
import shutil
from boto3.s3.transfer import TransferConfig, S3Transfer


def download_model(path):
  archive = 'zip'  # All model folders should be downloaded as zip files.

  # Check if the specified model path is a directory
  is_dir = path.endswith('/') or ('.' not in path.split('/').pop())

  if is_dir:
    # If desired model path is a directory, the path will be a .zip of that path
    save_to = '.'.join((path.rstrip('/'), archive))
    ext = archive
  else:
    save_to = path
    ext = path.split('/').pop().split('.').pop()

  repo_slug = os.environ.get('REPO_SLUG')
  cloud_path = '.'.join((repo_slug, ext))  # S3 file key
  tmp_path = 'tmp/model-{}'.format(cloud_path)

  # Construct absolute paths from relative ones
  abs_tmp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', tmp_path))
  abs_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', save_to))

  # Ensure all directories exist in each of our absolute paths
  file_helper.upsert_parent_dirs(abs_tmp_path)
  file_helper.upsert_parent_dirs(abs_model_path)

  # Download model file from S3 to abs_tmp_path
  fetch(cloud_path=cloud_path,
        bucket=os.environ.get('S3_BUCKET_NAME'),
        save_to=abs_tmp_path)

  # Replace the active model file with the new one
  shutil.move(abs_tmp_path, abs_model_path)

  # Extract model archive if a it's a dir
  if ext == archive:
    file_helper.extract_in_place(abs_model_path)


def fetch(cloud_path=None, bucket=None, save_to=None):
  client = boto3.client('s3', os.environ.get('AWS_REGION_NAME'))
  config = TransferConfig(use_threads=False)
  transfer = S3Transfer(client, config)
  transfer.download_file(bucket, cloud_path, save_to)