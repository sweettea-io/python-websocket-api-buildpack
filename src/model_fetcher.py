import boto3

s3 = boto3.resource('s3')


def fetch(local_path, team, team_uid, prediction):
  if '.' in local_path:
    file_type = local_path.split('.').pop()
    cloud_path = prediction + '.' + file_type
  else:
    cloud_path = prediction

  bucket_name = '{}-{}'.format(team, team_uid)
  bucket = s3.Bucket(bucket_name)

  bucket.download_file(cloud_path, local_path)