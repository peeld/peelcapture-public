from peel_devices import PeelDeviceBase
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket, QTcpServer, QHostAddress
from PySide6.QtCore import QTimer, QObject


class TcpServer(QObject):
    """ Generic TCP server class. """
    def __init__(self, parent):
        super().__init__(parent)
        self.port = None
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self.handle_new_connection)
        self.sessions = []
        self.error = None

    def start(self, port):
        self.port = port
        if not self.server.listen(QHostAddress.Any, self.port):
            self.error = "Unable to start server"
            print(f"Error: Unable to start server on port {self.port}")
        else:
            print(f"Server started on port {self.port}")
            self.error = None

    def stop(self):
        self.server.close()
        for client in self.sessions:
            client.close()
        self.sessions.clear()

    def handle_new_connection(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.readyRead.connect(lambda s=socket: self.handle_ready_read(s))
            socket.disconnected.connect(lambda s=socket: self.handle_disconnected(s))
            self.sessions.append(socket)
            print(f"New connection from {socket.peerAddress().toString()}")

    def handle_ready_read(self, socket):
        if socket.canReadLine():
            while socket.bytesAvailable():
                data = socket.readAll().data()
                if data:
                    self.handle_data(socket, data)

    def handle_disconnected(self, socket):
        if socket in self.sessions:
            self.sessions.remove(socket)
        socket.deleteLater()
        print(f"Connection closed: {socket.peerAddress().toString()}")

    def handle_data(self, remote, data):
        raise NotImplementedError()

    def send(self, data: bytes):
        invalid_sockets = []
        for socket in self.sessions:
            if socket.state() == QTcpSocket.ConnectedState:
                try:
                    socket.write(data)
                    socket.flush()
                except Exception as e:
                    print(f"Send error: {e}")
                    invalid_sockets.append(socket)
            else:
                invalid_sockets.append(socket)
        # Clean up invalid sockets
        for s in invalid_sockets:
            if s in self.sessions:
                self.sessions.remove(s)
            s.deleteLater()


def get_error_string(err):
    if err == QAbstractSocket.ConnectionRefusedError:
        return "Connection Refused"
    elif err == QAbstractSocket.SocketError.RemoteHostClosedError:
        return "Host Closed"
    elif err == QAbstractSocket.SocketError.HostNotFoundError:
        return "Host Not Found"
    elif err == QAbstractSocket.SocketError.SocketAccessError:
        return "Access Error"
    elif err == QAbstractSocket.SocketError.SocketResourceError:
        return "Resource Error"
    elif err == QAbstractSocket.SocketError.SocketTimeoutError:
        return "Timeout"
    elif err == QAbstractSocket.SocketError.DatagramTooLargeError:
        return "Overflow"
    elif err == QAbstractSocket.SocketError.NetworkError:
        return "No Connection"
    elif err == QAbstractSocket.SocketError.AddressInUseError:
        return "Address in use"
    elif err == QAbstractSocket.SocketError.SocketAddressNotAvailableError:
        return "Unavailable"
    elif err == QAbstractSocket.SocketError.UnsupportedSocketOperationError:
        return "Unsupported"
    elif err == QAbstractSocket.SocketError.ProxyAuthenticationRequiredError:
        return "Proxy Required"
    elif err == QAbstractSocket.SocketError.SslHandshakeFailedError:
        return "SSL HS Error"
    elif err == QAbstractSocket.SocketError.UnfinishedSocketOperationError:
        return "Unfinished Error"
    elif err == QAbstractSocket.SocketError.ProxyConnectionRefusedError:
        return "Proxy Refused"
    elif err == QAbstractSocket.SocketError.ProxyConnectionClosedError:
        return "Proxy Closed"
    elif err == QAbstractSocket.SocketError.ProxyConnectionTimeoutError:
        return "Proxy Timeout"
    elif err == QAbstractSocket.SocketError.ProxyNotFoundError:
        return "Proxy Not Found"
    elif err == QAbstractSocket.SocketError.ProxyProtocolError:
        return "Proxy tx Error"
    elif err == QAbstractSocket.SocketError.OperationError:
        return "Op Error"
    elif err == QAbstractSocket.SocketError.SslInternalError:
        return "SSL Error"
    elif err == QAbstractSocket.SocketError.SslInvalidUserDataError:
        return "SSL User Error"
    elif err == QAbstractSocket.SocketError.TemporaryError:
        return "Temp Error"
    elif err == QAbstractSocket.SocketError.UnknownSocketError:
        return "Unknown"
    else:
        return str(err)


class TcpBase:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = None
        self.port = None
        self.tcp = None
        self.error = None
        self.connected_state = "OFFLINE"  # ONLINE, OFFLINE, ERROR
        self.connect_timer = None

    def reconnect_timeout(self, interval):
        self.connect_timer = QTimer(self)
        self.connect_timer.setSingleShot(False)
        self.connect_timer.timeout.connect(self.connect_tcp)
        self.connect_timer.setInterval(interval)

    def send(self, msg):
        if self.tcp is None:
            print("TCP socket not initialized. Attempting to reconnect...")
            self.connect_tcp()
            return

        if self.tcp.state() != QAbstractSocket.ConnectedState:
            self.error = "Not connected"
            return

        self.tcp.write(msg.encode("utf8"))

    def do_connected(self):
        if self.connect_timer:
            self.connect_timer.stop()
        self.connected_state = "ONLINE"

    def do_error(self, err):
        # tcp errorOccurred
        print("TCP ERROR", get_error_string(err))
        self.error = get_error_string(err)
        self.connected_state = "ERROR"
        if self.connect_timer and self.tcp.state() != QAbstractSocket.ConnectedState:
            self.connect_timer.start()

    def do_disconnected(self):
        self.connected_state = "OFFLINE"
        if self.connect_timer:
            self.connect_timer.start()

    def connect_tcp(self, host=None, port=None):

        if host is not None:
            self.host = host
        if port is not None:
            self.port = port

        if self.host is None or self.port is None:
            self.error = "Invalid host/port"
            print("Invalid tcp host/port while connecting")
            return

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

    def close_tcp(self):
        if self.tcp:
            print("Tearing down TCP connection...")
            if self.tcp.state() == QAbstractSocket.ConnectedState:
                self.tcp.disconnectFromHost()
            self.tcp.close()
            self.tcp.deleteLater()
            self.tcp = None

        if self.connect_timer:
            self.connect_timer.stop()

    def do_read(self):
        raise NotImplementedError


class TcpDevice(TcpBase, PeelDeviceBase):

    """ Base class to implement a device that connects using tcp to a remote server """

    def __init__(self, name, parent=None, *args, **kwargs):
        super().__init__(name, parent, *args, **kwargs)
        self.current_take = None
        self.device_state = None  # ONLINE, PLAYING, RECORDING
        self.info = None

    @staticmethod
    def device():
        """ Return the name of the device """
        raise NotImplementedError

    def do_connected(self):
        super().do_connected()
        self.update_state(self.connected_state, "")

    def do_disconnected(self):
        super().do_disconnected()
        self.update_state(self.connected_state, "Disconnected")

    def do_read(self):
        # Subclass needs to implement
        raise NotImplementedError

    def do_error(self, err):
        super().do_error(err)
        self.update_state(self.connected_state, get_error_string(err))

    def as_dict(self):
        ret = super().as_dict()
        ret['port'] = self.port
        ret['host'] = self.host
        return ret

    def teardown(self):
        super().close_tcp()

    def reconfigure(self, name, **kwargs):

        if not super().reconfigure(name, **kwargs):
            return False

        self.teardown()

        self.host = kwargs.get('host')
        self.port = kwargs.get('port')

        self.current_take = None
        self.error = None
        self.connected_state = None

        return True

    def connect_device(self):
        print(f"TCP Connecting to {self.host} {self.port}")
        super().connect_tcp()

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

    @staticmethod
    def dialog_class():
        raise NotImplementedError

    def thread_join(self):
        raise NotImplementedError

