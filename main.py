import asyncio
import importlib
import os
import websockets


def get_internal_modules(env_prefix):
  # Construct key for project uid env var.
  project_uid_key = '{}PROJECT_UID'.format(env_prefix)
  project_uid = os.environ.get(project_uid_key)

  if not project_uid:
    print('{} must be provided as an environment variable in order to run this buildpack.'.format(project_uid_key))
    exit(1)

  try:
    config = get_src_mod(project_uid, 'config')
    definitions = get_src_mod(project_uid, 'definitions')
    envs = get_src_mod(project_uid, 'envs')
    model_fetcher = get_src_mod(project_uid, 'model_fetcher')
    req = get_src_mod(project_uid, 'req')
    responses = get_src_mod(project_uid, 'responses')

    return config, definitions, envs, model_fetcher, req, responses
  except BaseException as e:
    print('Internal module reference failed: {}'.format(e))
    exit(1)


def get_src_mod(parent_mod, name):
  return importlib.import_module('{}.{}'.format(parent_mod, name))


def get_validated_config(config_module, path):
  try:
    cfg = config_module.Config(path)

    if not cfg.validate_api_config():
      raise BaseException('Invalid SweetTea configuration file.')

    return cfg
  except BaseException as e:
    print(e)
    exit(1)


def get_config_func(func_path):
  # Split function path into ['<module_path>', '<function_name>']
  module_path, func_name = func_path.rsplit(':', 1)

  if not module_path:
    print('No module included in config function path: {}.'.format(func_path))
    exit(1)

  # Import module by path.
  mod = importlib.import_module(module_path)

  # Ensure module exists.
  if not mod:
    print('No module to import at destination: {}'.format(module_path))
    exit(1)

  # Ensure function exists on module.
  if not hasattr(mod, func_name):
    print('No function named {} exists on module {}'.format(func_name, module_path))
    exit(1)

  # Return reference to module function.
  return getattr(mod, func_name)


def perform():
  """
  Perform executes the following actions:

    1. Download model from cloud storage
    2. Create websocket server to host model's predictions
  """
  # Get internal environment variable prefix.
  env_prefix = os.environ.get('SWEET_TEA_INTERNAL_ENV_PREFIX', '')

  # Get reference to internal src modules.
  config, definitions, envs, model_fetcher, req, responses = get_internal_modules(env_prefix)

  # Create EnvVars instance from environment variables.
  env_vars = envs.EnvVars(prefix=env_prefix)

  # Create Config instance from SweetTea config file.
  cfg = get_validated_config(config, definitions.config_path)

  # Download model from cloud storage.
  model_fetcher.download_model(cloud_storage_url=env_vars.MODEL_STORAGE_URL,
                               cloud_model_path=env_vars.MODEL_STORAGE_FILE_PATH,
                               rel_local_model_path=cfg.model_path(),
                               region_name=env_vars.AWS_REGION_NAME,
                               aws_access_key_id=env_vars.AWS_ACCESS_KEY_ID,
                               aws_secret_access_key=env_vars.AWS_SECRET_ACCESS_KEY)

  # Create a RequestManager instance.
  req_manager = req.RequestManager(auth_headers={
    definitions.client_id_header: env_vars.CLIENT_ID,
    definitions.client_secret_header: env_vars.CLIENT_SECRET,
  })

  # Get ref to config functions.
  predict = get_config_func(cfg.predict_func())

  # Register predict function as a request handler.
  req_manager.register_handler('predict', predict)

  # Define function to serve forever.
  async def server(ws):
    await req_manager.handle(ws)

  # Start socket server.
  asyncio.get_event_loop().run_until_complete(websockets.serve(server, definitions.host, definitions.port))
  asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
  perform()
