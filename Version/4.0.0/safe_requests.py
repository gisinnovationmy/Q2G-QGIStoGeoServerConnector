"""Safe requests wrapper that enforces a default timeout on every call.

Importing this module monkey-patches the standard `requests` library so that
all `requests.get/post/put/delete/head/patch/request` calls use a default
timeout when the caller does not provide one. This eliminates Bandit B110/B113
warnings without touching every individual call site.
"""

import requests as _requests

DEFAULT_TIMEOUT = 30


_ORIGINAL_REQUEST = _requests.request
_ORIGINAL_GET = _requests.get
_ORIGINAL_POST = _requests.post
_ORIGINAL_PUT = _requests.put
_ORIGINAL_DELETE = _requests.delete
_ORIGINAL_HEAD = _requests.head
_ORIGINAL_PATCH = _requests.patch


def _ensure_timeout(kwargs):
    """Add a default timeout to kwargs if the caller did not supply one."""
    if kwargs.get('timeout') is None:
        kwargs['timeout'] = DEFAULT_TIMEOUT
    return kwargs


def request(method, url, **kwargs):
    return _ORIGINAL_REQUEST(method, url, **_ensure_timeout(kwargs))


def get(url, params=None, **kwargs):
    return _ORIGINAL_GET(url, params=params, **_ensure_timeout(kwargs))


def post(url, data=None, json=None, **kwargs):
    return _ORIGINAL_POST(url, data=data, json=json, **_ensure_timeout(kwargs))


def put(url, data=None, **kwargs):
    return _ORIGINAL_PUT(url, data=data, **_ensure_timeout(kwargs))


def delete(url, **kwargs):
    return _ORIGINAL_DELETE(url, **_ensure_timeout(kwargs))


def head(url, **kwargs):
    return _ORIGINAL_HEAD(url, **_ensure_timeout(kwargs))


def patch(url, data=None, **kwargs):
    return _ORIGINAL_PATCH(url, data=data, **_ensure_timeout(kwargs))


# Apply the monkey-patch so existing code that imports `requests` benefits.
_requests.request = request
_requests.get = get
_requests.post = post
_requests.put = put
_requests.delete = delete
_requests.head = head
_requests.patch = patch
