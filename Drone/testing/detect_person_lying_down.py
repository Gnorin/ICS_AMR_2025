from ultralytics import YOLO
import cv2
import os

base_path = os.path.dirname(os.path.realpath(__file__))

detector_path = os.path.join(base_path, "yolov8s.pt")
classifier_path = os.path.join(base_path, "best.pt")

detector = YOLO(detector_path)
classifier = YOLO(classifier_path)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    detections = detector(frame)[0]

    for box in detections.boxes:
        if box.cls == 0:  # class 0 = person
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            crop = frame[y1:y2, x1:x2]
            class_res = classifier(crop)[0]
            name = class_res.names[class_res.probs.top1]

            cv2.rectangle(frame, (x1,y1), (x2,y2), (255,255,255), 2)
            cv2.putText(frame, name, (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

    cv2.imshow("posture", frame)
    if cv2.waitKey(1) == 27:
        break