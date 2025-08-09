from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtNetwork import QUdpSocket, QHostAddress


class UdpBroadcast(QObject):
    def __init__(self, broadcast_port, parent=None):
        super().__init__(parent)
        self.broadcast_port = broadcast_port
        self.message = None

        # Create the QUdpSocket for broadcasting
        self.udp_socket = QUdpSocket(self)

        # Timer to send periodically
        self.timer = QTimer(self)
        self.timer.setInterval(5000)  # 5 seconds
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.send)

    def set_message(self, message: bytes):
        self.message = message

    def send(self):
        if not self.message:
            return
        bytes_sent = self.udp_socket.writeDatagram(
            self.message,
            QHostAddress.Broadcast,
            self.broadcast_port
        )
        if bytes_sent == -1:
            print(f"[ERROR] Failed to send broadcast: {self.udp_socket.errorString()}")

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()


class UdpBroadcastListener(QObject):
    packet_received = Signal(bytes, str, int)  # data, sender IP, sender port

    def __init__(self, parent=None):
        super().__init__(parent)
        self.port = None
        self.socket = QUdpSocket(self)

    def start(self, port):
        self.port = port

        # Bind to any IPv4 address, allow address reuse and broadcast reception
        success = self.socket.bind(
            QHostAddress.AnyIPv4,
            self.port,
            QUdpSocket.ShareAddress | QUdpSocket.ReuseAddressHint
        )

        if not success:
            print(f"[ERROR] Failed to bind to UDP port {self.port}")
            return

        print(f"[INFO] Listening for UDP broadcast on port {self.port}")
        self.socket.readyRead.connect(self.read_pending_datagrams)

    def stop(self):
        self.socket.close()

    def read_pending_datagrams(self):
        while self.socket.hasPendingDatagrams():
            datagram, host, port = self.socket.readDatagram(self.socket.pendingDatagramSize())
            # print(f"[RECEIVED] From {host.toString()}:{port} -> {datagram}")
            self.packet_received.emit(datagram, host.toString(), port)
