# Swift CV2 Counter

import imutils
import cv2


width = 800
height = 450

text_in = 0

video_path = "swift.mp4"

def test_intersection_in(x, y):
    # blue
    res = y - 205
    if ((res >= -5) and (res <= 5) and (x >= 400) and (x <= 460)):
        print('Res is: {}'.format(str(res)))
        return True
    return False

camera = cv2.VideoCapture(video_path)

firstFrame = None

# loop over the frames of the video
while True:
    # grab the current frame and initialize the occupied/unoccupied
    (grabbed, frame) = camera.read()

    # if the frame could not be grabbed, then we have reached the end
    # of the video
    if not grabbed:
        break

    # resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width=width)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # if the first frame is None, initialize it
    if firstFrame is None:
        firstFrame = gray
        continue

    # compute the absolute difference between the current frame and
    # first frame
    frameDelta = cv2.absdiff(firstFrame, gray)
    thresh = cv2.threshold(frameDelta, 32, 255, cv2.THRESH_BINARY)[1]
    # dilate the thresholded image to fill in holes, then find contours
    # on thresholded image
    thresh = cv2.dilate(thresh, None, iterations=2)
    _, cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # loop over the contours
    for c in cnts:
        # if the contour is too small, ignore it
        # if cv2.contourArea(c) < 10000:
        #     continue
        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)

        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        cv2.line(frame, (width // 2, height // 2 - 20), (width // 2 + 60, height // 2 - 20), (250, 0, 1), 2) #blue line

        rect_center_pt = ((x + x + w) // 2, (y + y + h) // 2)
        cv2.circle(frame, rect_center_pt, 1, (0, 0, 255), 5)

        if(test_intersection_in((x + x + w) // 2, (y + y + h) // 2)):
            print(rect_center_pt)
            text_in += 1

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    cv2.putText(frame, "In: {}".format(str(text_in)), (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    cv2.imshow("Swift Counter", frame)

print('The total amount of Swift birds in is: {}'.format(text_in))
# cleanup the camera and close any open windows
camera.release()
cv2.destroyAllWindows()
