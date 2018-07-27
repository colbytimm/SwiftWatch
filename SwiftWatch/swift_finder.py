import sys
import cv2
#import imutils
import resources #pyrcc5 -o resources.py resource.qrc
from enum import Enum
import threading
import math

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from PyQt5.QtGui import *
from PyQt5 import QtCore
import swiftCounter.swiftCounter as sc
import random

width = 800
height = 450

ref_pt = []
click_count = 0

mainROI = ()
chimneyPoints = ()

startCondition = threading.Condition()

class State(Enum):
    LOAD_VIDEO = 0
    DRAW_ROI = 1
    DRAW_CHIMNEY = 2
    RUNNING = 3
    STOPPED = 4

class Thread(QThread):
    changePixmap = pyqtSignal(QImage)

    def __init__(self, mainWindow):
        super(Thread, self).__init__()
        self.mainWindow = mainWindow
        print(self.mainWindow)

    def get_path(self, video_path):
        global path
        path = video_path

    def run(self):
        global mainROI
        global chimneyPoints

        # Get the main bounding box...
        mainBBox = (440, 178, 827, 556)

        # Get the chimney points...
        chimneyPoints = ((755, 693), (869, 687))

        # Convert to points to the correct position...

        self.state = State.RUNNING
        self.swiftCounter = sc.SwiftCounter(file_path, self.renderFrame, startCondition)
        self.swiftCounter.setMainROI(mainBBox)
        self.swiftCounter.setChimneyPoints(chimneyPoints)
        self.swiftCounter.start()

    def stop(self):
        if self.state == State.RUNNING:
            self.swiftCounter.stop()
            self.state = State.STOPPED

    def play(self):
        global startCondition
        if self.state == State.STOPPED:
            with startCondition:
                startCondition.notifyAll()
            self.state = State.RUNNING

    def toQtFormat(self, frame):
        rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        convertToQtFormat = QImage(rgbImage.data, rgbImage.shape[1], rgbImage.shape[0], QImage.Format_RGB888)
        #p = convertToQtFormat.scaled(826, 461, Qt.KeepAspectRatio)
        return convertToQtFormat

    def renderFrame(self, frame):
        #self.changePixmap.emit(self.toQtFormat(frame))
        # super().firstFramePixmap = frame
        # super().setFrame()
        self.mainWindow.update_current_frame_pixmap(self.getPixmap(frame))
        self.mainWindow.update()


    def getPixmap(self, frame):
        return QPixmap.fromImage(self.toQtFormat(frame))


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

class gui(QMainWindow):
    app_name = "SwiftWatch"
    trackerThread = None

    def __init__(self):
        super(gui, self).__init__()
        #loadUi("mainwindow.ui", self).setFixedSize(807, 450)
        loadUi("mainwindow.ui", self)#.setFixedSize(1050, 589)
        # dockWidget = self.findChild("dockWidget_2")
        # print(dockWidget)
        self.changePixmap = pyqtSignal(QImage)

        self.about_dialog = about(self)
        self.setting_dialog = settings(self)

        self.load_btn.clicked.connect(self.load_clicked)
        self.play_btn.clicked.connect(self.play_clicked)
        self.about_btn.clicked.connect(self.about_clicked)
        self.stop_btn.clicked.connect(self.stop_clicked)
        self.draw_btn.clicked.connect(self.draw_clicked)
        self.settings_btn.clicked.connect(self.settings_clicked)

        self.lcdNumber.display(random.randint(1,18))

        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()

        self.trackerThread = Thread(self)
        self.trackerThread.changePixmap.connect(self.set_image)
        self.state = State.LOAD_VIDEO


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
                self.initUI(file_path)
        except:
            print("Can't play from import")

    def update_current_frame_pixmap(self, framePixmap):
        self.firstFramePixmap = framePixmap

    def play_clicked(self):
        if not self.trackerThread:
            return
        self.trackerThread.play()

    def stop_clicked(self):
        if not self.trackerThread:
            return
        self.trackerThread.stop()

    def draw_clicked(self):
        # draw enterence to chimney here
        #self.showFullScreen()
        print("draw")

    def set_image(self, image):
        self.video_label.setPixmap(QPixmap.fromImage(image))

    def initUI(self, file_path):
        # Display the first frame
        cap = cv2.VideoCapture(file_path)
        ret, frame = cap.read()

        if not ret:
            print("Failed to get first frame.")

        self.firstFramePixmap = self.trackerThread.getPixmap(frame)
        self.frameDims = (len(frame[0]), len(frame))

        # paint the frame
        self.update()

        # update the state
        self.state = State.DRAW_ROI
            

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

    def paintEvent(self, event):
        qp = QPainter(self)
        if self.state == State.DRAW_ROI:
            qp.drawPixmap(self.rect(), self.firstFramePixmap)
            br = QBrush(QColor(0, 255, 0, 30))
            qp.setBrush(br)
            qp.drawRect(QtCore.QRect(self.begin, self.end))
        elif self.state == State.DRAW_CHIMNEY:
            qp.drawPixmap(self.rect(), self.firstFramePixmap)
            pen = QPen(Qt.red, 3)
            qp.setPen(pen)
            qp.drawLine(QtCore.QLine(self.begin, self.end))
        elif self.state == State.RUNNING:
            print(self.frameDims)
            #rect = QRect(0, 0, self.frameDims[0], self.frameDims[1])
            rect = self.getCorrectRatioRect()
            print(self.rect())
            qp.drawPixmap(rect, self.firstFramePixmap)

    def mousePressEvent(self, event):
        self.end = event.pos()
        self.begin = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end = event.pos()

    def keyPressEvent(self, event):
        global mainROI
        global chimneyPoints

        print("KEY PRESS", event.key())
        key = event.key()
        if self.state == State.DRAW_ROI:
            if key == QtCore.Qt.Key_Enter or key == QtCore.Qt.Key_Return:
                # set the main ROI
                x = self.begin.x()
                y = self.begin.y()
                w = self.end.x() - x
                h = self.end.y() - y
                
                self.mainROI = (x,y,w,h)
                print("MAIN ROI SET")
                print("begin:", self.begin, "end:", self.end, "ROI:", self.mainROI)

                # update the state
                self.state = State.DRAW_CHIMNEY

        elif self.state == State.DRAW_CHIMNEY:
            if key == QtCore.Qt.Key_Enter or key == QtCore.Qt.Key_Return:
                # set the chimney points
                chimneyPoints = ((self.begin.x(), self.begin.y()), (self.end.x(), self.end.y()))
                print("CHIMNEY POINTS SET")
                print("Chimney Points:", chimneyPoints)

                # update the state and start tracking
                self.state = State.RUNNING
                self.trackerThread.start()

        event.accept()

    def getCorrectRatioRect(self):
        guiW = self.rect().width()
        guiH = self.rect().height()
        frameW = self.frameDims[0]
        frameH = self.frameDims[1]

        correctRect = QRect()

        wRatio = frameW / guiW
        hRatio = frameH / guiH

        wRatioCorrected = abs(wRatio - 1)
        hRatioCorrected = abs(hRatio - 1)

        if wRatioCorrected <= hRatioCorrected:
            # width is closer than height
            # make the height the same then adjust the width
            w = frameW / hRatio
            h = guiH
            x = (guiW - w) / 2
            y = 0

        else:
            w = guiW
            h = frameH / wRatio
            x = 0
            y = (guiH - h) / 2


        return QRect(x, y, w, h)





if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = gui()
    main_window.setWindowTitle('SwiftWatch')
    main_window.show()

    sys.exit(app.exec_())




