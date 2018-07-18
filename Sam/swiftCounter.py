import numpy as np
import cv2 as cv
import customTracker as ct
import swiftHelper as sh
import time

# =============== GLOBAL VARIABLES ===============

projectDir = '/Users/SamTaylor/Courses/seng499/testfiles/'
inFile = projectDir + 'birds_052117_205059.mp4'
#inFile = projectDir + 'birds_052317_212859.mp4'

#inFile = projectDir + 'unofficial/swift_tester2.mp4'
#inFile = projectDir + 'unofficial/birds_busy1.mp4'

showFrames = False
waitForKeyPress = False

instructionTextColour = (204, 51, 0)

imageScale = 0.5

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

edgeDistance = 0
extraBoxSize = 25

enteredChimneyCount = 0
enteredChimneyCountFromPrediction = 0
enteredChimneyCountFromLostAboveChimney = 0
exitedChimneyCount = 0

totalTrackersCreated = 0
trackers = []

frameCols = 0
frameRows = 0


# =============== INITIALIZE COMPONENTS ===============

# background subtractor
#fgbg = cv.bgsegm.createBackgroundSubtractorMOG()
fgbg = cv.createBackgroundSubtractorMOG2()

# create other windows so they can be resizable
# cv.namedWindow('initialFrame', cv.WINDOW_KEEPRATIO)
# cv.namedWindow('mainFrame', cv.WINDOW_KEEPRATIO)
# cv.namedWindow('maskFrame', cv.WINDOW_KEEPRATIO)

# =============== GET MAIN ROI ===============

cap = cv.VideoCapture(inFile)

# resize and display initial frame
ret, initialFrame = cap.read()
if not ret:
	print('Failed to read first frame - aborting program.')
	quit()

#initialFrame = cv.resize(initialFrame, (0,0), fx=imageScale, fy=imageScale)

# instruction text
cv.putText(initialFrame, '1. Draw the main bounding box then press any key', (10, 30),
			cv.FONT_HERSHEY_SIMPLEX, 0.75, instructionTextColour, 2)

# select main region of interest
mainBBox = cv.selectROI('initialFrame', initialFrame, False)
frameCols = mainBBox[2]
frameRows = mainBBox[3]
sh.drawBoundingBox(initialFrame, mainBBox)
print(mainBBox)

# =============== GET CHIMNEY TOP LINE ===============

# instruction text
cv.putText(initialFrame, '2. Pick the chimney points starting with the left side then press any key', (10, 60),
			cv.FONT_HERSHEY_SIMPLEX, 0.75, instructionTextColour, 2)
cv.imshow('initialFrame', initialFrame)

# get the points for the chimney-top line
cv.setMouseCallback('initialFrame', sh.saveChimneyPoint, [initialFrame, chimneyPoints])

# draw the chimney line
while len(chimneyPoints) < 2:
	print('Add chimney points', chimneyPoints)
	# Wait for keypress
	cv.waitKey(0)

# draw the chimney line
cv.line(initialFrame, chimneyPoints[0], chimneyPoints[1], (250, 0, 1), 2)
cv.imshow('initialFrame', initialFrame)

# translate the line to the position in the main bounding box
chimneyPoints[0] = (chimneyPoints[0][0] - mainBBox[0], chimneyPoints[0][1] - mainBBox[1])
chimneyPoints[1] = (chimneyPoints[1][0] - mainBBox[0], chimneyPoints[1][1] - mainBBox[1])


# =============== DO THE WORK ===============

print('Starting the hard work')

startTime = time.time()

while(1):
	ret, bigFrame = cap.read()

	if not ret:
		break

	# resize the image to a viewable size
	#mainFrame = cv.resize(mainFrame, (0,0), fx=imageScale, fy=imageScale)

	# get the image from the bounding box
	mainFrame = bigFrame[int(mainBBox[1]):int(mainBBox[1]+mainBBox[3]), int(mainBBox[0]):int(mainBBox[0]+mainBBox[2])]

	# convert to greyscale and blur
	maskFrame = cv.cvtColor(mainFrame, cv.COLOR_BGR2GRAY)
	maskFrame = cv.GaussianBlur(maskFrame, (11, 11), 0)

	# get the foreground mask 
	maskFrame = fgbg.apply(maskFrame)

	# perform a series of erosions and dilations to remove
	# any small blobs of noise from the thresholded image
	maskFrame = cv.erode(maskFrame, None, iterations=1)
	maskFrame = cv.dilate(maskFrame, None, iterations=1)

	# find contours and draw then on the main frame
	contoursFrame, contours, hierarchy = cv.findContours(maskFrame, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
	#cv.drawContours(mainFrame, contours, -1,  (0, 255, 0), 1);

	# update trackers
	for tracker in trackers:
		wasLocated = tracker.update(maskFrame)

		# if not wasLocated and tracker.lostNewBirdJustAboveChimney(chimneyPoints):
		# 	# assume the bird went in
		# 	enteredChimneyCount +=1
		# 	enteredChimneyCountFromLostAboveChimney += 1

		if tracker.getStaleCount() >= maxStaleCount:
			trackers.remove(tracker)
			continue

		# guard against false positivies to preserve cpu resources
		# remove trackers with empty bounding boxes
		# is not necessary for most trackers (but useful for MIL)
		if removeEmptyTrackers and not tracker.containsContour(contours, dropContourOutsideSizeRange, minContourArea, maxContourArea):
				trackers.remove(tracker)
				continue

		if showFrames:
			#tracker.drawBbox(maskFrame, (255,0,0))
			tracker.drawShrunkBbox(maskFrame, (255,0,0))
			#tracker.drawBbox(mainFrame, (255,0,0))
			tracker.drawShrunkBbox(mainFrame, (255,0,0))

			# draw the line to the predicted point
			point = tracker.getPoint()
			ppoint = tracker.predictNextPoint()
			if point is not None and ppoint is not None:
				point = (int(point[0]), int(point[1]))
				ppoint = (int(ppoint[0]), int(ppoint[1]))
				cv.line(mainFrame, point, ppoint, (0, 255, 0), 1)


		if tracker.enteredChimney(chimneyPoints):
			enteredChimneyCount +=1
			enteredChimneyCountFromPrediction += 1
			print('\nENTERED CHIMNEY, count:', enteredChimneyCount, '\n')

		# if tracker.exitedChimney(chimneyPoints):
		# 	exitedChimneyCount +=1
		# 	print('\nEXITED CHIMNEY, count:', exitedChimneyCount, '\n')

	#print('Number of current trackers:', len(trackers))

	# find new contours and create trackers
	for contour in contours:

		# gets the contour size, ignoring contours outside the provided area bounds
		centerPoint = sh.getContourCenter(contour, minContourArea, maxContourArea)

		if centerPoint is None:
			continue

		if ignoreContoursInLargeBoundingBox:
			# don't create a tracker for contours inside a tracker main bounding box
			if sh.contourInBBox(centerPoint, trackers):
				continue
		else:
			# don't create a tracker for contours inside a shrunk tracker bounding box
			if sh.contourInShrunkBBox(centerPoint, trackers):
				continue

		x,y,w,h = cv.boundingRect(contour)

		# extra check to make sure bounding box is in the frame and has a width and heigt
		# of at least 1
		if x < 0 or (x + w) > frameCols or y < 0 or (y + h) > frameRows or w < 1 or h < 1:
			continue 

		# expand the bounding box size
		x = x - extraBoxSize
		y = y - extraBoxSize
		w = w + (extraBoxSize * 2)
		h = h + (extraBoxSize * 2)

		# ignore the bird if it is too close to the edge of the frame
		if (centerPoint[0] - edgeDistance) < 0 or (centerPoint[1] - edgeDistance) < 0 or \
			(centerPoint[0] + edgeDistance > mainBBox[2]) or (centerPoint[1] + edgeDistance > mainBBox[3]):
			continue

		# create and initialize the tracker

		#cvTracker = cv.TrackerBoosting_create()
		#cvTracker = cv.TrackerCSRT_create()
		#cvTracker = cv.TrackerGOTURN_create()
		#cvTracker = cv.TrackerKCF_create()
		#cvTracker = cv.TrackerMedianFlow_create()
		#cvTracker = cv.TrackerMIL_create()
		cvTracker = cv.TrackerMOSSE_create()
		#cvTracker = cv.TrackerTLD_create()
		
		success = cvTracker.init(maskFrame, (x,y,w,h))

		if success:
			totalTrackersCreated += 1

			# add the tracker and draw the bounding box
			customTracker = ct.Tracker(maskFrame, cvTracker, centerPoint, (x,y,w,h))
			trackers.append(customTracker)

			if showFrames:
				#customTracker.drawBbox(maskFrame, (255,0,0))
				customTracker.drawShrunkBbox(maskFrame, (0,0,255))
				#customTracker.drawBbox(mainFrame, (0,0,255))
				customTracker.drawShrunkBbox(mainFrame, (0,0,255))

		else:
			print('Failed to create tracker')

	#print('Total trackers created:', totalTrackersCreated)

	if showFrames:
		# display counts
		cv.putText(mainFrame, "In: {}".format(str(enteredChimneyCount)), (10, 70),
			cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
		# cv.putText(mainFrame, "Out: {}".format(str(exitedChimneyCount)), (10, 90),
		# 	cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
		
		# draw bounding box and chimney line
		sh.drawBoundingBox(bigFrame, mainBBox)
		cv.line(mainFrame, chimneyPoints[0], chimneyPoints[1], (250, 0, 1), 2)

		# draw the frames
		cv.imshow('initialFrame', bigFrame)
		#cv.imshow('mainFrame', mainFrame)
		cv.imshow('maskFrame', maskFrame)

	if waitForKeyPress:
		if cv.waitKey(0) == ord('q'): break

	#check if video is finished
	k = cv.waitKey(1) & 0xff
	if k == 27 or k == ord('q'):
		break


elapsedTime = time.time() - startTime

print('Total amount of birds entering:', enteredChimneyCount)
print('From prediction:', enteredChimneyCountFromPrediction)
print('From lost above chimney:', enteredChimneyCountFromLostAboveChimney)
print('Total amount of birds exiting:', exitedChimneyCount)
print('Elapsed time:', elapsedTime)
print('Total trackers created:', totalTrackersCreated)

cap.release()
cv.destroyAllWindows()




