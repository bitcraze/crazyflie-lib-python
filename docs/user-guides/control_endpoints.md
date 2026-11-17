---
title: Control endpoints
page_id: control_endpoints
---

Some devices on a Crazyflie, such as the Camera Deck, have settings and commands of their own. They serve them
through the Control protocol (`bitcraze.control`), and the Crazyflie makes them available on CRTP port 10, the
Control bridge. Each such device is a *Control endpoint*, named by a path such as `deck:bcCam`. Inside an endpoint,
values are named by paths too, such as `stream.mjpeg_quality`.

In the library the endpoints are reached through `cf.control`. The Control bridge needs a Crazyflie firmware with
CRTP protocol version 14 or later. With an older firmware the list of endpoints is empty.

An example is in [examples/control/control_endpoints.py](https://github.com/bitcraze/crazyflie-lib-python/blob/master/examples/control/control_endpoints.py).
It prints the endpoints and reads or writes a path on one of them.

## Usage

```python
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

cflib.crtp.init_drivers()

with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    control = scf.cf.control
    for ep in control.endpoints():
        print(ep.id, ep.path, ep.is_ready())

    cam = control.endpoint('deck:bcCam')
    quality = cam.get_typed('stream.mjpeg_quality')   # TypedValue(type, value)
    print(quality.value)
    cam.set('stream.mjpeg_quality', 80, quality.type)   # ints need their wire type
```

Reading the type first with `get_typed()` lets a script set an integer path without hard-coding its width.

## API

The calls block and raise an exception on failure, with a timeout on every call.

### `cf.control`

| Method | Description |
|--------|-------------|
| `endpoints(timeout=None)` | The list of `ControlEndpoint` of this connection. |
| `endpoint(path, timeout=None)` | The endpoint with this path, for example `'deck:bcCam'`. Raises `UnknownEndpointError`. |
| `info(timeout=None)` | `BridgeInfo(count, catalog_crc, max_in_flight, max_message)`, or `None` when the Crazyflie has no Control bridge. |
| `default_timeout` | Timeout of every call that does not give one, in seconds. 3 s by default. |

The list of endpoints is read the first time it is needed on a connection, not when connecting, so a script that
does not use Control endpoints pays nothing. It is kept until the connection ends.

### `ControlEndpoint`

| Member | Description |
|--------|-------------|
| `id`, `path` | Catalog ID and path of the endpoint. |
| `is_ready(timeout=None)` | `True` when the endpoint can take requests. A deck can be listed but not ready yet. |
| `status(timeout=None)` | `EndpointStatus(ready, max_request, max_response)`. The limits are the endpoint's own, in bytes. |
| `get(path, timeout=None)` | Read a path. Returns the plain Python value. |
| `get_typed(path, timeout=None)` | Read a path. Returns a `TypedValue(type, value)`, which also holds the wire type. |
| `set(path, value, value_type=None, timeout=None)` | Write a path. See [Values](#values) for `value_type`. |
| `cmd(path, arg=NO_ARG, arg_type=None, timeout=None)` | Run a command, with an optional argument. Returns its value, or `None`. |
| `request_raw(message, timeout=None)` | Send any Control request as bytes. The library sets byte 1, the request ID. Returns the whole response. |
| `submit(message, callback)` | Non-blocking version of `request_raw()`, see below. |

`timeout=None` means `cf.control.default_timeout`. A request answers in tens of milliseconds, so a timeout almost
always means that the link was lost. A timeout cancels nothing on the Crazyflie.

An endpoint object belongs to the connection it was read on. After a disconnect, it raises
`ControlDisconnectedError`; call `endpoints()` or `endpoint()` again on the new connection.

### Threads and `submit()`

The blocking calls cannot be used from a callback that runs on cflib's incoming-packet thread, such as a log or
parameter callback: they would wait for packets that only that thread can deliver. There they raise `RuntimeError`.
Use `submit()` instead:

```python
from cflib.crazyflie.control_codec import build_get

def on_response(error, response):
    if error is not None:
        print('Failed:', error)
    else:
        print('Response bytes:', response.hex())

cam.submit(build_get(0, 'stream.mjpeg_quality'), on_response)
```

The callback runs once, on the incoming-packet thread, with either an error or the whole response. `submit()` has
no timeout and does not retry: if the Crazyflie is busy, the callback gets `ControlBusyError` at once. Errors found
before anything is sent, such as a message too large, are raised by `submit()` itself.

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

* `ValueType` is an `IntEnum` of the Control type codes: `ValueType.U8`, `ValueType.STRING` and so on.
* `TypedValue` is a `NamedTuple(type, value)`, returned by `get_typed()` for callers who need to know the width.
* With an explicit `value_type` the value must fit: `ValueType.U8` with 300 raises `ValueError` before anything
  is sent. With `ValueType.IPV4`, a string such as `'192.168.4.1'` is accepted too.
* Strings are UTF-8 without NUL bytes, and a value holds at most 255 bytes.
* Received values are checked against the Control encoding rules: exact length for fixed-size types, bool 0 or 1,
  valid UTF-8 without NUL. A violation raises `MalformedValueError`.

## Errors

Every exception derives from `ControlError`, in `cflib.crazyflie.control`.

| Exception | When |
|-----------|------|
| `UnknownEndpointError` | The path or ID is not in the catalog. |
| `EndpointNotReadyError` | The endpoint is not ready. |
| `EndpointError` | The endpoint answered with a Control error: `.code` is a `ControlErrorCode` (or an `int` for an unknown code), `.detail` a text for humans. For example `UNKNOWN_PATH` or `READ_ONLY`. |
| `ControlTimeoutError` | No answer within the timeout. The request was sent: it may or may not have been applied. Also a `TimeoutError`. |
| `ControlBusyError` | The Crazyflie stayed busy until the timeout. The request was never applied and is safe to send again. |
| `ControlDisconnectedError` | Not connected, or the connection ended during the call. |
| `MessageTooLargeError` | The request is larger than the Crazyflie or the endpoint accepts. Nothing was sent. |
| `CrazyflieControlError` | Any other failure reported by the Crazyflie. `.errno` is the firmware's error number (see `FirmwareErrno`), and `.outcome_known` is `True` when the request is known not to have been applied. |
| `UnexpectedResponseError` | An answer of the wrong kind, for example OK when a value was expected. |
| `MalformedValueError` | A value that breaks the encoding rules. |

When the Crazyflie is busy, because all its request slots are taken or the endpoint's own queue is full, the
blocking calls send the request again every 10 ms until their timeout.

The wire protocol is described in the
[CRTP Control bridge](https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/crtp/crtp_control/)
page of the firmware documentation.
