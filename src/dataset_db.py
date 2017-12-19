import os
import json
from sqlalchemy import create_engine

dataset_db_url = os.environ.get('DATASET_DB_URL')

try:
  engine = create_engine(dataset_db_url)
except BaseException as e:
  engine = None
  print('Error connecting to Dataset DB url {} -- {}'.format(dataset_db_url, e))


# TODO: Batch insert
def populate_records(records, table=None):
  for r in records:
    engine.execute('INSERT INTO {} (data) VALUES (\'{}\');'.format(table, json.dumps(r)))


def data_schema(table):
  result = [r for r in engine.execute('SELECT data from {} LIMIT 1;'.format(table))]

  try:
    return {k: True for k in result[0][0].keys()}
  except:
    return {}