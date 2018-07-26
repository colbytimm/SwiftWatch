import numpy as np
import cv2 as cv
import swiftCounter.customTracker as ct
import swiftCounter.swiftHelper as sh
import time
import threading

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

	frameCols = 0
	frameRows = 0

	_stop = False
	startCondition = None


	def __init__(self, videoPath, renderFunc, startCondition, backgroundSubtractor=1):
		self.videoPath = videoPath
		self.renderFunc = renderFunc
		self.startCondition = startCondition
		self.setBackgroundSubtractor(backgroundSubtractor)

		self.videoCapture = cv.VideoCapture(videoPath)
		ret, self.currentBigFrame = self.videoCapture.read()

		# always render the big frame first
		self.renderFunc(self.currentBigFrame)

		if not ret:
			print('Failed to read first frame - aborting program.')
			quit() # Probably change this to display an error message

	# Convert to correct format and render in gui
	def renderMainFrame(self):
		if self.renderSmallFrame:
			self.renderFunc(self.currentSmallFrame)
		else:
			self.renderFunc(self.currentBigFrame)

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
		self.frameCols = mainBBox[2]
		self.frameRows = mainBBox[3]
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

	def start(self):
		self.countSwifts()

	def countSwifts(self):
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
				# display counts
				cv.putText(self.currentSmallFrame, "In: {}".format(str(self.enteredChimneyCount)), (10, 70),
					cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
				
				# draw bounding box and chimney line
				sh.drawBoundingBox(self.currentBigFrame, self.mainBBox)
				self.drawChimneyLine()

				# render the main frame in the gui
				self.renderMainFrame()

			if self._stop:
				self._stop = False
				with self.startCondition:
					self.startCondition.wait()

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
					#tracker.drawBbox(maskFrame, (255,0,0))
					tracker.drawShrunkBbox(maskFrame, (255,0,0))
					#tracker.drawBbox(self.currentSmallFrame, (255,0,0))
					tracker.drawShrunkBbox(self.currentSmallFrame, (255,0,0))

					# draw the line to the predicted point
					point = tracker.getPoint()
					ppoint = tracker.predictNextPoint()
					if point is not None and ppoint is not None:
						point = (int(point[0]), int(point[1]))
						ppoint = (int(ppoint[0]), int(ppoint[1]))
						cv.line(self.currentSmallFrame, point, ppoint, (0, 255, 0), 1)


				if tracker.enteredChimney(self.chimneyPoints):
					self.enteredChimneyCount +=1
					self.enteredChimneyCountFromPrediction += 1
					print('ENTERED CHIMNEY, count:', self.enteredChimneyCount)

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
			if x < 0 or (x + w) > self.frameCols or y < 0 or (y + h) > self.frameRows or w < 1 or h < 1:
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

				if self.showFrames:
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


