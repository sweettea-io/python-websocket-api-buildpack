import os
import boto3
from boto3.s3.transfer import TransferConfig, S3Transfer


def fetch(cloud_path=None, bucket=None, save_to=None):
  client = boto3.client('s3', os.environ.get('AWS_REGION_NAME'))
  config = TransferConfig(use_threads=False)
  transfer = S3Transfer(client, config)
  transfer.download_file(bucket, cloud_path, save_to)