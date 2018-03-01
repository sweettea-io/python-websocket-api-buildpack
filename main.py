import asyncio
import importlib
import json
import os
import websockets
import yaml


def read_config(config_path):
  with open(config_path) as f:
    config = yaml.load(f)

  if type(config) != dict or 'predict' not in config or 'model' not in config:
    print('Not starting API. Invalid config file: {}'.format(config))
    exit(1)

  return config


def get_exported_method(config, key=None):
  module_str, function_str = config.get(key).split(':')

  if not module_str:
    print('No module specified for config method({}={}).'.format(key, config.get(key)))
    exit(1)

  module = importlib.import_module(module_str)

  if not module:
    print('No module to import at destination: {}'.format(module_str))
    exit(1)

  if not hasattr(module, function_str):
    print('No function named {} exists on module {}'.format(function_str, module_str))
    exit(1)

  return getattr(module, function_str)


def get_src_mod(name):
  return importlib.import_module('.'.join((os.environ.get('REPO_UID'), name)))


def auth_client(headers, defs, envs):
  return headers.get(defs.client_id_header) == envs.CLIENT_ID and \
         headers.get(defs.client_secret_header) == envs.CLIENT_SECRET


def perform():
  # Get internal src modules
  envs = get_src_mod('envs').envs
  definitions = get_src_mod('definitions')
  responses = get_src_mod('responses')
  model_fetcher = get_src_mod('model_fetcher')

  # Read the project's config file.
  config = read_config(definitions.config_path)

  # Get exported config methods.
  predict = get_exported_method(config, key='predict')

  # Download the trained model from S3.
  model_fetcher.download_model(config.get('model'))

  # Register socket message handlers.
  handlers = {
    'predict': predict
  }

  async def server(websocket, path):
    headers = dict(websocket.request_headers.items()) or {}
    authed = auth_client(headers, definitions, envs)

    if not authed:
      await websocket.send(json.dumps(responses.UNAUTHORIZED))
      return

    async for message in websocket:
      try:
        payload = json.loads(message) or {}
      except:
        await websocket.send(json.dumps(responses.INVALID_JSON_PAYLOAD))
        return

      handler_name = payload.get('handler')
      req_data = payload.get('data')

      if not handler_name:
        await websocket.send(json.dumps(responses.UNSUPPORTED_HANDLER))
        return

      handler = handlers.get(handler_name)

      if not handler:
        await websocket.send(json.dumps(responses.UNSUPPORTED_HANDLER))
        return

      try:
        # Call the handler method passing in the request data
        resp_data = handler(req_data)

        resp_payload = {
          'ok': True,
          'data': resp_data
        }
      except BaseException:
        resp_payload = responses.EXPORTED_FUNC_CALL_FAILED

      await websocket.send(json.dumps(resp_payload))

  # Start socket server (run forever)
  asyncio.get_event_loop().run_until_complete(
    websockets.serve(server, host=definitions.host, port=definitions.port, ssl=True))

  asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
  perform()