'''
Created on May 25, 2018

@author: Timothy
'''
import numpy as np
import cv2 as cv
import matplotlib as mp
import matplotlib.pyplot as plt


print("numpy:  " + np.__version__)
print("opencv: " + cv.__version__)

#playing video
cap = cv.VideoCapture('swift_enter.mp4');

while(cap.isOpened()):
    
    ret, frame = cap.read()
    #video size
    #print(frame.shape)
    
    #our Region of Interest(ROI)
    roiFrame = frame[20:600, 900:1200]
    
    #resize
    resized = cv.resize(roiFrame, None, fx=2, fy=2, interpolation = cv.INTER_LINEAR)
    
    print(resized.shape)
    #grayscale
    gray = cv.cvtColor(resized, cv.COLOR_BGR2GRAY)
    
    #binary threshold
    threshLimit = 100
    ret, thresh = cv.threshold(gray, threshLimit, 255, cv.THRESH_BINARY)
    
    #adaptive threshold
    #thresh = cv.adaptiveThreshold(thresh, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY, 9, 10)
    
    
    #blurs to open and close bird shapes
    #blur = cv.blur(thresh, (4,4))
    #cv.imshow('blur', blur)
    blur = thresh
    #thresh = cv.GaussianBlur(thresh, (3,3),0)
    #blur2 = cv.bilateralFilter(blur,9,75,75)
    #cv.imshow('blur2', blur2)
    
    #morphs for open/close shapes
    kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (3, 3))
    closing = cv.morphologyEx(blur,cv.MORPH_CLOSE, kernel)

    opening = cv.morphologyEx(closing,cv.MORPH_OPEN, kernel)
    #kernel = np.ones((1,1), np.uint8)
    #thresh = cv.fastNlMeansDenoising(thresh, None, 20,7,21)
    cv.imshow('close/open morph', opening)
    
    #blur = cv.dilate(opening,kernel, iterations = 2)
    #cv.imshow('dilate',blur)

    #new threshold for contours
    ret,contThresh = cv.threshold(opening,20,255,0)
    cv.imshow('contour thresh', contThresh)

    #find bird contours
    contourFrame, contours, hierarchy = cv.findContours(contThresh,cv.RETR_TREE,cv.CHAIN_APPROX_NONE)
    
    birdAreas = []
    
    #draw contours
    for c in contours:
        M = cv.moments(c)
        m = M["m00"]
        if m > 0:
            #calc centroid
            cx = int(M["m10"] / m)
            cy = int(M["m01"] / m)
            
            #assume large contours are in foreground
            cntArea = cv.contourArea(c)
            if cntArea > 80:
                cv.circle(resized, (cx, cy), 2, (0,255,0), -1)
                #print contour borders on footage
                #cv.drawContours(resized, contours, -1, (0,0,255), 0)
                if cntArea < 255:
                    birdAreas.append(int(cntArea))
                #print("contour size: ", int(cv.contourArea(c)))
                cv.drawContours(resized, c, -1, (0,0,255), 0)
            else:  
                cv.circle(resized, (cx, cy), 2, (255,0,0), -1)
                
    
    
    
    
    
    
    
    
    #plt.hist(birdAreas,100,[0,100])
    #plt.show()
    #plt.close()
    
    #optical tracking (multiple?)
    if len(contours)>0:
        
        pass
    
    #window1 = cv.namedWindow('histogram', cv.WINDOW_NORMAL)
    #cv.resizeWindow('histogram', 1024, 900)    
    
    
    window = cv.namedWindow('frame', cv.WINDOW_NORMAL)
    #window1 = cv.namedWindow('histogram', cv.WINDOW_NORMAL)
    cv.resizeWindow('frame', 1024, 900)
    cv.imshow('frame', resized)
    
    if cv.waitKey(150) & 0xFF == ord('q'):
        break


plt.figure("Bird Area Histogram")
plt.hist(birdAreas,100,[0,100])
plt.show()
#plt.close()
#hist = np.bincount(birdAreas.ravel(), 256, [0,256])

#plt.imshow(hist)
cap.release()
cv.destroyAllWindows()
    
