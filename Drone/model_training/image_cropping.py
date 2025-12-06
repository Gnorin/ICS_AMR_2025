from ultralytics import YOLO
import cv2
import os

# Load YOLOv8 pretrained for detection
model = YOLO("yolov8n.pt")

# Create output folder
os.makedirs("crops", exist_ok=True)

# Crop all input images.
image_index = 0
person_count = 721
while True:
    # Input image
    img = cv2.imread(f"images4/image_{image_index}.png")

    # Run detection
    results = model(img)[0]

    for box in results.boxes:
        cls = int(box.cls[0])
        if cls != 0:  # class 0 = person
            continue

        # YOLO box format: xyxy
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

        # Crop the image
        crop = img[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]

        # Save
        filename = f"crops/person_{person_count}.jpg"
        cv2.imwrite(filename, crop)
        person_count += 1
    
    image_index += 1

    if image_index % 10 == 0:
        print(f"'image_{image_index}.png' analyzed...")
        print(f"Saved {person_count} person crops to ./crops/")