import json
from .responses import *
from websockets.exceptions import ConnectionClosed


class RequestManager(object):

  def __init__(self, handlers=None, auth_headers=None, require_auth=False):
    self.handlers = handlers or {}
    self.auth_headers = auth_headers or {}
    self.require_auth = require_auth

  def register_handler(self, name, handler):
    self.handlers[name] = handler

  async def handle(self, ws, path):
    # Parse request headers.
    headers = self._parse_headers(ws)

    # Check if request is authed.
    authed = self._is_authed_req(headers)

    # Return error message if unauthed and auth is required.
    if not authed and self.require_auth:
      await ws.send(json.dumps(UNAUTHORIZED))
      return

    try:
      async for message in ws:
        await self._handle_message(ws, message)
    except ConnectionClosed:
      return

  async def _handle_message(self, ws, message):
    # Attempt to parse JSON request message.
    try:
      payload = json.loads(message) or {}
    except:
      await ws.send(json.dumps(INVALID_JSON_PAYLOAD))
      return

    # Find handler to call from map of registered handlers.
    handler = self.handlers.get(payload.get('handler'))

    if not handler:
      await ws.send(json.dumps(UNSUPPORTED_HANDLER))
      return

    try:
      # Call the handler function, passing in the request data.
      resp_data = handler(payload.get('data'))

      resp_payload = {
        'ok': True,
        'data': resp_data
      }
    except BaseException:
      resp_payload = CONFIG_FUNC_CALL_FAILED

    await ws.send(json.dumps(resp_payload))

  def _parse_headers(self, ws):
    return dict(ws.request_headers.items()) or {}

  def _is_authed_req(self, headers):
    for k, v in self.auth_headers.items():
      if headers.get(k) != v:
        return False

    return True
