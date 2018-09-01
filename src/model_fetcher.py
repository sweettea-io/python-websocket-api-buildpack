import os
import boto3
from . import file_util
from .definitions import model_archive_format
from boto3.s3.transfer import TransferConfig, S3Transfer


def download_model(path):
  # Check if the specified model path is a directory
  is_dir = path.endswith('/') or ('.' not in path.split('/').pop())

  if is_dir:
    # If desired model path is a directory, the path will be a .zip of that path
    save_to = '.'.join((path.rstrip('/'), model_archive_format))
    ext = model_archive_format
  else:
    save_to = path
    ext = path.split('/').pop().split('.').pop()

  repo_slug = os.environ.get('REPO_SLUG')
  cloud_path = '.'.join((repo_slug, ext))  # S3 file key

  # Construct absolute paths from relative ones
  abs_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', save_to))

  # Ensure all directories exist in each of our absolute paths
  file_util.upsert_parent_dirs(abs_model_path)

  # Download model file from S3 to abs_tmp_path
  bucket = os.environ.get('S3_BUCKET_NAME')

  client = boto3.client('s3')
  config = TransferConfig(use_threads=False)
  transfer = S3Transfer(client, config)

  transfer.download_file(bucket, cloud_path, abs_model_path)

  if ext == model_archive_format:
    file_util.extract_in_place(abs_model_path)