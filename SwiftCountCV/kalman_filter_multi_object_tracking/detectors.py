'''
    File name         : detectors.py
    File Description  : Detect objects in video frame
    Author            : Srini Ananthakrishnan
    Date created      : 07/14/2017
    Date last modified: 07/16/2017
    Python Version    : >=3.0
'''

# Import python libraries
import numpy as np
import cv2

# set to 1 for pipeline images
debug = 1


class Detectors(object):
    """Detectors class to detect objects in video frame
    Attributes:
        None
    """
    def __init__(self):
        """Initialize variables used by Detectors class
        Args:
            None
        Return:
            None
        """
        self.fgbg = cv2.createBackgroundSubtractorMOG2()
        self.count = 0

    def Detect(self, frame):
        """Detect objects in video frame using following pipeline
            - Convert captured frame from BGR to GRAY
            - Perform Background Subtraction
            - Detect edges using Canny Edge Detection
              http://docs.opencv.org/trunk/da/d22/tutorial_py_canny.html
            - Retain only edges within the threshold
            - Find contours
            - Find centroids for each valid contours
        Args:
            frame: single video frame
        Return:
            centers: vector of object centroids in a frame
        """

        # Convert BGR to GRAY
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if (debug == 1):
            cv2.imshow('gray', gray)

        # Perform Background Subtraction
        fgmask = self.fgbg.apply(gray)

        if (debug == 0):
            cv2.imshow('bgsub', fgmask)

        # Detect edges
        edges = cv2.Canny(fgmask, 10, 255, 3)

        if (debug == 1):
            cv2.imshow('Edges', edges)

        # Retain only edges within the threshold
        ret, thresh = cv2.threshold(edges, 150, 255, 0)
        
        #morphs
        #morphs for open/close shapes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (6, 6))
        thresh = cv2.morphologyEx(thresh,cv2.MORPH_CLOSE, kernel)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        thresh = cv2.morphologyEx(thresh,cv2.MORPH_OPEN, kernel)
        
        if (debug == 1):
            cv2.imshow('Morphs', thresh)

        # Find contours
        _, contours, hierarchy = cv2.findContours(thresh,
                                                  cv2.RETR_EXTERNAL,
                                                  cv2.CHAIN_APPROX_SIMPLE)

        if (debug == 0):
            cv2.imshow('thresh', thresh)

        centers = []  # vector of object centroids in a frame
        # we only care about centroids with size of bug in this example
        # recommended to be tunned based on expected object size for
        # improved performance
        blob_radius_thresh = 7.5
        # Find centroid for each valid contours
        for cnt in contours:
            try:
                # Calculate and draw circle
                (x, y), radius = cv2.minEnclosingCircle(cnt)
                centeroid = (x, y)
                centeroid_int = (int(x), int(y))
                
                
                thick = 3
                x1 = 120
                x2 = 400
                y1 = 960 + thick
                y2 = 970 + thick
                
                line = ((120, 950) ,(400, 960))
                bline = ((120, 950 + thick) ,(400, 960 + thick))
                
                #crossingLine = x1 < x < x2 and y1 < y < y2
                crossingLine = y > y2 and x1 < x < x2
                
                #update count (intersection with line)
                if crossingLine:
                    self.count = self.count + 1
                
                cv2.putText(frame,str(self.count) + " Counted!" ,(100,100),cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,0.7,(0, 0, 255),1, cv2.LINE_AA)

            
                if (radius > blob_radius_thresh):
                    cv2.circle(frame, centeroid_int, int(radius), (0, 255, 0), 2)
                    cv2.putText(frame, str(float("%0.1f" % (radius))),centeroid_int,cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,0.7,(0, 0, 255),1, cv2.LINE_AA)
                    b = np.array([[int(x)], [int(y)]])
                    centers.append(np.round(b))
            except ZeroDivisionError:
                pass

        # show contours of tracking objects
        # cv2.imshow('Track Bugs', frame)

        return centers
