UNAUTHORIZED = {
  'ok': False,
  'status': 401,
  'error': 'unauthorized'
}

INVALID_JSON_PAYLOAD = {
  'ok': False,
  'status': 400,
  'error': 'invalid_json_payload'
}

UNSUPPORTED_HANDLER = {
  'ok': False,
  'status': 400,
  'error': 'handler_not_supported'
}

CONFIG_FUNC_CALL_FAILED = {
  'ok': False,
  'status': 500,
  'error': 'config_func_call_failed'
}