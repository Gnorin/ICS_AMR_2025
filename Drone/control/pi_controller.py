from ultralytics import YOLO
import cv2
import os
import time

#================== Video Analysis Setup ====================
base_path = os.path.dirname(os.path.realpath(__file__))

detector_path = os.path.join(base_path, "yolov8s.pt")
classifier_path = os.path.join(base_path, "best.pt")

detector = YOLO(detector_path)
classifier = YOLO(classifier_path)

cap = cv2.VideoCapture(0)

#================== Main Control Loop =======================
# Retrieve height and width information about the image.
ret, frame = cap.read()
height, width, channels = frame.shape

# Constants
kP = 0.3
kI = 0.1

vel = 0.3 # m/s
wheel_radius = 0.05 # m
wheel_separation = 0.15 # m

x_ref = width/2
fow = 90 # Degrees
deg_per_pixel = fow/width

# Initial values
omega_i = 0
angle = 0
error = [0, 0, 0]
x1, y1, x2, y2 = [0, 0, 0, 0]

t_prev = time.monotonic()

while True:
    #-------------- Image Classification --------------------
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
    
    # Shows the image at the end. Press 'Esc' to exit.
    cv2.imshow("posture", frame)
    if cv2.waitKey(1) == 27:
        break

    #-------------- System Drive and Propagation ------------
    # Error definition & propagation
    x_avg = (x1+x2)/2
    x_error = x_avg - x_ref

    error = x_error*deg_per_pixel

    # Determine dT
    t = time.monotonic()
    dt = t - t_prev
    t_prev = t

    # Integration
    omega_i = omega_i + dt*error

    # New omega
    omega = omega_i*kI + error*kP

    # Calculating control variables
    wL = vel/wheel_radius + wheel_separation/(2*wheel_radius)*omega
    wR = vel/wheel_radius - wheel_separation/(2*wheel_radius)*omega

    print("Left wheel speed: ", wL*wheel_radius)
    print("Right wheel speed: ", wR*wheel_radius)

