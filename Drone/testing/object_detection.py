import cv2 as cv
import numpy as np

# Paths to YOLOv4 files
weights_path = "yolo-config/yolov4.weights"
cfg_path = "yolo-config/yolov4.cfg"
names_path = "yolo-config/coco.names"
video_path = "video.mp4"  # Your video file
output_path = "output.mp4"

# Load class names
with open(names_path, "r") as f:
    classes = [line.strip() for line in f.readlines()]

# Load YOLOv4 network
net = cv.dnn.readNet(weights_path, cfg_path)
layer_names = net.getLayerNames()
output_layers = [layer_names[i[0]-1] for i in net.getUnconnectedOutLayers()]

# Open video
cap = cv.VideoCapture(video_path)
width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv.CAP_PROP_FPS)

# Video writer
fourcc = cv.VideoWriter_fourcc(*"mp4v")
out = cv.VideoWriter(output_path, fourcc, fps, (width, height))

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Create blob from frame
    blob = cv.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    outputs = net.forward(output_layers)

    class_ids, confidences, boxes = [], [], []

    # Parse outputs
    for out in outputs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5:  # Confidence threshold
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # Non-max suppression
    indexes = cv.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)

    # Draw bounding boxes
    for i in indexes.flatten():
        x, y, w, h = boxes[i]
        label = classes[class_ids[i]]
        cv.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv.putText(frame, label, (x, y - 10), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    out.write(frame)
    cv.imshow("YOLOv4 Detection", frame)

    if cv.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv.destroyAllWindows()