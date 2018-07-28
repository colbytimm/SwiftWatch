import sys
import cv2
import resources #pyrcc5 -o resources.py resource.qrc
from enum import Enum
import threading

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
from PyQt5.QtGui import *
from PyQt5 import QtCore
import swiftCounter.swiftCounter as sc

width = 800
height = 450

ref_pt = []
click_count = 0

mainROI = ()
chimneyPoints = ()

startCondition = threading.Condition()

defaultSettings = sc.settings.copy()

# Translate point from the GUI Frame position to the original CV Frame position
def translatePointToCVFrame(guiFramePoint, guiFrameRect, cvFrameDims):
    xRatio = cvFrameDims[0] / guiFrameRect.width()
    yRatio = cvFrameDims[1] / guiFrameRect.height()

    # subtract x black space not covered by frame
    cvFramePointX = guiFramePoint[0] - guiFrameRect.x()
    cvFramePointX *= xRatio

    # subtract y black space not covered by frame
    cvFramePointY = guiFramePoint[1] - guiFrameRect.y()
    cvFramePointY *= yRatio

    return (int(cvFramePointX), int(cvFramePointY))

# Translate ROI from the GUI Frame position to the original CV Frame position
def translateROIToCVFrame(guiFrameROI, guiFrameRect, cvFrameDims):
    xRatio = cvFrameDims[0] / guiFrameRect.width()
    yRatio = cvFrameDims[1] / guiFrameRect.height()

    # subtract x black space not covered by frame
    x = guiFrameROI[0] - guiFrameRect.x()
    x *= xRatio

    # subtract y black space not covered by frame
    y = guiFrameROI[1] - guiFrameRect.y()
    y *= yRatio

    w = guiFrameROI[2] * xRatio
    h = guiFrameROI[3] * yRatio

    return (int(x), int(y), int(w), int(h))

class State(Enum):
    LOAD_VIDEO = 0
    DRAW_ROI = 1
    DRAW_CHIMNEY = 2
    RUNNING = 3
    STOPPED = 4

class Thread(QThread):
    changePixmap = pyqtSignal(QImage)
    state = State.LOAD_VIDEO

    def __init__(self, mainWindow):
        super(Thread, self).__init__()
        self.mainWindow = mainWindow

    def get_path(self, video_path):
        global path
        path = video_path

    def run(self):
        global mainROI
        global chimneyPoints

        self.state = State.RUNNING
        self.swiftCounter = sc.SwiftCounter(file_path, self.renderFrame, self.displayCount, startCondition)

        cvFrameDims = self.swiftCounter.getBigFrameDims()
        guiFrameRect = self.mainWindow.getCorrectRatioRect()

        # Translate the points to the correct coordinates in the CV Frame
        chimneyPointsX = translatePointToCVFrame(chimneyPoints[0], guiFrameRect, cvFrameDims)
        chimneyPointsY = translatePointToCVFrame(chimneyPoints[1], guiFrameRect, cvFrameDims)
        chimneyPoints = (chimneyPointsX, chimneyPointsY)
        mainROI = translateROIToCVFrame(mainROI, guiFrameRect, cvFrameDims)

        self.swiftCounter.setMainROI(mainROI)
        self.swiftCounter.setChimneyPoints(chimneyPoints)
        self.swiftCounter.start()

    def stop(self):
        if self.state == State.RUNNING:
            self.swiftCounter.stop()
            self.state = State.STOPPED

    def play(self):
        global startCondition
        if self.state == State.STOPPED:
            self.swiftCounter.play()
            with startCondition:
                startCondition.notifyAll()
            self.state = State.RUNNING

    def toggleZoomMainROI(self):
        if self.state != State.LOAD_VIDEO:
            # tacker is initialized
            self.swiftCounter.renderSmallFrame =  not self.swiftCounter.renderSmallFrame

    def toQtFormat(self, frame):
        rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        convertToQtFormat = QImage(rgbImage.data, rgbImage.shape[1], rgbImage.shape[0], QImage.Format_RGB888)
        #p = convertToQtFormat.scaled(826, 461, Qt.KeepAspectRatio)
        return convertToQtFormat

    def displayCount(self, count):
        self.mainWindow.lcdNumber.display(count)

    def renderFrame(self, frame):
        #self.changePixmap.emit(self.toQtFormat(frame))
        # super().currentFramePixmap = frame
        # super().setFrame()
        self.mainWindow.update_current_frame_pixmap(self.getPixmap(frame))
        self.mainWindow.update()

    def getPixmap(self, frame):
        return QPixmap.fromImage(self.toQtFormat(frame))

class About(QMainWindow):
    def __init__(self, parent=None):
        super(About, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("about_box.ui", self).setFixedSize(606, 340)

class Settings(QMainWindow):
    def __init__(self, parent=None):
        super(Settings, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("settings.ui", self).setFixedSize(350, 550)
        self.parent = parent

        self.tracker_combo.currentIndexChanged.connect(self.tracker_selection)
        self.bckgrnd_sub_combo.currentIndexChanged.connect(self.bckgrnd_sub_selection)
        self.erode_value.valueChanged.connect(self.erode_value_selection)
        self.dilate_value.valueChanged.connect(self.dilate_value_selection)
        self.video_checkbox.toggled.connect(self.video_checkbox_selection)
        self.prediction_checkbox.toggled.connect(self.prediction_checkbox_selection)
        self.bounding_checkbox.toggled.connect(self.bounding_checkbox_selection)
        self.empty_tracker_checkbox.toggled.connect(self.empty_tracker_checkbox_selection)
        self.reset_defaults_btn.clicked.connect(self.reset_defaults)

        self.reset_defaults()

    def tracker_selection(self):
        sc.settings[sc.Settings.TRACKER] = self.tracker_combo.currentIndex()

    def bckgrnd_sub_selection(self):
        sc.settings[sc.Settings.BACKGROUND_SUBTRACTOR] = self.bckgrnd_sub_combo.currentIndex()

    def erode_value_selection(self):
        sc.settings[sc.Settings.ERODE_ITERATIONS] = self.erode_value.value()

    def dilate_value_selection(self):
        sc.settings[sc.Settings.DILATE_ITERATIONS] = self.dilate_value.value()

    def prediction_checkbox_selection(self):
        sc.settings[sc.Settings.SHOW_PREDICTION_LINES] = self.prediction_checkbox.isChecked()

    def video_checkbox_selection(self):
        sc.settings[sc.Settings.SHOW_VIDEO] = self.video_checkbox.isChecked()
        if not sc.settings[sc.Settings.SHOW_VIDEO]:
            # black out the screen
            self.parent.currentFramePixmap = None

    def bounding_checkbox_selection(self):
        sc.settings[sc.Settings.SHOW_BOUNDING_BOXES] = self.bounding_checkbox.isChecked()

    def empty_tracker_checkbox_selection(self):
        sc.settings[sc.Settings.REMOVE_EMPTY_TRACKERS] = self.empty_tracker_checkbox.isChecked()

    def reset_defaults(self):
        print("setting defaults:", defaultSettings)
        self.tracker_combo.setCurrentIndex(defaultSettings[sc.Settings.TRACKER])
        self.bckgrnd_sub_combo.setCurrentIndex(defaultSettings[sc.Settings.BACKGROUND_SUBTRACTOR])
        self.erode_value.setValue(defaultSettings[sc.Settings.ERODE_ITERATIONS])
        self.dilate_value.setValue(defaultSettings[sc.Settings.DILATE_ITERATIONS])
        self.video_checkbox.setChecked(defaultSettings[sc.Settings.SHOW_VIDEO])
        self.prediction_checkbox.setChecked(defaultSettings[sc.Settings.SHOW_PREDICTION_LINES])
        self.bounding_checkbox.setChecked(defaultSettings[sc.Settings.SHOW_BOUNDING_BOXES])
        self.empty_tracker_checkbox.setChecked(defaultSettings[sc.Settings.REMOVE_EMPTY_TRACKERS])
        print(self.parent)
        self.update()
        self.parent.update()

class Export(QDialog):
    def __init__(self, parent=None):
        super(Export, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("CSV_exporter.ui", self).setFixedSize(395, 161)

        self.export_btn.clicked.connect(self.export_clicked)
        self.dont_export_btn.clicked.connect(self.dont_export_clicked)
        self.cancel_btn.clicked.connect(self.cancel_clicked)

    def export_clicked(self):
        print("Export")
        self.exportFileNameDialog()
        self.close()

    def dont_export_clicked(self):
        print("Don't export")
        self.close()

    def cancel_clicked(self):
        self.close()

    def exportFileNameDialog(self):
        global file_path
        options = QFileDialog.Options()
        #options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "",
        ".csv", options=options)
        # try:
        if file_path:
            print(file_path)
            main_window.trackerThread.swiftCounter.writeToCSV(file_path)
        # except:
        #     print("Can't export")

class Contour(QMainWindow):
    def __init__(self):
        super(Contour, self).__init__()
        loadUi("contourwindow.ui", self)

class Gui(QMainWindow):
    trackerThread = None

    def __init__(self):
        super(Gui, self).__init__()
        #loadUi("mainwindow.ui", self).setFixedSize(807, 450)
        loadUi("mainwindow.ui", self)#.setFixedSize(1050, 589)

        self.changePixmap = pyqtSignal(QImage)

        self.about_dialog = About(self)
        self.setting_dialog = Settings(self)
        self.export_dialog = Export(self)
        self.contour_window = Contour()

        self.load_btn.clicked.connect(self.load_clicked)
        self.play_btn.clicked.connect(self.play_clicked)
        self.about_btn.clicked.connect(self.about_clicked)
        self.stop_btn.clicked.connect(self.stop_clicked)
        #self.draw_btn.clicked.connect(self.draw_clicked)
        self.settings_btn.clicked.connect(self.settings_clicked)
        self.export_btn.clicked.connect(self.export_clicked)
        self.draw_btn.clicked.connect(self.draw_contour)
        self.zoom_btn.clicked.connect(self.toggle_zoom_main_ROI)
        self.finished_btn.clicked.connect(self.finished_clicked)

        self.finished_btn.setVisible(False)

        self.lcdNumber.display(0)

        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()

        self.state = State.LOAD_VIDEO
        self.trackerThread = Thread(self)
        self.trackerThread.changePixmap.connect(self.set_image)
        

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
        self.currentFramePixmap = framePixmap

    def export_clicked(self):
        try:
            self.export_dialog.setWindowTitle('Export to CSV')
            self.export_dialog.show()
        except:
            print("No export dialog found")

    def finished_clicked(self):
        global mainROI
        global chimneyPoints
        global startCondition

        self.finished_btn.setVisible(False)

        if self.state == State.DRAW_ROI:
            # set the main ROI
            x = self.begin.x()
            y = self.begin.y()
            w = self.end.x() - x
            h = self.end.y() - y

            mainROI = (x, y, w, h)

            print(self.begin, self.end)

            # update the state
            self.state = State.DRAW_CHIMNEY

        elif self.state == State.DRAW_CHIMNEY:
            # set the chimney points
            chimneyPoints = ((self.begin.x(), self.begin.y()), (self.end.x(), self.end.y()))

            # update the state and start tracking
            self.state = State.RUNNING
            self.trackerThread.start()

    def play_clicked(self):
        self.trackerThread.play()

    def stop_clicked(self):
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

        self.currentFramePixmap = self.trackerThread.getPixmap(frame)
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

    def draw_contour(self):
        try:
            print("contour clicked")
            self.contour_window.setWindowTitle('Contour View SwiftWatch')
            self.contour_window.show()
        except:
            print("No contour window found")

    def settings_clicked(self):
        try:
            print("settings clicked")
            self.setting_dialog.setWindowTitle('Settings SwiftWatch')
            self.setting_dialog.show()
        except:
            print("No settings window found")

    def paintEvent(self, event):
        qp = QPainter(self)
        if self.state == State.DRAW_ROI:
            self.display_text.setText("Select Region of Interest")
            # draw the frame
            qp.drawPixmap(self.getCorrectRatioRect(), self.currentFramePixmap)

            # draw the main ROI
            br = QBrush(QColor(0, 255, 0, 30))
            qp.setBrush(br)
            qp.drawRect(QtCore.QRect(self.begin, self.end))

        elif self.state == State.DRAW_CHIMNEY:
            self.display_text.setText("Select Entrance of Chimney")

            # draw the frame
            qp.drawPixmap(self.getCorrectRatioRect(), self.currentFramePixmap)

            # draw the main ROI
            roiBegin = QtCore.QPoint(mainROI[0], mainROI[1])
            roiEnd = QtCore.QPoint(mainROI[0] + mainROI[2], mainROI[1] + mainROI[3])
            br = QBrush(QColor(0, 255, 0, 30))
            qp.setBrush(br)
            qp.drawRect(QtCore.QRect(roiBegin, roiEnd))

            # draw the chimney line
            pen = QPen(Qt.red, 3)
            qp.setPen(pen)
            qp.drawLine(QtCore.QLine(self.begin, self.end))

        elif self.state == State.RUNNING:
            self.display_text.setText("")
            if self.currentFramePixmap is not None:
                qp.drawPixmap(self.getCorrectRatioRect(), self.currentFramePixmap)
            else:
                self.display_text.setText("The video is hidden, but we're still counting!")
                br = QBrush(QColor(255, 255, 255, 1))
                qp.setBrush(br)
                qp.drawRect(self.rect())

    def mousePressEvent(self, event):
        self.end = event.pos()
        self.begin = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.end = event.pos()
        if self.state == State.DRAW_ROI or self.state == State.DRAW_CHIMNEY:
            self.finished_btn.setVisible(True)

    def keyPressEvent(self, event):
        global mainROI
        global chimneyPoints
        global startCondition

        key = event.key()
        if self.state == State.DRAW_ROI:
            if key == QtCore.Qt.Key_Enter or key == QtCore.Qt.Key_Return:
                self.finished_btn.setVisible(False)
                # set the main ROI
                x = self.begin.x()
                y = self.begin.y()
                w = self.end.x() - x
                h = self.end.y() - y
                
                mainROI = (x,y,w,h)

                print(self.begin, self.end)

                # update the state
                self.state = State.DRAW_CHIMNEY

        elif self.state == State.DRAW_CHIMNEY:
            if key == QtCore.Qt.Key_Enter or key == QtCore.Qt.Key_Return:
                self.finished_btn.setVisible(False)
                # set the chimney points
                chimneyPoints = ((self.begin.x(), self.begin.y()), (self.end.x(), self.end.y()))

                # update the state and start tracking
                self.state = State.RUNNING
                self.trackerThread.start()

        elif self.trackerThread.state == State.STOPPED:
            # allow single frame skipping if stopped
            if key == QtCore.Qt.Key_Right:
                with startCondition:
                    startCondition.notifyAll()
        event.accept()

    def getCorrectRatioRect(self):
        correctRect = QRect()

        guiW = self.rect().width()
        guiH = self.rect().height()
        frameW = self.frameDims[0]
        frameH = self.frameDims[1]

        wRatio = frameW / guiW
        hRatio = frameH / guiH
        wRatioCorrected = abs(wRatio - 1)
        hRatioCorrected = abs(hRatio - 1)

        if wRatioCorrected <= hRatioCorrected:
            # Width is closer than height. Make the frame height the same as the gui 
            # height then adjust the width to preserve aspect ratio
            w = frameW / hRatio
            h = guiH
            x = (guiW - w) / 2
            y = 0
        else:
            # Height is closer than width. Make the frame width the same as the gui 
            # width then adjust the height to preserve aspect ratio
            w = guiW
            h = frameH / wRatio
            x = 0
            y = (guiH - h) / 2

        return QRect(x, y, w, h)

    def toggle_zoom_main_ROI(self):
        self.trackerThread.toggleZoomMainROI()



if __name__ == "__main__":
    global main_window
    app = QApplication(sys.argv)
    main_window = Gui()
    main_window.setWindowTitle('SwiftWatch')
    main_window.show()

    sys.exit(app.exec_())




