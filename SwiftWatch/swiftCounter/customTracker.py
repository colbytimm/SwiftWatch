import numpy as np
import cv2 as cv
import swiftCounter.swiftHelper as sh

# =============== CUSTOM TRACKER CLASS ===============

class Tracker:
	cvTracker = None

	initializedJustAboveChimneySlack = 20
	boxShrinkSize = 12

	# the number of times the bBox has not moved
	staleCount = 0

	oldBBox = None
	bBox = None

	# controls the length of the prediction line
	predictPointMultiple = 2

	oldPoint = None
	point = None

	inChimney = False

	def __init__(self, frame, cvTracker, point, bBox):
		self.cvTracker = cvTracker
		self.point = point
		self.bBox = bBox

	def getPoint(self):
		return self.point


	def setInChimney(self, inChimney):
		self.inChimney = inChimney

	def update(self, frame):
		# update the tracker and get the new bounding box
		wasLocated, newBBox = self.cvTracker.update(frame)

		if wasLocated:
			self.bBox = newBBox

			# save the old values
			self.oldPoint = self.point
			self.oldBBox = self.bBox

			# get the new center point
			px = self.bBox[0] + (self.bBox[2] / 2)
			py = self.bBox[1] + (self.bBox[3] / 2)
			self.point = (px, py)

		else:
			self.staleCount += 1

		return wasLocated

	def lostNewBirdJustAboveChimney(self, chimneyPoints):
		chimneyYAvg = (chimneyPoints[0][1] + chimneyPoints[1][1]) / 2

		# if the tracker was initialized right above the chimney line and the
		# bird was not located on the first update, assume the bird entered the chimney
		if not self.inChimney and \
			self.oldPoint == None and \
			self.inChimneyXRange(chimneyPoints) and \
			(self.point[1] + self.initializedJustAboveChimneySlack) > chimneyYAvg:
			self.inChimney = True
		return self.inChimney



	def drawBbox(self, frame, colour):
		self.__drawBbox(frame, colour, self.bBox)

	def drawShrunkBbox(self, frame, colour):
		self.__drawBbox(frame, colour, self.getShrunkBBox())

	def __drawBbox(self, frame, colour, bBox):
		p1 = (int(bBox[0]), int(bBox[1]))
		p2 = (int(bBox[0] + bBox[2]), int(bBox[1] + bBox[3]))
		cv.rectangle(frame, p1, p2, colour, 2, 1)

	def getBBox(self):
		return self.bBox

	def getShrunkBBox(self):
		x = self.bBox[0] + self.boxShrinkSize
		y = self.bBox[1] + self.boxShrinkSize
		w = self.bBox[2] - (self.boxShrinkSize * 2)
		h = self.bBox[3] - (self.boxShrinkSize * 2)
		return (x, y, w, h)

	def inChimneyXRange(self, chimneyPoints):
		if self.point[0] >= chimneyPoints[0][0] and \
			self.point[0] <= chimneyPoints[1][0]:
			return True
		return False

	def enteredChimney(self, chimneyPoints):
		if self.inChimney or \
			self.point is None or \
			self.oldPoint is None or \
			not self.inChimneyXRange(chimneyPoints):
			return False

		# try to predict the new point since we won't see the new bird point
		# after it enters the chimney
		predictedPoint = self.predictNextPoint()

		# check that the new point is below the chimney line and the 
		# old point is above the chimney line

		#cp = sh.crossProduct(self.point, chimneyPoints)
		cp = sh.crossProduct(predictedPoint, chimneyPoints)
		if cp < 0:
			# point above the chimney line
			return False

		#cp = sh.crossProduct(self.oldPoint, chimneyPoints)
		cp = sh.crossProduct(self.point, chimneyPoints)
		if cp > 0:
			# oldPoint is below the chimney line
			return False

		self.inChimney = True
		return True

	def exitedChimney(self, chimneyPoints):
		if self.point is None or \
			self.oldPoint is None or \
			not self.inChimneyXRange(chimneyPoints):
			return False

		# check that the new point is below the chimney line and the 
		# old point is above the chimney line

		cp = sh.crossProduct(self.point, chimneyPoints)
		if cp > 0:
			# point above the chimney line
			return False

		cp = sh.crossProduct(self.oldPoint, chimneyPoints)
		if cp < 0:
			# oldPoint is below the chimney line
			return False

		return True

	# Get the vector  oldPoint -> point, then multiply X and Y components
	# by predictPointMultiple to predict where the bird will
	def predictNextPoint(self):
		if self.point is None or self.oldPoint is None:
			return None

		pointVecX = self.point[0] - self.oldPoint[0]
		pointVecY = self.point[1] - self.oldPoint[1]

		predictedPointX = self.point[0] + (pointVecX * self.predictPointMultiple)
		predictedPointY = self.point[1] + (pointVecY * self.predictPointMultiple)

		return (predictedPointX, predictedPointY)

	def getStaleCount(self):
		return self.staleCount

	def containsContour(self, contours, dropContourOutsideSizeRange, minContourArea, maxContourArea):
		for contour in contours:
			M = cv.moments(contour)

			# M['m00'] is the contour area
			if M['m00'] <= 0 or \
				(dropContourOutsideSizeRange and (M['m00'] < minContourArea or M['m00'] > maxContourArea)):
				continue

			cx = int(M['m10'] / M['m00'])
			cy = int(M['m01'] / M['m00'])

			if sh.rectContainsPoint((cx, cy), self.bBox):
				return True

		return False



