import boto3

s3 = boto3.resource('s3')


def fetch(cloud_path=None, bucket=None, save_to=None):
  bucket = s3.Bucket(bucket)
  bucket.download_file(cloud_path, save_to)