import socket
from Server import Server


class ServerHandle:

    def __init__(self):
        self.rtsp_port = 8000
        self.rtsp_ip = '127.0.0.1'
        self.rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rtsp_socket.bind((self.rtsp_ip, self.rtsp_port))
        self.rtsp_socket.listen(10)
        self.rtp_port = 3000
        self.run()

    def run(self):
        """ serve multiple clients."""
        while True:
            client_socket, addr = self.rtsp_socket.accept()
            client = Server(client_socket, self.rtp_port)
            self.rtp_port += 1


if __name__ == '__main__':
    server = ServerHandle()
