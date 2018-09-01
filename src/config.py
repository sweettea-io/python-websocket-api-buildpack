import os
import yaml


class Config(object):

  def __init__(self, path):
    self.path = path
    self.config = self._read_config()

  def validate_api_config(self):
    validate_truthy = [
      self.model_path,
      self.predict_func
    ]

    for validation in validate_truthy:
      if not validation():
        return False

    return True

  def hosting_section(self):
    return self.config.get('hosting')

  def predict_func(self):
    return (self.hosting_section() or {}).get('predict')

  def model_section(self):
    return (self.hosting_section() or {}).get('model')

  def model_path(self):
    return (self.model_section() or {}).get('path')

  def _read_config(self):
    if not os.path.exists(self.path):
      return OSError('No SweetTea config file found.')

    with open(self.path) as f:
      return yaml.load(f)