import os
import random
import socket
import threading
import time
from RtpPacket import RtpPacket
import cv2
from PIL import Image
from RtcpPacket import RtcpPacket


class Server:

    def __init__(self, client_rtsp_socket, client_rtp_port):
        self.rtsp_socket = client_rtsp_socket
        self.rtsp_seq = 0
        self.status_code = 200

        self.rtp_socket = 0
        self.rtp_addr = '127.0.0.1'
        self.rtp_port = client_rtp_port

        self.rtcp_port = 3100
        self.rtcp_ip = '127.0.0.1'
        self.rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # about file
        self.frame_window = []
        self.file_size = 1024
        self.file_name = ''
        self.session_id = 0
        self.picture_size = 1  # 1代表720p, 0 代表360p

        # play status
        self.SETUP = 2000
        self.PLAY = 2001
        self.PAUSE = 2002
        self.TEARDOWN = 2003

        # playing status
        self.play_event = threading.Event()
        self.kill_cur_play = False

        # current frame
        self.cur_frame = 0
        self.seq_num = 1
        self.percent = 0

        self.frame_total_count = 0
        threading.Thread(target=self.recv_rtsp).start()

    def recv_rtsp(self):
        while True:
            try:
                data = self.rtsp_socket.recv(2048).decode('utf-8')
                self.parse_reply(data)
            except OSError:
                break

    def send_message(self, data):
        self.rtsp_socket.send(data.encode())

    def parse_reply(self, reply):
        lines = reply.split('\n')
        command = lines[0].split(' ')[0]
        self.rtsp_seq = lines[1].split(' ')[1]

        client_file_name = lines[0].split(' ')[1]
        if command == 'SETUP':
            # 添加文件
            file_list = os.listdir('video/')
            file_transfer = ""
            for file in file_list:
                file_transfer += str(file) + " "
            file_transfer = file_transfer[:-1]
            m_response = 'RTSP/1.0 ' + str(self.status_code) + ' OK\n' + 'Cseq: ' + str(self.rtsp_seq) + '\n' + \
                         'Session: ' + str(self.session_id) + '\nfile: ' + str(file_transfer)
            self.rtp_port = int(lines[2].split(' ')[3])
            self.rtcp_port = int(lines[3].split(' ')[3])
            self.listen_rtcp_port()
            self.send_message(m_response)
            self.open_rtp_port()
        elif command == 'PLAY':
            self.picture_size = int(lines[-3].split(' ')[1])
            frame = self.get_frame_count('video/' + client_file_name)
            self.session_id = lines[-2].split(' ')[1]
            client_movie_percent = float(lines[-1].split(' ')[1])
            t_response = 'RTSP/1.0 ' + str(self.status_code) + ' OK\n' + 'Cseq: ' + str(self.rtsp_seq) + '\n' + \
                         'Session: ' + str(self.session_id) + '\nRTP-Info: rtptime= ' + str(frame)
            self.send_message(t_response)
            # 从头开始播放或者播放新的视频
            if self.percent == 0 or (client_file_name != self.file_name):
                self.cur_frame = 0
                self.percent = 0
                try:
                    self.play_event.set()
                except:
                    pass
                self.kill_cur_play = True
                # wait for threading end
                time.sleep(0.01)
                self.file_name = client_file_name
                self.kill_cur_play = False
                # 播放视频
                threading.Thread(target=self.send_movie_from_point, args=(self.percent, 'video/' + self.file_name)) \
                    .start()

                self.play_event = threading.Event()
                self.play_event.clear()
            elif client_file_name == self.file_name and abs(client_movie_percent - self.percent) * \
                    self.frame_total_count > 25:
                # 对方拉了视频进度条，从头开始读

                self.percent = client_movie_percent
                try:
                    self.play_event.set()
                except:
                    pass
                self.kill_cur_play = True
                # wait for threading end
                time.sleep(0.01)
                self.file_name = client_file_name
                self.kill_cur_play = False
                threading.Thread(target=self.send_movie_from_point, args=(self.percent, 'video/' + self.file_name)) \
                    .start()
                self.play_event = threading.Event()
                self.play_event.clear()
            elif client_file_name == self.file_name and abs(client_movie_percent - self.percent) * \
                    self.frame_total_count < 25:
                # 从暂停状态中恢复过来
                self.play_event.clear()

        elif command == 'PAUSE':
            self.play_event.set()
            self.session_id = lines[-1].split(' ')[1]
            t_response = 'RTSP/1.0 ' + str(self.status_code) + ' OK\n' + 'Cseq: ' + str(self.rtsp_seq) + '\n' + \
                         'Session: ' + str(self.session_id)
            self.send_message(t_response)

        elif command == 'TEARDOWN':
            self.play_event.set()
            self.session_id = lines[-1].split(' ')[1]
            t_response = 'RTSP/1.0 ' + str(self.status_code) + ' OK\n' + 'Cseq: ' + str(self.rtsp_seq) + '\n' + \
                         'Session: ' + str(self.session_id)
            self.send_message(t_response)
            self.rtsp_socket.close()
            self.kill_cur_play = True

        else:
            pass

    def open_rtp_port(self):
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def listen_rtcp_port(self):
        self.rtcp_socket.bind(("127.0.0.1", self.rtcp_port))

    def send_movie_from_point(self, percent, filename):
        self.seq_num = 0
        vid_cap = cv2.VideoCapture(filename)
        success, image = vid_cap.read()
        fps = 1
        self.frame_total_count = vid_cap.get(cv2.CAP_PROP_FRAME_COUNT)
        frame_start = int(self.frame_total_count * percent)
        vid_cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_start))
        count = frame_start
        while success or self.play_event.isSet():
            if not self.play_event.isSet():
                if count % fps == 0 and count >= frame_start:
                    self.percent = float(count / self.frame_total_count)
                    frame_name = 'jpg_stream/' + str(time.time()) + str(int(count / fps)) + '.jpg'
                    cv2.imwrite(frame_name, image)
                    self.send_one_picture_frame(frame_name)
                if not self.play_event.isSet():
                    success, image = vid_cap.read()
                    count += 1
            if self.kill_cur_play:
                break
        vid_cap.release()

    def send_jpg(self, file_name):
        """ send a picture"""
        try:
            if not self.play_event.isSet():
                fp = open(file_name, 'rb')
                rtp_pack = RtpPacket()
                SSRC = random.randint(566, 200000)
                next_payload = fp.read(65000)
                n = len(next_payload)
                self.seq_num = 1
                self.frame_window.clear()
                while n > 0:
                    payload = next_payload
                    next_payload = fp.read(65000)
                    n = len(next_payload)
                    self.frame_window.append(payload)
                    if self.play_event.isSet():
                        break
                fp.close()
                length_packet = len(self.frame_window)
                for index in range(length_packet):
                    if self.play_event.isSet():
                        break
                    V, P, X, CC, seq, M, PT = 2, 0, 0, length_packet, self.seq_num, 0, 26
                    if index == length_packet - 1:
                        M = 1
                    rtp_pack.encode(V, P, X, CC, seq, M, PT, SSRC, self.frame_window[index])
                    buf = rtp_pack.getPacket()
                    self.frame_window[index] = buf
                    self.rtp_socket.sendto(buf, ('127.0.0.1', self.rtp_port))
                    self.seq_num += 1
            else:
                return
        except FileNotFoundError:
            pass

    def send_packet(self, number):
        """lose packet, send data in window again"""
        number = int(number) - 1
        length = len(self.frame_window)
        for index in range(number, length):
            if self.play_event.isSet():
                break
            self.rtp_socket.sendto(self.frame_window[index], ('127.0.0.1', self.rtp_port))

    def get_frame_count(self, filename):
        """get total frame of a video file"""
        vid_cap = cv2.VideoCapture(filename)
        frame_total_count = vid_cap.get(cv2.CAP_PROP_FRAME_COUNT)
        return int(frame_total_count // 2)

    def send_one_picture_frame(self, frame_name):
        """send a picture, if lose packet, loop loop until success"""
        self.changeSize(frame_name)
        self.send_jpg(frame_name)
        if self.play_event.isSet():
            os.remove(frame_name)
            return
        data = self.rtcp_socket.recv(2048)
        rtcpPacket = RtcpPacket()
        rtcpPacket.decode(data)
        data = rtcpPacket.getPayload().decode('utf-8')
        if data == 'ack':
            pass
        elif data[:3] == 'nak':
            while data[:3] == 'nak':
                if self.play_event.isSet():
                    break
                self.send_packet(data.split(' ')[1])
                if self.play_event.isSet():
                    break
                data = self.rtcp_socket.recv(2048)
                rtcpPacket.decode(data)
                data = rtcpPacket.getPayload().decode('utf-8')
        os.remove(frame_name)
        return

    def changeSize(self, file_name):
        image = Image.open(file_name)
        size = image.size
        if self.picture_size == 0:
            size1, size2 = size
            size1, size2 = 0.3 * size1, 0.3 * size2
            size = size1, size2
        image.thumbnail(size, Image.ANTIALIAS)
        image.save(file_name, 'jpeg')
