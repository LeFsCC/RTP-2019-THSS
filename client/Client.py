import random
import sys
from socket import *
import socket
import os
import time
import threading
from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from RtpPacket import RtpPacket
from RtcpPacket import RtcpPacket


class Client(QtWidgets.QWidget):
    # status
    INIT = 2000
    READY = 2001
    PLAYING = 2002
    state = INIT
    CACHE_FILE_NAME = str(int(round(time.time() * 1000))) + '/'
    # command
    SETUP = 1001
    PLAY = 1002
    PAUSE = 1003
    TEARDOWN = 1004

    def __init__(self):
        super(Client, self).__init__()

        """ about ui """
        os.makedirs(self.CACHE_FILE_NAME)
        self.rate_queue = ['1', '0.5', '1.25', '1.5', '2.0']
        self.play_delay = 0.035
        self.desktop = QApplication.desktop()
        self.screenRect = self.desktop.screenGeometry()
        self.screen_width = self.screenRect.width()
        self.screen_height = self.screenRect.height()
        self.port_edit = QLineEdit(self)
        self.ip_edit = QLineEdit(self)
        self.connect_btn = QtWidgets.QPushButton('连接', self)
        self.rtp_port_edit = QLineEdit(self)
        self.rtp_label = QtWidgets.QLabel(self)
        self.rtcp_port_label = QtWidgets.QLabel(self)
        self.rtcp_port_edit = QLineEdit(self)
        self.movie_name_label = QtWidgets.QLabel(self)
        self.movie_name_edit = QLineEdit(self)
        self.lose_rate = QtWidgets.QLabel(self)
        self.time_label = QtWidgets.QLabel(self)
        self.timer = QTimer(self)
        self.setup_btn = QtWidgets.QPushButton('准备', self)
        self.play_btn = QtWidgets.QPushButton('播放', self)
        self.pause_btn = QtWidgets.QPushButton('暂停', self)
        self.teardown_btn = QtWidgets.QPushButton('退出', self)
        self.fullscreen_btn = QtWidgets.QPushButton('全屏', self)
        self.video_label = QtWidgets.QLabel(self)
        self.video_slider = QtWidgets.QSlider(Qt.Horizontal, self)
        self.load_gif = QMovie('load.gif')
        self.low_level_video = QRadioButton(self)
        self.high_level_video = QRadioButton(self)
        self.rate_select = QComboBox(self)
        self.video_list = QListWidget(self)
        self.createWindow()

        # 当前播放图片的大小
        self.cur_imageRect = {'width': 1000, 'height': 500}

        """ about RTSP/RTP/RTCP """
        self.rtsp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.rtsp_seq = 0
        self.rtsp_command_send = -1
        self.rtp_socket = 0
        self.rtp_port = 3000
        self.rtcp_port = 3100
        self.rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.session_id = 0
        self.teardown_ack = 0

        """ about file """
        self.fileName = ""
        self.play_event = 0
        self.frame_num = 0
        self.cc = 0
        self.ack_num = 0
        self.nak_num = 0
        # 从何处开始播放视频(百分比)
        self.percent = 0
        self.play_seconds = 0  # 已经播放的秒数
        self.play_delay_queue = [0.035, 0.07, 0.028, 0.0235, 0.0175]
        self.total_frame = 0
        self.curr_frame = 0
        self.time_flag = 1
        self.video_level = 1  # 默认高分辨率

    def createWindow(self):
        """ init Gui """
        qr = self.frameGeometry()
        cp = QtWidgets.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.setWindowTitle("MultiMedia")

        self.ip_edit.resize(120, 25)
        self.ip_edit.move(1050, 50)
        self.ip_edit.setText('127.0.0.1')

        self.port_edit.resize(80, 25)
        self.port_edit.move(1190, 50)
        self.port_edit.setText('8000')

        self.connect_btn.resize(100, 25)
        self.connect_btn.move(1290, 50)
        self.connect_btn.clicked.connect(self.on_connect_btn)

        self.rtp_port_edit.resize(80, 25)
        self.rtp_port_edit.move(1120, 80)
        self.rtp_port_edit.setText('3000')
        self.rtp_label.resize(50, 25)
        self.rtp_label.move(1050, 80)
        self.rtp_label.setText('RTP port')

        self.rtcp_port_edit.resize(80, 25)
        self.rtcp_port_edit.move(1300, 80)
        self.rtcp_port_edit.setText('3100')
        self.rtcp_port_label.resize(60, 25)
        self.rtcp_port_label.move(1220, 80)
        self.rtcp_port_label.setText('RTCP port')

        self.movie_name_label.resize(50, 25)
        self.movie_name_label.move(1050, 110)
        self.movie_name_label.setText('movie')

        self.movie_name_edit.resize(100, 25)
        self.movie_name_edit.move(1120, 110)
        self.movie_name_edit.setText('xinjiang.mp4')

        self.lose_rate.resize(50, 25)
        self.lose_rate.move(1050, 140)
        self.lose_rate.setText('0')

        self.time_label.resize(100, 20)
        self.time_label.move(500, 560)
        self.time_label.setText('00:00:00')

        self.timer.timeout.connect(self.update_time)

        self.setup_btn.resize(120, 40)
        self.setup_btn.move(120, 620)
        self.setup_btn.clicked.connect(self.on_setup_btn)

        self.play_btn.resize(120, 40)
        self.play_btn.move(300, 620)
        self.play_btn.clicked.connect(self.on_play_btn)

        self.pause_btn.resize(120, 40)
        self.pause_btn.move(480, 620)
        self.pause_btn.clicked.connect(self.on_pause_btn)

        self.teardown_btn.resize(120, 40)
        self.teardown_btn.move(660, 620)
        self.teardown_btn.clicked.connect(self.on_teardown_btn)

        self.fullscreen_btn.resize(120, 40)
        self.fullscreen_btn.move(840, 620)
        self.fullscreen_btn.clicked.connect(self.fullscreen)

        self.video_slider.resize(1000, 30)
        self.video_slider.move(40, 520)
        self.video_slider.sliderReleased.connect(self.change_point)
        self.video_slider.sliderPressed.connect(self.load_frame)
        self.video_slider.setSingleStep(1)
        self.video_slider.setMinimum(1)

        self.video_label.setScaledContents(True)

        self.rate_select.resize(100, 30)
        self.rate_select.move(1050, 170)
        self.rate_select.addItems(self.rate_queue)
        self.rate_select.currentIndexChanged.connect(self.selectionchange)

        self.low_level_video.resize(60, 20)
        self.low_level_video.move(700, 560)
        self.low_level_video.setText('低分辨')
        self.low_level_video.toggled.connect(self.change_video_low_level)

        self.high_level_video.resize(60, 20)
        self.high_level_video.move(800, 560)
        self.high_level_video.setText('高分辨')
        self.high_level_video.toggled.connect(self.change_video_high_level)

        self.video_list.resize(300, 300)
        self.video_list.move(1050, 230)
        self.video_list.clicked.connect(self.choose_video)

        self.resize(1450, 720)
        self.show()

    def on_connect_btn(self):
        """ connect to the Server. start a new RTSP/TCP session."""
        ip = self.ip_edit.text()
        port = int(self.port_edit.text())
        try:
            self.rtsp_socket.connect((ip, port))
            QMessageBox.information(self, 'success', 'Connection Success\n' + str(self.ip_edit.text()) + '\n' +
                                    str(self.port_edit.text()), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        except:
            QMessageBox.critical(self, "Connection Error", "Failed to connect \n" + str(self.ip_edit.text()) + '\n' +
                                 str(self.port_edit.text()), QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def on_setup_btn(self):
        """ setup movie for preparing."""
        if self.state == self.INIT:
            self.send_rtsp_request(self.SETUP)

    def change_video_low_level(self):
        self.play_delay_queue = [0.045, 0.09, 0.036, 0.03, 0.0225]
        self.video_level = 0

    def change_video_high_level(self):
        self.play_delay_queue = [0.035, 0.07, 0.028, 0.0235, 0.0175]
        self.video_level = 1

    def choose_video(self, index):
        self.movie_name_edit.setText(self.video_list.item(index.row()).text())

    def on_play_btn(self):
        """ play movie on screen."""
        if self.state == self.READY:
            self.send_rtsp_request(self.PLAY)

    def load_frame(self):
        self.video_label.setMovie(self.load_gif)
        self.video_label.setGeometry(500, 250, 64, 64)
        self.load_gif.start()
        self.on_pause_btn()

    def on_pause_btn(self):
        """ pause movie. """
        if self.state == self.PLAYING:
            self.timer.stop()
            self.send_rtsp_request(self.PAUSE)
            self.time_flag = 0

    def on_teardown_btn(self):
        """Teardown button handler."""
        # self.send_rtsp_request(self.TEARDOWN)
        self.close()

    def selectionchange(self, i):
        """ change speed."""
        self.timer.stop()
        if i == 0:
            self.timer.start(1000)
        elif i == 1:
            self.timer.start(2000)
        elif i == 2:
            self.timer.start(800)
        elif i == 3:
            self.timer.start(666.6666)
        elif i == 4:
            self.timer.start(500)
        else:
            self.timer.start(1000)
        self.play_delay = self.play_delay_queue[i]

    def fullscreen(self):
        """ entering full screen mode. """
        self.port_edit.setVisible(False)
        self.ip_edit.setVisible(False)
        self.connect_btn.setVisible(False)
        self.setup_btn.setVisible(False)
        self.play_btn.setVisible(False)
        self.pause_btn.setVisible(False)
        self.teardown_btn.setVisible(False)
        self.fullscreen_btn.setVisible(False)
        self.video_slider.setVisible(False)
        self.rtp_port_edit.setVisible(False)
        self.rtp_label.setVisible(False)
        self.rtcp_port_edit.setVisible(False)
        self.rtcp_port_label.setVisible(False)
        self.movie_name_edit.setVisible(False)
        self.movie_name_label.setVisible(False)
        self.rate_select.setVisible(False)
        self.time_label.setVisible(False)
        self.low_level_video.setVisible(False)
        self.high_level_video.setVisible(False)
        self.video_list.setVisible(False)
        self.video_label.setGeometry(0, 0, self.screen_width, self.screen_height)
        self.showFullScreen()

    def keyPressEvent(self, QKeyEvent):
        """ exit full screen mode. """
        if QKeyEvent.key() == Qt.Key_Escape:  # 判断是否按下了A键
            width = 1000
            height = 450
            try:
                scale = min(width / self.cur_imageRect['width'], height / self.cur_imageRect['height'])
                self.video_label.setGeometry(40, 50, self.cur_imageRect['width'] * scale, self.cur_imageRect['height']
                                             * scale)
            except:
                return

            self.port_edit.setVisible(True)
            self.ip_edit.setVisible(True)
            self.connect_btn.setVisible(True)
            self.setup_btn.setVisible(True)
            self.play_btn.setVisible(True)
            self.pause_btn.setVisible(True)
            self.teardown_btn.setVisible(True)
            self.fullscreen_btn.setVisible(True)
            self.video_slider.setVisible(True)
            self.rtp_port_edit.setVisible(True)
            self.rtp_label.setVisible(True)
            self.rtcp_port_edit.setVisible(True)
            self.rtcp_port_label.setVisible(True)
            self.movie_name_label.setVisible(True)
            self.movie_name_edit.setVisible(True)
            self.rate_select.setVisible(True)
            self.time_label.setVisible(True)
            self.low_level_video.setVisible(True)
            self.high_level_video.setVisible(True)
            self.video_list.setVisible(True)
            self.showNormal()

    def open_rtp_port(self):
        """Open RTP socket binded to a specified port."""
        self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rtp_socket.settimeout(0.005)
        try:
            self.rtp_socket.bind(("127.0.0.1", self.rtp_port))
        except:
            QMessageBox.critical(self, 'Unable to Bind', 'Unable to bind PORT=%d' % self.rtp_port,
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def open_rtcp_port(self):
        """Open RTP socket binded to a specified port."""
        self.rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_rtsp_request(self, request_code):
        """ send RTSP request to the server."""
        last_fileName = ''
        if request_code == self.PLAY:
            last_fileName = self.fileName
            self.fileName = self.movie_name_edit.text()
        if request_code == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recv_rtsp_reply).start()
            self.rtsp_seq += 1
            self.rtp_port = int(self.rtp_port_edit.text())
            self.rtcp_port = int(self.rtcp_port_edit.text())
            request = 'SETUP ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(
                self.rtsp_seq) + '\nTransport: RTP/UDP; client_port= ' + str(self.rtp_port) + \
                '\nProtect: RTCP/TCP; rtcp_port= ' + str(self.rtcp_port)
            self.rtsp_command_send = request_code
        elif request_code == self.PLAY and self.state == self.READY:
            if last_fileName != self.fileName:
                self.play_seconds = 0
                self.curr_frame = 0
                self.time_label.setText('00:00:00')
            self.rtsp_seq += 1
            self.timer.start(1000)

            request = 'PLAY ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtsp_seq) + '\nlevel: ' + \
                      str(self.video_level) + '\nSession: ' + str(self.session_id) + '\nRange: ' + str(self.percent)
            self.rtsp_command_send = request_code
        elif request_code == self.PAUSE and self.state == self.PLAYING:
            self.rtsp_seq += 1
            request = 'PAUSE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtsp_seq) + '\nSession: ' + str(
                self.session_id)
            self.rtsp_command_send = request_code
        elif request_code == self.TEARDOWN and not self.state == self.INIT:
            self.rtsp_seq += 1
            request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtsp_seq) + '\nSession: ' + str(
                self.session_id)
            self.rtsp_command_send = request_code
        else:
            return
        self.rtsp_socket.send(request.encode())

    def recv_rtsp_reply(self):
        while True:
            reply = self.rtsp_socket.recv(2048)
            if reply:
                self.parse_reply(reply.decode("utf-8"))

            if self.rtsp_command_send == self.TEARDOWN:
                self.rtsp_socket.shutdown(socket.SHUT_RDWR)
                self.rtsp_socket.close()
                break

    def parse_reply(self, reply):
        """Parse the RTSP reply from the server."""
        lines = str(reply).split('\n')
        seq_num = int(lines[1].split(' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seq_num == self.rtsp_seq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.session_id == 0:
                self.session_id = session

            # Process only if the session ID is the same
            if self.session_id == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.rtsp_command_send == self.SETUP:
                        file_list = lines[3].split(' ')[1:]
                        for file in file_list:
                            self.video_list.addItem(file)

                        self.state = self.READY
                        self.open_rtp_port()
                        self.open_rtcp_port()
                    elif self.rtsp_command_send == self.PLAY:
                        self.total_frame = int(lines[3].split(' ')[2])
                        self.video_slider.setMaximum(self.total_frame)
                        self.state = self.PLAYING
                        threading.Thread(target=self.listen_rtp).start()
                        self.play_event = threading.Event()
                        self.play_event.clear()
                    elif self.rtsp_command_send == self.PAUSE:
                        self.state = self.READY
                        self.play_event.set()
                    elif self.rtsp_command_send == self.TEARDOWN:
                        self.state = self.INIT
                        self.teardown_ack = 1
                        self.play_event.set()
                        self.close()

    def listen_rtp(self):
        """Listen for RTP packets."""
        one_frame_data = ""
        fault_mark = 'ack'
        currFrameNbr = 0
        last_time_fault = False
        self.cc = 0
        while True:
            try:
                if self.nak_num + self.ack_num != 0:
                    self.lose_rate.setText(str(self.nak_num / (self.nak_num + self.ack_num))[:5])
                data = self.rtp_socket.recv(65536)
                if data:
                    self.time_flag = 1
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    currFrameNbr = rtpPacket.seqNum()
                    marker = rtpPacket.getMarker()
                    pt = rtpPacket.payloadType()

                    self.cc = rtpPacket.get_csrc()
                    if currFrameNbr != self.frame_num + 1:  # order error
                        fault_mark = 'nak 1'
                        last_time_fault = True
                    elif marker == 1 and not last_time_fault and fault_mark == 'ack':  # end, no error
                        # update some parameter
                        self.ack_num += 1
                        self.frame_num = 0
                        self.curr_frame += 1
                        self.percent = float(self.curr_frame / self.total_frame)
                        self.video_slider.setValue(self.curr_frame)
                        # send rtcp
                        rtcpPacket = RtcpPacket()
                        ssrc = random.randint(556, 10000)
                        rtcpPacket.encode(2, 0, 1, 200, ssrc, 16, fault_mark.encode())
                        packet = rtcpPacket.getPacket()

                        self.rtcp_socket.sendto(packet, ('127.0.0.1', self.rtcp_port))
                        if one_frame_data == "":
                            one_frame_data = rtpPacket.getPayload()
                        else:
                            one_frame_data += rtpPacket.getPayload()

                        time_sleep = self.play_delay
                        time.sleep(time_sleep)
                        cache_name = self.write_frame(one_frame_data)
                        self.update_movie(cache_name)

                        # reset parameter
                        one_frame_data = ""
                        fault_mark = 'ack'
                        last_time_fault = False

                    elif marker == 1 and last_time_fault:  # end, with error
                        self.nak_num += 1
                        self.rtcp_socket.sendto(fault_mark.encode(), ('127.0.0.1', self.rtcp_port))
                        one_frame_data = ""
                        fault_mark = 'ack'
                        last_time_fault = False
                        self.frame_num = 0
                    else:
                        self.frame_num = currFrameNbr
                        if one_frame_data == "":
                            one_frame_data = rtpPacket.getPayload()
                        else:
                            one_frame_data += rtpPacket.getPayload()
            except:
                # 超时处理
                if self.play_event.isSet():
                    break
                if self.teardown_ack == 1:
                    self.rtp_socket.shutdown(socket.SHUT_RDWR)
                    self.rtp_socket.close()
                    break

                if (not self.play_event.isSet()) and self.teardown_ack == 0:
                    self.nak_num += 1
                    # 之前没有出现错误,仅仅是最后的超时错误
                    if not last_time_fault:
                        fault_mark = 'nak ' + str(currFrameNbr + 1)
                    # 之前出现错误, 帧归0
                    if last_time_fault:
                        self.frame_num = 0
                    self.rtcp_socket.sendto(fault_mark.encode(), ('127.0.0.1', self.rtcp_port))
                    last_time_fault = False
                    fault_mark = 'ack'

    def write_audio_segment(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cache_name = self.CACHE_FILE_NAME + str(time.time()) + '.wav'
        file = open(cache_name, "wb")
        file.write(data)
        file.close()
        return cache_name

    def closeEvent(self, event):
        """ close window."""
        if QMessageBox.Yes == QMessageBox.question(self, "close", "确定退出?", QMessageBox.Yes | QMessageBox.No,
                                                   QMessageBox.No):
            try:
                self.send_rtsp_request(self.TEARDOWN)
            except:
                pass
            try:
                self.play_event.set()
            except:
                pass
            self.on_pause_btn()
            self.timer.stop()
            self.remove_cache()
            event.accept()
        else:
            self.play_event.clear()
            event.ignore()

    def remove_cache(self):
        path = self.CACHE_FILE_NAME
        if os.path.isdir(path):
            files = os.listdir(path)
            if len(files) == 0:
                os.rmdir(self.CACHE_FILE_NAME)
            else:
                for file in files:
                    path1 = os.path.join(path, file)
                    os.remove(path1)
                os.rmdir(self.CACHE_FILE_NAME)

    def update_movie(self, file_name):
        """ update movie, put picture on video label. """
        try:
            pix = QPixmap(file_name)
            self.cur_imageRect['width'] = pix.width()
            self.cur_imageRect['height'] = pix.height()
            if self.isFullScreen():
                width = self.screen_width
                height = self.screen_height
                padding_left = 0
                padding_top = 0
            else:
                width = 1000
                height = 450
                padding_left = 40
                padding_top = 50
            scale = min(width / pix.width(), height / pix.height())
            self.video_label.setGeometry(padding_left, padding_top, pix.width() * scale, pix.height() * scale)
            self.video_label.clear()
            self.video_label.setPixmap(pix)
        except:
            pass
        os.remove(file_name)

    def write_frame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        try:
            cache_name = self.CACHE_FILE_NAME + str(time.time()) + '.jpg'
            file = open(cache_name, "wb")
            file.write(data)
            file.close()
            return cache_name
        except:
            return ""

    def update_time(self):
        if self.state == self.PLAYING and self.time_flag == 1:
            self.play_seconds += 1
            m, s = divmod(self.play_seconds, 60)
            h, m = divmod(m, 60)
            self.time_label.setText("%02d:%02d:%02d" % (h, m, s))

    def change_point(self):
        try:
            self.percent = float(int(self.video_slider.value()) / self.total_frame)
            self.curr_frame = int(self.video_slider.value())
            self.play_seconds = int(self.curr_frame * 0.085)
            m, s = divmod(self.play_seconds, 60)
            h, m = divmod(m, 60)
            self.time_label.setText("%02d:%02d:%02d" % (h, m, s))
            self.video_slider.setValue(self.curr_frame)
        except ZeroDivisionError:
            pass
        self.time_flag = 0
        self.video_label.setMovie(self.load_gif)
        self.video_label.setGeometry(500, 250, 64, 64)
        self.load_gif.start()
        self.on_play_btn()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    gui = Client()
    sys.exit(app.exec_())
