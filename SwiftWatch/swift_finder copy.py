

import sys
import cv2
#import imutils
import resources #pyrcc5 -o resources.py resource.qrc

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from PyQt5.QtGui import *
from PyQt5 import QtCore

width = 800
height = 450

ref_pt = []
click_count = 0


class Thread(QThread):
    changePixmap = pyqtSignal(QImage)

    def get_path(self, video_path):
        global path
        path = video_path

    def run(self):
        cap = cv2.VideoCapture(path)

        while True:
            ret, frame = cap.read()
            rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            convertToQtFormat = QImage(rgbImage.data, rgbImage.shape[1], rgbImage.shape[0], QImage.Format_RGB888)
            #p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
            p = convertToQtFormat.scaled(826, 461, Qt.KeepAspectRatio)
            self.changePixmap.emit(p)


    def stop(self):
        global key
        try:
            if path:
                key = 'stop'
                print("stop")
        except:
            print("Can't stop -- no path")

class about(QMainWindow):
    def __init__(self, parent=None):
        super(about, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("about_box.ui", self).setFixedSize(606, 340)

class gui(QMainWindow):

    def __init__(self):
        super(gui, self).__init__()
        loadUi("mainwindow.ui", self).setFixedSize(807, 450)

        self.about_dialog = about(self)

        self.load_btn.clicked.connect(self.load_clicked)
        self.play_btn.clicked.connect(self.play_clicked)
        self.about_btn.clicked.connect(self.about_clicked)
        self.stop_btn.clicked.connect(self.stop_clicked)
        self.draw_btn.clicked.connect(self.draw_clicked)
        self.initUI()


    @pyqtSlot()
    def load_clicked(self):
        self.openFileNameDialog()

    def openFileNameDialog(self):
        global file_path
        options = QFileDialog.Options()
        #options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Video File", "",
        "Video Files (*.mp4 *.mov *avi);;All Files (*)", options=options)
        try:
            if file_path:
                print(file_path)
                self.initUI()
        except:
            print("Can't play from import")

    def play_clicked(self):
        try:
            print("Path exists {}".format(file_path))
            self.initUI()
        except:
            print("Play: no path exists")

    def stop_clicked(self):
        th = Thread(self)
        th.stop()

    def draw_clicked(self):
        print("draw")
        # global ref_pt, click_count
        #
        # if click_count == 0:
        #     if event == cv2.EVENT_LBUTTONUP:
        #         ref_pt = [(x, y - 10)]
        #         click_count += 1
        # elif click_count == 1:
        #     if event == cv2.EVENT_LBUTTONUP:
        #         ref_pt.append((x, y - 10))
        #         click_count = 0

    def set_image(self, image):
        self.video_label.setPixmap(QPixmap.fromImage(image))

    def initUI(self):
        th = Thread(self)
        try:
            th.get_path(file_path)
            th.changePixmap.connect(self.set_image)
            th.start()
        except:
            print("No path")

    def about_clicked(self):
        try:
            self.about_dialog.setWindowTitle('About SwiftFinder')
            self.about_dialog.show()
        except:
            print("No about box found")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = gui()
    main_window.setWindowTitle('SwiftFinder')
    main_window.show()

    sys.exit(app.exec_())




