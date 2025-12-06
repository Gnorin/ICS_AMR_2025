import cv2 as cv

# Open video
#cap = cv.VideoCapture("phone_video.mp4")
cap = cv.VideoCapture(0)

if not cap.isOpened():
    raise Exception("Could not open video")

while True:
    ret, frame = cap.read()
    if not ret:
        break  # end of video
    
    # Display frame
    cv.imshow("Video", frame)
    
    if cv.waitKey(1) == 27: # Press 'Esc' to close the stream window.
        break

cap.release()
cv.destroyAllWindows()