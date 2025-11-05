import cv2 as cv

# Open video
cap = cv.VideoCapture("phone_video.mp4")  # path to your video file

if not cap.isOpened():
    raise Exception("Could not open video")

while True:
    ret, frame = cap.read()
    if not ret:
        break  # end of video
    
    # Display frame
    cv.imshow("Video", frame)
    
    if cv.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv.destroyAllWindows()