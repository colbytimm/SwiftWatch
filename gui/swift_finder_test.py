

import sys
import random
import cv2
#import imutils
import resources #pyrcc5 -o resources.py resource.qrc

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from PyQt5.QtGui import *
from PyQt5 import QtCore
import swiftCounter.swiftCounter as sc
import PyQt5

width = 800
height = 450

ref_pt = []
click_count = 0

class Point:
    def __init__(self):
        self.x1 = None
        self.y1 = None
        self.x2 = None
        self.y2 = None


class about(QMainWindow):
    def __init__(self, parent=None):
        super(about, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("about_box.ui", self).setFixedSize(606, 340)

class settings(QMainWindow):
    def __init__(self, parent=None):
        super(settings, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("settings.ui", self).setFixedSize(350, 550)

        self.tracker_combo.currentIndexChanged.connect(self.tracker_selection)
        self.bckgrnd_sub_combo.currentIndexChanged.connect(self.bckgrnd_sub_selection)
        self.erode_value.valueChanged.connect(self.erode_value_selection)
        self.dilate_value.valueChanged.connect(self.dilate_value_selection)
        self.contour_checkbox.toggled.connect(self.contour_checkbox_selection)
        self.video_checkbox.toggled.connect(self.video_checkbox_selection)
        self.prediction_checkbox.toggled.connect(self.prediction_checkbox_selection)
        self.bounding_checkbox.toggled.connect(self.bounding_checkbox_selection)
        self.empty_tracker_checkbox.toggled.connect(self.empty_tracker_checkbox_selection)
        self.reset_defaults_btn.clicked.connect(self.reset_defaults_clicked)

    def tracker_selection(self):
        # set tracker here
        print(self.tracker_combo.currentText())

    def bckgrnd_sub_selection(self):
        # set background subtraction here
        print(self.bckgrnd_sub_combo.currentText())

    def erode_value_selection(self):
        # set erode value here
        print(self.erode_value.value())

    def dilate_value_selection(self):
        # set erode value here
        print(self.dilate_value.value())

    def contour_checkbox_selection(self):
        # set contour view here
        if self.contour_checkbox.isChecked() == True:
            print("Contour view selected")
        else:
            print("Not using contour view")

    def prediction_checkbox_selection(self):
        # set contour view here
        if self.prediction_checkbox.isChecked() == True:
            print("Prediction view selected")
        else:
            print("Not using prediction view")

    def video_checkbox_selection(self):
        # set contour view here
        if self.video_checkbox.isChecked() == True:
            print("Video view removed selected")
        else:
            print("Video view shown")

    def bounding_checkbox_selection(self):
        # set contour view here
        if self.bounding_checkbox.isChecked() == True:
            print("Bounding view selected")
        else:
            print("Not using bounding view")

    def empty_tracker_checkbox_selection(self):
        # set contour view here
        if self.empty_tracker_checkbox.isChecked() == True:
            print("Remove empty tracker selected")
        else:
            print("Using empty tracker")

    def reset_defaults_clicked(self):
        print("reset defaults")

    def reset_defaults(self):
        self.prediction_checkbox.setChecked(False)
        self.erode_value.setText("0")

class GraphicsScene(QGraphicsScene):
    def __init__(self, parent=None):
        QGraphicsScene.__init__(self, parent)
        self.opt = ""
        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()

    def setOption(self, opt):
        self.opt = opt

    def paintEvent(self, event):
        qp = QPainter(self)
        br = QBrush(QColor(100, 10, 10, 100))
        qp.setBrush(br)
        if self.opt == "Rect":
            qp.drawRect(QtCore.QRect(self.begin, self.end))
            print("im here")

        elif self.opt == "Line":
            qp.drawLine(QtCore.QLine(self.begin, self.end))

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        print(event.pos())
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        print(event.pos())


class gui(QMainWindow):
    app_name = "SwiftWatch"
    x1 = None
    y1 = None
    x2 = None
    y2 = None

    def __init__(self):
        super(gui, self).__init__()
        loadUi("mainwindow.ui", self).setFixedSize(807, 450)

        # self.begin = QtCore.QPoint()
        # self.end = QtCore.QPoint()

        self.about_dialog = about(self)
        self.setting_dialog = settings(self)

        self.load_btn.clicked.connect(self.load_clicked)
        self.play_btn.clicked.connect(self.play_clicked)
        self.about_btn.clicked.connect(self.about_clicked)
        self.stop_btn.clicked.connect(self.stop_clicked)
        self.draw_btn.clicked.connect(self.draw_clicked)
        self.settings_btn.clicked.connect(self.settings_clicked)

        self.initUI()

        self.scene = GraphicsScene(self)
        self.opt = ""
        self.scene.setOption(self.opt)


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
        except:
            print("Can't play from import")

    def play_clicked(self):
        try:
            if path:
                print("Path exists {}".format(file_path))

        except:
            print("Play: no path exists")

    def stop_clicked(self):
        print('stop')

    def draw_clicked(self):
        # draw enterence to chimney here
        self.opt = "Rect"
        self.scene.setOption(self.opt)
        print(self.opt)
        print("draw")

    def set_image(self, image):
        self.video_label.setPixmap(QPixmap.fromImage(image))

    def initUI(self):
        try:
            self.swiftCounter = sc.SwiftCounter(file_path)
            self.get_path(file_path)
            self.run()

        except:
            print("No path")

    def get_path(self, video_path):
        global path
        path = video_path

    def run(self):
        print('run')
        # frame = self.swiftCounter.currentFrame
        #
        # rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # convertToQtFormat = QImage(rgbImage.data, rgbImage.shape[1], rgbImage.shape[0], QImage.Format_RGB888)
        # p = convertToQtFormat.scaled(826, 461, Qt.KeepAspectRatio)
        # self.changePixmap.emit(p)

    def about_clicked(self):
        try:
            self.about_dialog.setWindowTitle('About SwiftWatch')
            self.about_dialog.show()
        except:
            print("No about box found")

    def settings_clicked(self):
        try:
            print("settings clicked")
            self.setting_dialog.setWindowTitle('Settings SwiftWatch')
            self.setting_dialog.show()
        except:
            print("No settings box found")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = gui()
    main_window.setWindowTitle('SwiftWatch')
    main_window.show()

    sys.exit(app.exec_())




