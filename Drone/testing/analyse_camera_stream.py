import cv2 as cv
from ultralytics import YOLO

stream = cv.VideoCapture(0)
model = YOLO("yolov8s.pt")

while True:
    ret, frame = stream.read()

    if ret == False:
        break

    results = model(frame)

    annotated = results[0].plot()
    cv.imshow("YOLOv8", annotated)
    if cv.waitKey(1) == 27: # Press 'Esc' to close the stream window.
        break