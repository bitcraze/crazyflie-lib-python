---
title: API Service endpoints
page_id: apiservice_endpoints
---

Some devices on a Crazyflie, such as the Camera Deck, have settings and commands of their own. They serve them
through the API Service protocol (`bitcraze.api`), and the Crazyflie makes them available on CRTP port 10, the
API Service bridge. Each such device is an *API Service endpoint*, named by a path such as `deck:bcCam`. Inside an endpoint,
values are named by paths too, such as `stream.mjpeg_quality`.

In the library the endpoints are reached through `cf.apiservice`. The API Service bridge needs a Crazyflie firmware with
CRTP protocol version 14 or later. With an older firmware the list of endpoints is empty.

An example is in [examples/apiservice/apiservice_endpoints.py](https://github.com/bitcraze/crazyflie-lib-python/blob/master/examples/apiservice/apiservice_endpoints.py).
It prints the endpoints and reads or writes a path on one of them.
[examples/apiservice/apiservice_notify.py](https://github.com/bitcraze/crazyflie-lib-python/blob/master/examples/apiservice/apiservice_notify.py)
prints the changes an endpoint reports, see [Change notifications](#change-notifications).

## Usage

```python
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

cflib.crtp.init_drivers()

with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    apiservice = scf.cf.apiservice
    for ep in apiservice.endpoints():
        print(ep.id, ep.path, ep.is_ready())

    cam = apiservice.endpoint('deck:bcCam')
    quality = cam.get_typed('stream.mjpeg_quality')   # TypedValue(type, value)
    print(quality.value)
    cam.set('stream.mjpeg_quality', 80, quality.type)   # ints need their wire type
```

Reading the type first with `get_typed()` lets a script set an integer path without hard-coding its width.

## API

The calls block and raise an exception on failure, with a timeout on every call.

### `cf.apiservice`

| Method | Description |
|--------|-------------|
| `endpoints(timeout=None)` | The list of `ApiserviceEndpoint` of this connection. |
| `endpoint(path, timeout=None)` | The endpoint with this path, for example `'deck:bcCam'`. Raises `UnknownEndpointError`. |
| `info(timeout=None)` | `BridgeInfo(count, catalog_crc, max_in_flight, max_message)`, or `None` when the Crazyflie has no API Service bridge. |
| `default_timeout` | Timeout of every call that does not give one, in seconds. 3 s by default. |

The list of endpoints is read the first time it is needed on a connection, not when connecting, so a script that
does not use API Service endpoints pays nothing. It is kept until the connection ends.

### `ApiserviceEndpoint`

| Member | Description |
|--------|-------------|
| `id`, `path` | Catalog ID and path of the endpoint. |
| `is_ready(timeout=None)` | `True` when the endpoint can take requests. A deck can be listed but not ready yet. |
| `status(timeout=None)` | `EndpointStatus(ready, max_request, max_response)`. The limits are the endpoint's own, in bytes. |
| `get(path, timeout=None)` | Read a path. Returns the plain Python value. |
| `get_typed(path, timeout=None)` | Read a path. Returns a `TypedValue(type, value)`, which also holds the wire type. |
| `set(path, value, value_type=None, timeout=None)` | Write a path. See [Values](#values) for `value_type`. |
| `cmd(path, arg=NO_ARG, arg_type=None, timeout=None)` | Run a command, with an optional argument. Returns its value, or `None`. |
| `request_raw(message, timeout=None)` | Send any API Service request as bytes. The library sets byte 1, the request ID. Returns the whole response. |
| `submit(message, callback)` | Non-blocking version of `request_raw()`, see below. |
| `notified` | `Caller` of the change notifications, see [Change notifications](#change-notifications). |
| `notify_lost` | `Caller` of the lost notification reports. |
| `set_notify(enabled, timeout=None)` | Turn the forwarding of this endpoint's notifications on or off. |

`timeout=None` means `cf.apiservice.default_timeout`. A request answers in tens of milliseconds, so a timeout almost
always means that the link was lost. A timeout cancels nothing on the Crazyflie.

An endpoint object belongs to the connection it was read on. After a disconnect, it raises
`ApiserviceDisconnectedError`; call `endpoints()` or `endpoint()` again on the new connection.

### Threads and `submit()`

The blocking calls cannot be used from a callback that runs on cflib's incoming-packet thread, such as a log or
parameter callback: they would wait for packets that only that thread can deliver. There they raise `RuntimeError`.
Use `submit()` instead:

```python
from cflib.crazyflie.apiservice_codec import build_get

def on_response(error, response):
    if error is not None:
        print('Failed:', error)
    else:
        print('Response bytes:', response.hex())

cam.submit(build_get(0, 'stream.mjpeg_quality'), on_response)
```

The callback runs once, on the incoming-packet thread, with either an error or the whole response. `submit()` has
no timeout and does not retry: if the Crazyflie is busy, the callback gets `ApiserviceBusyError` at once. Errors found
before anything is sent, such as a message too large, are raised by `submit()` itself.

## Change notifications

An endpoint can report when one of its values changes, for example when setting one Camera Deck setting changes
another one. The Crazyflie forwards these notifications once the client asks for them:

```python
cam = scf.cf.apiservice.endpoint('deck:bcCam')
cam.notified.add_callback(lambda path, value: print(path, value))
cam.notify_lost.add_callback(lambda dropped: refresh_needed.set())   # read again on another thread
cam.set_notify(True)
```

* `notified` and `notify_lost` are `Caller` objects (`add_callback()`, `remove_callback()`). `notified` callbacks
  get `(path, value)`, with the plain Python value as `get()` returns it. `notify_lost` callbacks get `dropped`, the
  number of notifications that were lost (at least that many, 255 at most).
* Adding a callback does not turn forwarding on: `set_notify(True)` does, and `set_notify(False)` turns it off.
  With a firmware that cannot forward notifications, `set_notify()` raises `CrazyflieApiserviceError` with errno
  `FirmwareErrno.ENOSYS`.
* The callbacks are kept by endpoint path in `cf.apiservice`, so they survive a reconnect: an endpoint object read
  on the new connection has the same `notified` and `notify_lost`. Forwarding does not survive: call
  `set_notify(True)` again after each connect.
* Notifications are best effort. When some are lost, for example because the radio link was busy, `notify_lost`
  is called. A client that mirrors values should then read again the paths it mirrors.
* The callbacks run on cflib's incoming-packet thread. They must return quickly and cannot call the blocking
  `cf.apiservice` methods (those raise `RuntimeError` there): hand the work to another thread instead, as with the
  event above. An exception in a callback is logged and does not stop the other callbacks.
* A notification that breaks the encoding rules is logged as a warning and skipped.

## Values

Values come back as plain Python objects. Going out, the library needs a wire type, and Python's `int` does not
say which one.

| Wire type | Python on get | Inferred on set from |
|-----------|---------------|----------------------|
| null | `None` | `None` |
| bool | `bool` | `bool` |
| u8, i8, u16, i16, u32, i32, u64, i64 | `int` | never: pass `value_type`, or `TypeError` |
| string | `str` | `str` |
| bytes | `bytes` | `bytes`, `bytearray` |
| ipv4 | `ipaddress.IPv4Address` | `IPv4Address` |
| unknown type code | `UnknownValue(type_code, data)` | `UnknownValue`, sent as is |

* `ValueType` is an `IntEnum` of the API Service type codes: `ValueType.U8`, `ValueType.STRING` and so on.
* `TypedValue` is a `NamedTuple(type, value)`, returned by `get_typed()` for callers who need to know the width.
* With an explicit `value_type` the value must fit: `ValueType.U8` with 300 raises `ValueError` before anything
  is sent. With `ValueType.IPV4`, a string such as `'192.168.4.1'` is accepted too.
* Strings are UTF-8 without NUL bytes, and a value holds at most 255 bytes.
* Received values are checked against the API Service encoding rules: exact length for fixed-size types, bool 0 or 1,
  valid UTF-8 without NUL. A violation raises `MalformedValueError`.

## Errors

Every exception derives from `ApiserviceError`, in `cflib.crazyflie.apiservice`.

| Exception | When |
|-----------|------|
| `UnknownEndpointError` | The path or ID is not in the catalog. |
| `EndpointNotReadyError` | The endpoint is not ready. |
| `EndpointError` | The endpoint answered with an API Service error: `.code` is a `ApiserviceErrorCode` (or an `int` for an unknown code), `.detail` a text for humans. For example `UNKNOWN_PATH` or `READ_ONLY`. |
| `ApiserviceTimeoutError` | No answer within the timeout. The request was sent: it may or may not have been applied. Also a `TimeoutError`. |
| `ApiserviceBusyError` | The Crazyflie stayed busy until the timeout. The request was never applied and is safe to send again. |
| `ApiserviceDisconnectedError` | Not connected, or the connection ended during the call. |
| `MessageTooLargeError` | The request is larger than the Crazyflie or the endpoint accepts. Nothing was sent. |
| `CrazyflieApiserviceError` | Any other failure reported by the Crazyflie. `.errno` is the firmware's error number (see `FirmwareErrno`), and `.outcome_known` is `True` when the request is known not to have been applied. |
| `UnexpectedResponseError` | An answer of the wrong kind, for example OK when a value was expected. |
| `MalformedValueError` | A value that breaks the encoding rules. |

When the Crazyflie is busy, because all its request slots are taken or the endpoint's own queue is full, the
blocking calls send the request again every 10 ms until their timeout.

The wire protocol is described in the
[CRTP API Service bridge](https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/crtp/crtp_apiservice/)
page of the firmware documentation.
