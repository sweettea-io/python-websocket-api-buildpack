import os
from redis import StrictRedis

redis_url = os.environ.get('REDIS_URL')

if redis_url:
  redis = StrictRedis.from_url(url=redis_url)
else:
  redis = None


def log_request(repo_uid):
  key = 'request-count:{}'.format(repo_uid)

  try:
    curr_req_count = int(redis.get(key))
  except:
    curr_req_count = 0

  new_req_count = curr_req_count + 1

  redis.set(key, str(new_req_count))