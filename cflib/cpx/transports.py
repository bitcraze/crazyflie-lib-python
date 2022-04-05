
import socket

class CPXTransport:
    def __init__(self):
      raise NotImplementedError("Cannot be used")

    # Change this to URI?
    def connect(host, port):
      raise NotImplementedError("Cannot be used")

    def disconnect():
      raise NotImplementedError("Cannot be used")

    def send(self, data):
      raise NotImplementedError("Cannot be used")

    def receive(self, size):
      raise NotImplementedError("Cannot be used")

class SocketTransport(CPXTransport):
    def __init__(self, host, port):
      print("CPX socket transport")
      self._host = host
      self._port = port

      self.connect()

    def connect(self):
      print("Connecting to socket on {}:{}...".format(self._host, self._port))
      self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self._socket.connect((self._host, self._port))
      print("Connected")

    def disconnect(self):
      self._socket.close()
      self._socket = None

    def write(self, data):
      self._socket.send(data)

    def read(self, size):
      data = bytearray()
      while len(data) < size:
        data.extend(self._socket.recv(size-len(data)))
      return data

class CRTPTransport(CPXTransport):
    def __init__(self):
        print("CPX CRTP transport")

    # This connection will not really work...
    def connect(host, port):
      pass

    def disconnect():
      pass

    def send(self, data):
      pass

    def receive(self, size):
      pass
