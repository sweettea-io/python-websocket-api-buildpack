import os
import boto3
import file_helper


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

  client.download_file(bucket, cloud_path, abs_model_path)

  if ext == archive:
    file_helper.extract_in_place(abs_model_path)