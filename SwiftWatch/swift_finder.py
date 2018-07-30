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

def getCorrectRatioRect(guiRect=None, getCurrentFrameDims=True):
    if guiRect is None:
        guiRect = main_window.rect()

    if getCurrentFrameDims and main_window.trackerThread.swiftCounter is not None:
        frameDims = main_window.trackerThread.swiftCounter.getCurrentFrameDims()
        if frameDims is None:
            frameDims = main_window.frameDims
    else:
        frameDims = main_window.frameDims

    correctRect = QRect()

    guiW = guiRect.width()
    guiH = guiRect.height()
    frameW = frameDims[0]
    frameH = frameDims[1]

    wRatio = frameW / guiW
    hRatio = frameH / guiH

    if wRatio <= hRatio:
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

class State(Enum):
    LOAD_VIDEO = 0
    DRAW_ROI = 1
    DRAW_CHIMNEY = 2
    RUNNING = 3
    STOPPED = 4

class Thread(QThread):
    changePixmap = pyqtSignal(QImage)
    state = State.LOAD_VIDEO
    swiftCounter = None

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
        self.swiftCounter = sc.SwiftCounter(file_path, self.renderFrames, self.displayCount, startCondition)

        cvFrameDims = self.swiftCounter.getBigFrameDims()
        guiFrameRect = getCorrectRatioRect()

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

    def forceStop(self):
        self.swiftCounter.forceStop = True

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

    def displayCount(self, count):
        self.mainWindow.lcdNumber.display(count)

    def renderFrames(self, mainFrame, contourFrame = None):
        pixmap = self.getPixmap(mainFrame, cv2.COLOR_BGR2RGB)
        self.mainWindow.update_current_frame_pixmap(pixmap)
        self.mainWindow.update()

        if contourFrame is not None:
            self.mainWindow.contour_window.update_current_frame_pixmap(self.getPixmap(contourFrame, cv2.COLOR_GRAY2RGB))
            self.mainWindow.contour_window.update()

    def getPixmap(self, frame, conversionType):
        rgbImage = cv2.cvtColor(frame, conversionType)
        convertToQtFormat = QImage(rgbImage.data, rgbImage.shape[1], rgbImage.shape[0], QImage.Format_RGB888)
        return QPixmap.fromImage(convertToQtFormat)


class About(QMainWindow):
    def __init__(self, parent=None):
        super(About, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("about_box.ui", self).setFixedSize(606, 340)

class Settings(QMainWindow):
    def __init__(self, parent=None):
        super(Settings, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("settings.ui", self).setFixedSize(350, 509)
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
        self.tracker_combo.setCurrentIndex(defaultSettings[sc.Settings.TRACKER])
        self.bckgrnd_sub_combo.setCurrentIndex(defaultSettings[sc.Settings.BACKGROUND_SUBTRACTOR])
        self.erode_value.setValue(defaultSettings[sc.Settings.ERODE_ITERATIONS])
        self.dilate_value.setValue(defaultSettings[sc.Settings.DILATE_ITERATIONS])
        self.video_checkbox.setChecked(defaultSettings[sc.Settings.SHOW_VIDEO])
        self.prediction_checkbox.setChecked(defaultSettings[sc.Settings.SHOW_PREDICTION_LINES])
        self.bounding_checkbox.setChecked(defaultSettings[sc.Settings.SHOW_BOUNDING_BOXES])
        self.empty_tracker_checkbox.setChecked(defaultSettings[sc.Settings.REMOVE_EMPTY_TRACKERS])
        self.update()
        self.parent.update()

class Export(QDialog):
    def __init__(self, parent=None):
        super(Export, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("CSV_exporter.ui", self).setFixedSize(395, 161)

        self.error_export_dialog = ErrorExportDialog(self)

        self.export_btn.clicked.connect(self.export_clicked)
        self.cancel_btn.clicked.connect(self.cancel_clicked)

    def export_clicked(self):
        self.exportFileNameDialog()
        self.close()

    def cancel_clicked(self):
        self.close()

    def exportFileNameDialog(self):
        global file_path
        options = QFileDialog.Options()
        #options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "",
        "CSV (*.csv)", options=options)
        try:
            if file_path:
                if main_window.trackerThread.swiftCounter.writeToCSV(file_path) == False:
                    try:
                        self.error_export_dialog.setWindowTitle("Error on Export")
                        self.error_export_dialog.show()
                    except:
                        print("No export dialog found")

        except:
            try:
                self.error_export_dialog.setWindowTitle("Error on Export")
                self.error_export_dialog.show()
            except:
                print("No export dialog found")
            print("Can't export")

class ErrorExportDialog(QDialog):
    def __init__(self, parent=None):
        super(ErrorExportDialog, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        loadUi("error_export_dialog.ui", self).setFixedSize(538, 177)

        self.ok_btn.clicked.connect(self.ok_clicked)

    def ok_clicked(self):
        self.close()

class Contour(QMainWindow):
    def __init__(self):
        super(Contour, self).__init__()
        loadUi("contourwindow.ui", self)
        self.setWindowTitle('Contour View SwiftWatch')
        self.currentFramePixmap = None

    def update_current_frame_pixmap(self, framePixmap):
        self.currentFramePixmap = framePixmap

    def paintEvent(self, event):
        if self.currentFramePixmap is not None:
            qp = QPainter(self)
            qp.drawPixmap(getCorrectRatioRect(self.rect()), self.currentFramePixmap)

    def keyPressEvent(self, event):
        main_window.keyPressEvent(event)

    def closeEvent(self, event):
        # stop rendering the contours frame
        sc.settings[sc.Settings.SHOW_CONTOURS] = False
        event.accept()

class MainWindow(QMainWindow):
    trackerThread = None

    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("mainwindow.ui", self)

        self.changePixmap = pyqtSignal(QImage)

        self.about_dialog = About(self)
        self.setting_dialog = Settings(self)
        self.export_dialog = Export(self)
        self.contour_window = Contour()

        self.load_btn.clicked.connect(self.load_clicked)
        self.play_btn.clicked.connect(self.play_clicked)
        self.about_btn.clicked.connect(self.about_clicked)
        self.stop_btn.clicked.connect(self.stop_clicked)
        self.settings_btn.clicked.connect(self.settings_clicked)
        self.export_btn.clicked.connect(self.export_clicked)
        self.draw_btn.clicked.connect(self.toggle_contour_window)
        self.zoom_btn.clicked.connect(self.toggle_zoom_main_ROI)
        self.finished_btn.clicked.connect(self.finished_clicked)

        self.lcdNumber.display(0)

        self.finished_btn.setVisible(False)
        self.play_btn.setVisible(False)
        self.stop_btn.setVisible(False)
        self.lcdNumber.setVisible(False)
        self.export_btn.setVisible(False)
        self.zoom_btn.setVisible(False)
        self.draw_btn.setVisible(False)

        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()

        self.state = State.LOAD_VIDEO
        self.trackerThread = Thread(self)
        self.trackerThread.changePixmap.connect(self.set_image)

    @pyqtSlot()
    def load_clicked(self):
        if self.state == State.RUNNING:
            # DISPLAY WARNING THAT CURRENT VIDEO WILL CLOSE AND RESULTS WILL BE LOST
            pass
        self.openFileNameDialog()

    def openFileNameDialog(self):
        global file_path
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Video File", "",
        "Video Files (*.mp4 *.mov *avi);;All Files (*)", options=options)
        try:
            if file_path:
                self.initUI(file_path)
        except Exception as e:
            print("Failed in openFileNameDialog\n", e)

    def update_current_frame_pixmap(self, framePixmap):
        self.currentFramePixmap = framePixmap

    def export_clicked(self):
        try:
            self.export_dialog.setWindowTitle('Export to CSV')
            self.export_dialog.show()
        except Exception as e:
            print("No export dialog found\n", e)

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

            # update the state
            self.state = State.DRAW_CHIMNEY

        elif self.state == State.DRAW_CHIMNEY:
            # set the chimney points
            chimneyPoints = ((self.begin.x(), self.begin.y()), (self.end.x(), self.end.y()))

            self.play_btn.setVisible(True)
            self.stop_btn.setVisible(True)
            self.lcdNumber.setVisible(True)
            self.export_btn.setVisible(True)
            self.zoom_btn.setVisible(True)
            self.draw_btn.setVisible(True)

            # update the state and start tracking
            self.state = State.RUNNING
            self.trackerThread.start()

    def play_clicked(self):
        self.trackerThread.play()

    def stop_clicked(self):
        self.trackerThread.stop()

    def set_image(self, image):
        self.video_label.setPixmap(QPixmap.fromImage(image))

    def initUI(self, file_path):
        if self.state == State.RUNNING:
            self.state = State.LOAD_VIDEO
            self.lcdNumber.display(0)
            self.trackerThread.forceStop()
            self.trackerThread = Thread(self)

        # Display the first frame
        cap = cv2.VideoCapture(file_path)
        ret, frame = cap.read()

        if not ret:
            print("Failed to get first frame.")

        self.currentFramePixmap = self.trackerThread.getPixmap(frame, cv2.COLOR_BGR2RGB)
        self.frameDims = (len(frame[0]), len(frame))

        # paint the frame
        self.update()

        # update the state
        self.state = State.DRAW_ROI
            

    def about_clicked(self):
        try:
            self.about_dialog.setWindowTitle('About')
            self.about_dialog.show()
        except:
            print("No about box found")

    def toggle_contour_window(self):
        if sc.settings[sc.Settings.SHOW_CONTOURS]:
            self.contour_window.close()
        else:
            sc.settings[sc.Settings.SHOW_CONTOURS] = True
            self.contour_window.show()

    def settings_clicked(self):
        try:
            print("settings clicked")
            self.setting_dialog.setWindowTitle('Settings')
            self.setting_dialog.show()
        except:
            print("No settings window found")

    def paintEvent(self, event):
        qp = QPainter(self)
        if self.state == State.DRAW_ROI:
            self.display_text.setText("Select Region of Interest")
            # draw the frame
            qp.drawPixmap(getCorrectRatioRect(getCurrentFrameDims=False), self.currentFramePixmap)

            # draw the main ROI
            br = QBrush(QColor(0, 255, 0, 30))
            qp.setBrush(br)
            qp.drawRect(QtCore.QRect(self.begin, self.end))

        elif self.state == State.DRAW_CHIMNEY:
            self.display_text.setText("Select Entrance of Chimney")

            # draw the frame
            qp.drawPixmap(getCorrectRatioRect(getCurrentFrameDims=False), self.currentFramePixmap)

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
                qp.drawPixmap(getCorrectRatioRect(), self.currentFramePixmap)
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

                # fix point ordering
                if self.begin.x() <= self.end.x():
                    x = self.begin.x()
                    w = self.end.x() - x
                else:
                    x = self.end.x()
                    w = self.begin.x() - x

                if self.begin.y() <= self.end.y():
                    y = self.begin.y()
                    h = self.end.y() - y
                else:
                    y = self.end.y()
                    h = self.begin.y() - y

                # 5 pixels for a min width and height
                if w > 5 and h > 5:
                    mainROI = (x,y,w,h)
                    self.state = State.DRAW_CHIMNEY

        elif self.state == State.DRAW_CHIMNEY:
            if key == QtCore.Qt.Key_Enter or key == QtCore.Qt.Key_Return:
                self.finished_btn.setVisible(False)
                self.play_btn.setVisible(True)
                self.stop_btn.setVisible(True)
                self.lcdNumber.setVisible(True)
                self.export_btn.setVisible(True)
                self.zoom_btn.setVisible(True)
                self.draw_btn.setVisible(True)

                # fix point ordering
                if self.begin.x() <= self.end.x():
                    begin = self.begin
                    end = self.end
                else:
                    print("swapping chimney points")
                    begin = self.end
                    end = self.begin

                # set the chimney points
                chimneyPoints = ((begin.x(), begin.y()), (end.x(), end.y()))

                # update the state and start tracking
                self.state = State.RUNNING
                self.trackerThread.start()

        elif self.trackerThread.state == State.STOPPED:
            # allow single frame skipping if stopped
            if key == QtCore.Qt.Key_Right:
                with startCondition:
                    startCondition.notifyAll()
            elif key == QtCore.Qt.Key_Space:
                self.trackerThread.play()

        elif self.trackerThread.state == State.RUNNING:
            if key == QtCore.Qt.Key_Space:
                self.trackerThread.stop()

        event.accept()

    def toggle_zoom_main_ROI(self):
        self.trackerThread.toggleZoomMainROI()



if __name__ == "__main__":
    global main_window
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.setWindowTitle('SwiftWatch')
    main_window.show()

    sys.exit(app.exec_())




