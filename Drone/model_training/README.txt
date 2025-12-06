This is the setup for training the model. It is also necessary to supply the training images, but they are too big for github.

1. Use video_to_images.py to generate images from a video source file. Do this for both lying_down and not_lying_down data.
2. Split up the images (80+20) into train and val respectively. Do this for both datasets.
3. execute train.bat
4. The weights can be found in the folder /runs/classify/train/weights

The images in train are used in training the model, while the images in val are for validating it.