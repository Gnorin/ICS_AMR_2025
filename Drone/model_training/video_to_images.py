import cv2 as cv
import os

# Source file
source_video = "video.mp4"

# Destination folder
destination_folder = "images"

stream = cv.VideoCapture(source_video)

if not stream.isOpened():
    raise RuntimeError(f"Could not open source file '{source_video}'")

# Create a destination folder if the file was opened
os.makedirs(destination_folder, exist_ok=True)

frame_index = 0
filename = ""

while True:
    ret, frame = stream.read()
    if not ret:
        break

    filename = os.path.join(destination_folder, f"image_{frame_index}.png")
    
    cv.imwrite(filename, frame)
    
    frame_index += 1

stream.release()
print("Done.")
print(f"Images generated in '{os.path.realpath(destination_folder)}'")