import os
import boto3
import file_helper
import shutil
import threading
from boto3.s3.transfer import TransferConfig, S3Transfer


class ProgressPercentage(object):
  def __init__(self, size, path, move_to, extract=False):
    self.path = path
    self.move_to = move_to
    self.size = size
    self.seen_so_far = 0
    self.lock = threading.Lock()
    self.extract = extract

  def __call__(self, bytes_amount):
    with self.lock:
      self.seen_so_far += bytes_amount
      percentage = self.seen_so_far / self.size

      if percentage == 1:
        # Replace the active model file with the new one
        shutil.move(self.path, self.move_to)

        # Extract model archive if a it's a dir
        if self.extract:
          file_helper.extract_in_place(self.move_to)


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
  tmp_path = 'tci_tmp/model-{}'.format(cloud_path)

  # Construct absolute paths from relative ones
  abs_tmp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', tmp_path))
  abs_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', save_to))

  # Ensure all directories exist in each of our absolute paths
  file_helper.upsert_parent_dirs(abs_tmp_path)
  file_helper.upsert_parent_dirs(abs_model_path)

  # Download model file from S3 to abs_tmp_path
  bucket = os.environ.get('S3_BUCKET_NAME')

  client = boto3.client('s3')
  config = TransferConfig(use_threads=False)
  transfer = S3Transfer(client, config)
  is_archive = ext == archive

  size = client.head_object(Bucket=bucket, Key=cloud_path).get('ContentLength')

  progress = ProgressPercentage(size, abs_tmp_path, abs_model_path, extract=is_archive)

  transfer.download_file(bucket, cloud_path, abs_tmp_path, callback=progress)
