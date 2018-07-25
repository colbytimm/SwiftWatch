import numpy as np
import cv2 as cv

# =============== HELPER FUNCTIONS ===============

def saveChimneyPoint(event, x, y, flags, param):
	frame = param[0]
	frameName = param[1]
	chimneyPoints = param[2]

	if event == cv.EVENT_LBUTTONDOWN and len(chimneyPoints) < 2:
		print('Chimney point selected:', (x, y))
		chimneyPoints.append((x,y))
		cv.circle(frame, (x, y), 1, (0, 0, 255), 2)
		cv.imshow(frameName, frame)

def drawBoundingBox(frame, box):
	cv.rectangle(frame, (box[0], box[1]), (box[0]+box[2]-1, box[1]+box[3]-1), (250, 0, 1), 2)

def rectContainsPoint(point, rect):
	px = point[0]
	py = point[1]
	rx1 = rect[0]
	rx2 = rect[0] + rect[2]
	ry1 = rect[1]
	ry2 = rect[1] + rect[3]

	if px >= rx1 and px <= rx2 and py >= ry1 and py <= ry2:
		return True
	return False

def getContourCenter(contour, minContourArea, maxContourArea):
	M = cv.moments(contour)

	# M['m00'] is the contour area
	if M['m00'] < minContourArea or M['m00'] > maxContourArea:
		return None

	cx = int(M['m10'] / M['m00'])
	cy = int(M['m01'] / M['m00'])

	return (cx, cy)

# the countour does not have a bounding box if it is a new bird
def contourInBBox(contourCenterPoint, trackers):
	# check if a bounding box contains the center point
	for tracker in trackers:
		if rectContainsPoint(contourCenterPoint, tracker.getBBox()):
			return True
	return False

def contourInShrunkBBox(contourCenterPoint, trackers):
	# check if a bounding box contains the center point
	for tracker in trackers:
		if rectContainsPoint(contourCenterPoint, tracker.getShrunkBBox()):
			return True
	return False


# a POSITIVE cross product means the birdPoint is to the RIGHT of (below) the chimney line,
# as long as the chimney points are with the leftmost point first.
def crossProduct(birdPoint, chimneyPoints):
	# point B
	birdX = birdPoint[0]
	birdY = birdPoint[1]

	# point C0
	chimneyX0 = chimneyPoints[0][0]
	chimneyY0 = chimneyPoints[0][1]

	# point C1
	chimneyX1 = chimneyPoints[1][0]
	chimneyY1 = chimneyPoints[1][1]

	# compute the cross product: C0C1 x C0P
	C0C1 = [(chimneyX1 - chimneyX0), (chimneyY1 - chimneyY0)]
	C0B = [(birdX - chimneyX0), (birdY - chimneyY0)]

	return np.cross(C0C1, C0B)


def testCrossProduct():
	chimneyPoints = [(749, 695), (915, 679)]

	birdPoint = (800, 650)
	cp = crossProduct(birdPoint, chimneyPoints)
	assert cp < 0

	birdPoint = (800, 700)
	cp = crossProduct(birdPoint, chimneyPoints)
	assert cp > 0

	birdPoint = (750, 695)
	cp = crossProduct(birdPoint, chimneyPoints)
	assert cp > 0

	birdPoint = (914, 679)
	cp = crossProduct(birdPoint, chimneyPoints)
	assert cp < 0

	birdPoint = (749, 695)
	cp = crossProduct(birdPoint, chimneyPoints)
	assert cp == 0



