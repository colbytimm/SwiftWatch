import numpy as np
import cv2 as cv
import swiftCounter.customTracker as ct
import swiftCounter.swiftHelper as sh
from datetime import datetime, timedelta
import csv
import threading
from enum import Enum

class Settings(Enum):
    TRACKER = 0
    BACKGROUND_SUBTRACTOR = 1
    ERODE_ITERATIONS = 2
    DILATE_ITERATIONS = 3
    SHOW_CONTOURS = 4
    SHOW_VIDEO = 5
    SHOW_PREDICTION_LINES = 6
    SHOW_BOUNDING_BOXES = 7
    REMOVE_EMPTY_TRACKERS = 8

settings = {
    Settings.TRACKER: 0,
    Settings.BACKGROUND_SUBTRACTOR: 0,
    Settings.ERODE_ITERATIONS: 1,
    Settings.DILATE_ITERATIONS: 1,
    Settings.SHOW_CONTOURS: False,
    Settings.SHOW_VIDEO: True,
    Settings.SHOW_PREDICTION_LINES: True,
    Settings.SHOW_BOUNDING_BOXES: True,
    Settings.REMOVE_EMPTY_TRACKERS: True
}

class SwiftCounter:

	mainFrameName = 'Main Frame'
	maskFrameName = 'Mask Frame'
	currentBigFrame = None
	currentSmallFrame = None

	instructionTextColour = (204, 51, 0)

	showFrames = True
	frameByFrame = False
	renderSmallFrame = False

	erodeIterations = 1
	dilateIterations = 1

	imageScale = 0.5

	# points relate to position on the small frame (main bounding box)
	chimneyPoints = []
	drawingChimneyLine = False

	# 40 min area seems to work okay
	minContourArea = 40
	maxContourArea = 160
	maxStaleCount = 3
	removeEmptyTrackers = True
	dropContourOutsideSizeRange = False

	# determines if trackers should be created for countours inside
	# existing 'large' bounding boxes
	# if False, the 'shrunk' bounding box will be used instead
	ignoreContoursInLargeBoundingBox = False

	extraBoxSize = 25

	enteredChimneyCount = 0
	enteredChimneyCountFromPrediction = 0
	enteredChimneyCountFromLostAboveChimney = 0
	exitedChimneyCount = 0

	totalTrackersCreated = 0
	cvTrackerIndex = 0
	trackers = []

	bigFrameCols = 0
	bigFrameRows = 0
	smallFrameCols = 0
	smallFrameRows = 0

	_stop = False
	startCondition = None

	cachedTimeStamps = []

	showPredictionLines = True


	def __init__(self, videoPath, renderFunc, displayCountFunc, startCondition, backgroundSubtractor=1):
		self.videoPath = videoPath
		self.renderFunc = renderFunc
		self.startCondition = startCondition
		self.displayCountFunc = displayCountFunc
		self.setBackgroundSubtractor(backgroundSubtractor)

		self.videoCapture = cv.VideoCapture(videoPath)

		ret, self.currentBigFrame = self.videoCapture.read()

		if not ret:
			print('Failed to read first frame - aborting program.')
			quit() # Probably change this to display an error message

		# always render the big frame first
		self.renderFunc(self.currentBigFrame)
		self.bigFrameRows = len(self.currentBigFrame)
		self.bigFrameCols = len(self.currentBigFrame[0])

	def updateSetting(self, setting, value):
		settings[setting] = value

	# Convert to correct format and render in gui
	def renderMainFrame(self):
		if self.renderSmallFrame:
			self.renderFunc(self.currentSmallFrame)
		else:
			self.renderFunc(self.currentBigFrame)

	def getBigFrameDims(self):
		return (self.bigFrameCols, self.bigFrameRows)

	def setBackgroundSubtractor(self, index):
		if index == 0:
			self.backgroundSubtractor = cv.createBackgroundSubtractorMOG()
		elif index == 1:
			self.backgroundSubtractor = cv.createBackgroundSubtractorMOG2()

	def createCVTracker(self):
		if self.cvTrackerIndex == 0:
			return cv.TrackerMOSSE_create()
		elif self.cvTrackerIndex == 1:
			return cv.TrackerCSRT_create()

		#cvTracker = cv.TrackerBoosting_create()
		#cvTracker = cv.TrackerGOTURN_create()
		#cvTracker = cv.TrackerKCF_create()
		#cvTracker = cv.TrackerMedianFlow_create()
		#cvTracker = cv.TrackerMIL_create()
		#cvTracker = cv.TrackerTLD_create()

	def setMainROI(self, mainBBox):
		self.mainBBox = mainBBox
		self.smallFrameCols = mainBBox[2]
		self.smallFrameRows = mainBBox[3]
		sh.drawBoundingBox(self.currentBigFrame, self.mainBBox)
		# always render the big frame here
		self.renderFunc(self.currentBigFrame)

	def setChimneyPoints(self, chimneyPoints):
		# translate the line to the position in the small frame (main bounding box)
		self.chimneyPoints.append((chimneyPoints[0][0] - self.mainBBox[0], chimneyPoints[0][1] - self.mainBBox[1]))
		self.chimneyPoints.append((chimneyPoints[1][0] - self.mainBBox[0], chimneyPoints[1][1] - self.mainBBox[1]))
		self.drawChimneyLine()

		# always render the big frame here
		self.renderFunc(self.currentBigFrame)
		

	def drawChimneyLine(self):
		cv.line(self.currentSmallFrame, self.chimneyPoints[0], self.chimneyPoints[1], (250, 0, 1), 2)

	def updateSmallFrame(self):
			# get the small frame from the bounding box
			self.currentSmallFrame = self.currentBigFrame[int(self.mainBBox[1]):int(self.mainBBox[1]+self.mainBBox[3]), \
				int(self.mainBBox[0]):int(self.mainBBox[0]+self.mainBBox[2])]

	def cleanup(self):
		self.videoCapture.release()

	def stop(self):
		self._stop = True

	def play(self):
		self._stop = False

	def start(self):
		self.countSwifts()

	def cacheTimeStamp(self, current_frame, fps, videoPath):
		# Caches time stamps for each bird
		self.time = self.getTimeStamp(current_frame, fps, videoPath)
		self.cachedTimeStamps.append(self.time)

	def getTimeStamp(self, current_frame, fps, videoPath):
		# This function takes the video start time and adds the currenrt seconds that have passed to it
		self.videoString = videoPath.split("/")
		self.videoStringLen = len(self.videoString) - 1
		self.videoName = self.videoString[self.videoStringLen].split("_")[1].split('.mov')[0]

		self.datetime_object = datetime.strptime(self.videoName, '%Y%m%d%H%M%S')
		self.current_time_object = int(datetime.fromtimestamp(int(current_frame / fps)).strftime('%H%M%S'))
		self.datetime_object += timedelta(seconds=self.current_time_object)

		return self.datetime_object.time()

	def getVideoName(self, videoPath):
		videoString = videoPath.split("/")
		videoStringLen = len(videoString) - 1
		videoName = videoString[videoStringLen]
		return videoName

	def writeToCSV(self, filePath, videoPath):
		self.videoName = self.getVideoName(videoPath)
		self.writeToCSV = [["Filename","Time","Swift Entering"]]
		for num in range(len(self.cachedTimeStamps)):
			self.writeToCSV.append([self.videoName,self.cachedTimeStamps[num],"1"])

		self.myFile = open(filePath, 'w')
		with self.myFile:
			self.writer = csv.writer(self.myFile)
			self.writer.writerows(self.myData)

	def countSwifts(self):
		count = 0
		fps = self.videoCapture.get(cv.CAP_PROP_FPS)

		while True:
			ret, self.currentBigFrame = self.videoCapture.read()

			if not ret:
				break

			self.updateSmallFrame()

			# convert to greyscale and blur
			maskFrame = cv.cvtColor(self.currentSmallFrame, cv.COLOR_BGR2GRAY)
			maskFrame = cv.GaussianBlur(maskFrame, (11, 11), 0)

			# get the foreground mask 
			maskFrame = self.backgroundSubtractor.apply(maskFrame)

			# perform a series of erosions and dilations to remove
			# any small blobs of noise from the thresholded image
			maskFrame = cv.erode(maskFrame, None, iterations=self.erodeIterations)
			maskFrame = cv.dilate(maskFrame, None, iterations=self.dilateIterations)

			# find contours and draw then on the main frame
			contoursFrame, contours, hierarchy = cv.findContours(maskFrame, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
			#cv.drawContours(self.currentSmallFrame, contours, -1,  (0, 255, 0), 1);

			self.updateTrackers(maskFrame, contours)
			self.findNewContours(maskFrame, contours)

			if self.showFrames:
				# draw bounding box and chimney line
				sh.drawBoundingBox(self.currentBigFrame, self.mainBBox)
				self.drawChimneyLine()

				# render the main frame in the gui
				self.renderMainFrame()

			if self._stop:
				with self.startCondition:
					self.startCondition.wait()

			count += 1

			#check if video is finished
			k = cv.waitKey(1) & 0xff
			if k == 27 or k == ord('q'):
				break

		print("LOOP ENDED")

		# print('Total amount of birds entering:', self.enteredChimneyCount)
		# print('From prediction:', self.enteredChimneyCountFromPrediction)
		# print('From lost above chimney:', self.enteredChimneyCountFromLostAboveChimney)
		# print('Total amount of birds exiting:', self.exitedChimneyCount)
		# print('Total trackers created:', self.totalTrackersCreated)


	def updateTrackers(self, maskFrame, contours):
			for tracker in self.trackers:
				wasLocated = tracker.update(maskFrame)

				# if not wasLocated and tracker.lostNewBirdJustAboveChimney(chimneyPoints):
				# 	# assume the bird went in
				# 	enteredChimneyCount +=1
				# 	enteredChimneyCountFromLostAboveChimney += 1

				if tracker.getStaleCount() >= self.maxStaleCount:
					self.trackers.remove(tracker)
					continue

				# guard against false positivies to preserve cpu resources
				# remove trackers with empty bounding boxes
				# is not necessary for most trackers (but useful for MIL)
				if self.removeEmptyTrackers and not tracker.containsContour(contours, self.dropContourOutsideSizeRange, self.minContourArea, self.maxContourArea):
						self.trackers.remove(tracker)
						continue

				if self.showFrames:
					if settings[Settings.SHOW_BOUNDING_BOXES]:
						#tracker.drawBbox(maskFrame, (255,0,0))
						tracker.drawShrunkBbox(maskFrame, (255,0,0))
						#tracker.drawBbox(self.currentSmallFrame, (255,0,0))
						tracker.drawShrunkBbox(self.currentSmallFrame, (255,0,0))

					if self.showPredictionLines:
						# draw the line to the predicted point
						point = tracker.getPoint()
						ppoint = tracker.predictNextPoint()
						if point is not None and ppoint is not None:
							point = (int(point[0]), int(point[1]))
							ppoint = (int(ppoint[0]), int(ppoint[1]))
							cv.line(self.currentSmallFrame, point, ppoint, (0, 255, 0), 1)


				if tracker.enteredChimney(self.chimneyPoints):
					self.enteredChimneyCount += 1
					self.enteredChimneyCountFromPrediction += 1
					print('ENTERED CHIMNEY, count:', self.enteredChimneyCount)
					self.displayCountFunc(self.enteredChimneyCount)

				# if tracker.exitedChimney(chimneyPoints):
				# 	exitedChimneyCount +=1
				# 	print('\nEXITED CHIMNEY, count:', exitedChimneyCount, '\n')


	# Creates a tracker when a new contour is found
	def findNewContours(self, maskFrame, contours):
		for contour in contours:

			# gets the contour size, ignoring contours outside the provided area bounds
			centerPoint = sh.getContourCenter(contour, self.minContourArea, self.maxContourArea)

			if centerPoint is None:
				continue

			if self.ignoreContoursInLargeBoundingBox:
				# don't create a tracker for contours inside a tracker main bounding box
				if sh.contourInBBox(centerPoint, self.trackers):
					continue
			else:
				# don't create a tracker for contours inside a shrunk tracker bounding box
				if sh.contourInShrunkBBox(centerPoint, self.trackers):
					continue

			x,y,w,h = cv.boundingRect(contour)

			# extra check to make sure bounding box is in the frame and has a width and heigt
			# of at least 1
			if x < 0 or (x + w) > self.smallFrameCols or y < 0 or (y + h) > self.smallFrameRows or w < 1 or h < 1:
				continue 

			# expand the bounding box size
			x = x - self.extraBoxSize
			y = y - self.extraBoxSize
			w = w + (self.extraBoxSize * 2)
			h = h + (self.extraBoxSize * 2)

			# ignore the bird if it is too close to the edge of the frame
			if centerPoint[0] < 0 or centerPoint[1] < 0 or \
				centerPoint[0] > self.mainBBox[2] or centerPoint[1] > self.mainBBox[3]:
				continue

			# create and initialize the tracker
			cvTracker = self.createCVTracker()
			success = cvTracker.init(maskFrame, (x,y,w,h))

			if success:
				self.totalTrackersCreated += 1

				# add the tracker and draw the bounding box
				customTracker = ct.Tracker(maskFrame, cvTracker, centerPoint, (x,y,w,h))
				self.trackers.append(customTracker)

				if self.showFrames and settings[Settings.SHOW_BOUNDING_BOXES]:
					customTracker.drawShrunkBbox(maskFrame, (0,0,255))
					customTracker.drawShrunkBbox(self.currentSmallFrame, (0,0,255))

			else:
				print('Failed to create tracker')


if __name__ == '__main__':

	cv.namedWindow('Main Frame', cv.WINDOW_KEEPRATIO)

	def cvRender(frame):
		cv.imshow('Main Frame', frame)

	file_path = '/Users/SamTaylor/Courses/seng499/testfiles/unofficial/birds_busy1.mp4'
	mainBBox = (440, 178, 827, 556)
	chimneyPoints = ((755, 693), (869, 687))

	swiftCounter = SwiftCounter(file_path, cvRender)
	swiftCounter.setMainROI(mainBBox)
	swiftCounter.setChimneyPoints(chimneyPoints)
	swiftCounter.start()
	swiftCounter.cleanup()


