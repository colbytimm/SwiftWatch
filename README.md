# SwiftWatch
## Automating the Collection of Bird Data from Video Footage
Go check out the website: [SwiftWatch](https://swiftwatch.azurewebsites.net/)..

Read the report on this project: [Automating the Collection of Bird Data from Video Footage](https://swiftwatch.azurewebsites.net/documents/final_report.pdf).
### Executive Summary

The chimney swift is a bird that  is designated as a threatened species in Canada. These birds nest and roost in cave walls but now also use man-made chimneys for this purpose. Initially, the bird population grew with the expansion of urban settlements. Recently, however, the bird population has declined.

To track the chimney swift population size, the Ontario government installed high-definition cameras to monitor two large communal chimneys in Sault Ste Marie, Ontario. The camera footage is manually examined to estimate the number of birds entering the chimneys.

Given that counting birds by hand is exhausting and tedious work, software automation would greatly reduce the time required to count the birds, thereby resulting in decreased cost and increased productivity. Furthermore, automation would remove the potential for a human counter to make errors. 

Computer vision techniques implemented in Python and OpenCV were employed to detect and track moving swifts in recorded video footage. The future path of a swift is predicted based on the swift’s current and previous position. The predicted path is used to determine if the swift will enter the chimney.

![](https://github.com/colbytimm/SwiftWatch-Website/blob/master/images/run.gif)

The bird tracking process starts with background subtraction. This technique produces an image which contains only moving objects in a frame. The objects contours within the resulting image are detected, and a tracker is applied to each new contour that does not already have a tracker. The swifts are continuously tracked until they enter the chimney. A performant bird counting application with a GUI is built using this bird tracking algorithm.

The proposed algorithm was found to be successful in most cases, but struggles to provide accurate results under high-stress situations when there are many birds to track simultaneously with the birds overlapping in the video footage. 
