import boto3
import os
from . import file_util
from .definitions import model_archive_format, base_dir
from boto3.s3.transfer import TransferConfig, S3Transfer
from urllib.parse import urlparse


def download_model(cloud_storage_url=None, cloud_model_path=None, rel_local_model_path=None):
  # Configure S3 Bucket before downloading model.
  bucket_name = urlparse(cloud_storage_url).netloc
  transfer = S3Transfer(boto3.client('s3'), TransferConfig(use_threads=False))

  # Get exact cloud and local model paths for download.
  ext, cloud_path, dest = get_paths_for_download(cloud_model_path, rel_local_model_path)

  # Upsert parent dirs of local model before downloading.
  file_util.upsert_parent_dirs(dest)

  # Download model file from S3.
  transfer.download_file(bucket_name, cloud_path, dest)

  # If model file is an archive, extract it in place.
  if ext == model_archive_format:
    file_util.extract_in_place(dest)


def get_paths_for_download(cloud_model_path, rel_local_model_path):
  # Check if the specified model path is a directory.
  is_dir = rel_local_model_path.endswith('/') or ('.' not in rel_local_model_path.split('/').pop())

  # If desired model destination is a directory, the cloud path will be a .zip of that path.
  if is_dir:
    rel_dest = '.'.join((rel_local_model_path.rstrip('/'), model_archive_format))
    ext = model_archive_format
  else:
    rel_dest = rel_local_model_path
    ext = rel_local_model_path.split('/').pop().split('.').pop()

  cloud_path = cloud_model_path

  if ext:
    cloud_path = '.'.join((cloud_path, ext))

  return ext, cloud_path, os.path.join(base_dir, rel_dest)
