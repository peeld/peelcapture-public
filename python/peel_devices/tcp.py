from peel_devices import PeelDeviceBase
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket
from PySide6.QtCore import QTimer


class TcpDevice(PeelDeviceBase):

    def __init__(self, name):
        super(TcpDevice, self).__init__(name)
        self.host = None
        self.port = None
        self.tcp = None
        self.current_take = None
        self.error = None
        self.connected_state = None  # ONLINE, OFFLINE, ERROR
        self.device_state = None  # ONLINE, PLAYING, RECORDING
        self.info = None

    def send(self, msg):
        if self.tcp is None:
            print("TCP socket not initialized. Attempting to reconnect...")
            self.connect_device()
            return

        if self.tcp.state() != QAbstractSocket.ConnectedState:
            print("TCP not connected. Attempting to reconnect...")
            self.connect_device()
            return

        print("Sending:", msg.strip())
        self.tcp.write(msg.encode("utf8"))

    def do_read(self):
        raise NotImplementedError

    def do_connected(self):
        self.connected_state = "ONLINE"
        self.update_state(self.connected_state, "")

    def do_disconnected(self):
        self.connected_state = "OFFLINE"
        self.update_state(self.connected_state, "Disconnected")

        # Optional: Retry connection after delay
        QTimer.singleShot(2000, self.connect_device)

    def do_error(self, err):
        print("ERROR", str(err))
        self.connected_state = "ERROR"
        if err == QAbstractSocket.ConnectionRefusedError:
            self.update_state(self.connected_state, "Connection Refused")
        elif err == QAbstractSocket.SocketError.RemoteHostClosedError:
            self.update_state(self.connected_state, "Host Closed")
        elif err == QAbstractSocket.SocketError.HostNotFoundError:
            self.update_state(self.connected_state, "Host Not Found")
        elif err == QAbstractSocket.SocketError.SocketAccessError:
            self.update_state(self.connected_state, "Access Error")
        elif err == QAbstractSocket.SocketError.SocketResourceError:
            self.update_state(self.connected_state, "Resource Error")
        elif err == QAbstractSocket.SocketError.SocketTimeoutError:
            self.update_state(self.connected_state, "Timeout")
        elif err == QAbstractSocket.SocketError.DatagramTooLargeError:
            self.update_state(self.connected_state, "Overflow")
        elif err == QAbstractSocket.SocketError.NetworkError:
            self.update_state(self.connected_state, "No Connection")
        elif err == QAbstractSocket.SocketError.AddressInUseError:
            self.update_state(self.connected_state, "Address in use")
        elif err == QAbstractSocket.SocketError.SocketAddressNotAvailableError:
            self.update_state(self.connected_state, "Unavailable")
        elif err == QAbstractSocket.SocketError.UnsupportedSocketOperationError:
            self.update_state(self.connected_state, "Unsupported")
        elif err == QAbstractSocket.SocketError.ProxyAuthenticationRequiredError:
            self.update_state(self.connected_state, "Proxy Required")
        elif err == QAbstractSocket.SocketError.SslHandshakeFailedError:
            self.update_state(self.connected_state, "SSL HS Error")
        elif err == QAbstractSocket.SocketError.UnfinishedSocketOperationError:
            self.update_state(self.connected_state, "Unfinished Error")
        elif err == QAbstractSocket.SocketError.ProxyConnectionRefusedError:
            self.update_state(self.connected_state, "Proxy Refused")
        elif err == QAbstractSocket.SocketError.ProxyConnectionClosedError:
            self.update_state(self.connected_state, "Proxy Closed")
        elif err == QAbstractSocket.SocketError.ProxyConnectionTimeoutError:
            self.update_state(self.connected_state, "Proxy Timeout")
        elif err == QAbstractSocket.SocketError.ProxyNotFoundError:
            self.update_state(self.connected_state, "Proxy Not Found")
        elif err == QAbstractSocket.SocketError.ProxyProtocolError:
            self.update_state(self.connected_state, "Proxy tx Error")
        elif err == QAbstractSocket.SocketError.OperationError:
            self.update_state(self.connected_state, "Op Error")
        elif err == QAbstractSocket.SocketError.SslInternalError:
            self.update_state(self.connected_state, "SSL Error")
        elif err == QAbstractSocket.SocketError.SslInvalidUserDataError:
            self.update_state(self.connected_state, "SSL User Error")
        elif err == QAbstractSocket.SocketError.TemporaryError:
            self.update_state(self.connected_state, "Temp Error")
        elif err == QAbstractSocket.SocketError.UnknownSocketError:
            self.update_state(self.connected_state, "Unknown")
        else:
            self.update_state(self.connected_state, str(err))

    def as_dict(self):
        return {'name': self.name,
                'host': self.host,
                'port': self.port}

    def teardown(self):
        if self.tcp:
            print("Tearing down TCP connection...")
            if self.tcp.state() == QAbstractSocket.ConnectedState:
                self.tcp.disconnectFromHost()
            self.tcp.close()
            self.tcp.deleteLater()
            self.tcp = None

    def reconfigure(self, name, **kwargs):

        self.teardown()

        self.host = kwargs.get('host')
        self.port = kwargs.get('port')

        self.current_take = None
        self.error = None
        self.connected_state = None
        self.name = name

        return True

    def connect_device(self):
        print(f"TCP Connecting to {self.host} {self.port}")

        # Tear down existing socket if needed
        if self.tcp is not None:
            self.tcp.abort()  # Immediately disconnect any existing connection
            self.tcp.deleteLater()

        self.tcp = QTcpSocket()
        self.tcp.connected.connect(self.do_connected)
        self.tcp.disconnected.connect(self.do_disconnected)
        self.tcp.readyRead.connect(self.do_read)
        self.tcp.errorOccurred.connect(self.do_error)

        self.tcp.connectToHost(self.host, self.port)

    def get_state(self, reason=None):

        if not self.enabled:
            return "OFFLINE"

        if self.error is not None:
            return "ERROR"

        if self.connected_state in ["OFFLINE", "ERROR"]:
            return self.connected_state

        if self.device_state is None:
            return "OFFLINE"

        return self.device_state

    def get_info(self, reason=None):
        if self.error is not None:
            return self.error
        return ""