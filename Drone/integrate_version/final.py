import os
import cv2                          
from ultralytics import YOLO        
import paho.mqtt.client as mqtt     
import time                         
import threading                    
import random                       # for simulate coordinate
import json                         
from flask import Flask, Response   # to build up the one-page website for video streaming

# ==========================================
# 1. parameters setting
# ==========================================

# --- video resource setting ---
# ESP32-CAM streaming website *must to include :81/stream to get MJPEG streaming
STREAM_URL = "http://xx.xx.xxx.xxx:81/stream" 
#STREAM_URL = 0
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
# --- MQTT broker setting ---
MQTT_BROKER = "xxx.xxx.xxx.xxx"       # MQTT Broker IP
MQTT_PORT = 1883                    # MQTT port

# --- MQTT topic setting ---
TOPIC_CMD   = "patrol/car/follow_cmd" 
TOPIC_ALERT = "patrol/car/alert"      
TOPIC_MODE  = "patrol/car/mode"       
TOPIC_COORD = "patrol/car/coordinate" 

# --- model setting ---
FALL_LABEL = "lying_down"          
FALL_CONF_THRESHOLD = 0.7           

# --- video frame parameters ---
FRAME_WIDTH = 640                   # image width(esp32's VGA setting)
FRAME_HEIGHT = 480                  # image height
TOTAL_FRAME_AREA = FRAME_WIDTH * FRAME_HEIGHT 
CENTER_X = FRAME_WIDTH // 2         # image center
DEAD_ZONE = 100                     # tolerant error

KP = 0.5 
BASE_SPEED = 140 
MAX_SPEED = 200  

# --- distant control parameters ---
MIN_AREA = 80000                    # body frame < this value : too far (go forward)
MAX_AREA = 150000                   # body frame > this value : too close (go backward)

# --- visual avoiding parameters ---
DANGER_RATIO = 0.4                  # dangerous (occupy 40% of the scene : backward)
SAFE_RATIO = 0.3                    # safe (30% ~ 40% : stop)

# --- simulated coordinates dataset ---
LOCATIONS = [
    {"zone": "Living Room", "x": 10.5, "y": 5.2},
    {"zone": "Kitchen", "x": -3.2, "y": 8.8},
    {"zone": "Laboratory", "x": 15.0, "y": -2.5},
    {"zone": "Corridor A", "x": 0.0, "y": 20.0}
]

# ==========================================
# 2. initialization and global variable
# ==========================================
app = Flask(__name__)               
outputFrame = None                  
lock = threading.Lock()    # prevent ai detection from conflict with the website when loading video stream

# follow mode's flag : false(default)
is_follow_mode = False 

# --- MQTT callback function---
def on_message(client, userdata, msg):
    global is_follow_mode 
    
    topic = msg.topic 
    payload = msg.payload.decode("utf-8") # get the payload and decode it into string form
    
    if topic == TOPIC_MODE:
        print(f"Mode: {payload}")
        
        if payload == "follow":
            is_follow_mode = True
            print("Change to Follow Mode!")
        
        else:
            is_follow_mode = False
            print("Stop following!")
            client.publish(TOPIC_CMD, "0,0")

client = mqtt.Client()
client.on_message = on_message

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    client.subscribe(TOPIC_MODE) 
    
    client.loop_start() 
    print("Successful connect to MQTT Broker!!!")

except Exception as e:
    print(f"Fail connect to MQTT Broker: {e}")

print("Loading model...")
detector = YOLO("yolov8s.pt") 
classifier = YOLO("best.pt")   

# ==========================================
# 3. core logic
# ==========================================
def processing_thread():
    global outputFrame, lock, is_follow_mode
    
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;60000000|timeout;60000000"
    cap = cv2.VideoCapture(STREAM_URL)
    
    last_cmd = ""       # record the last message
    last_alert_time = 0 # record the time
    is_emergency_stop = False 

    def send_drive_cmd(cmd):
        nonlocal last_cmd
        
        if not is_follow_mode or is_emergency_stop:
            return 

        if cmd != last_cmd:
            client.publish(TOPIC_CMD, cmd)
            last_cmd = cmd

    def send_simulated_location():
        loc = random.choice(LOCATIONS)
        payload = json.dumps(loc)
        client.publish(TOPIC_COORD, payload)
        return loc['zone']

    # --- continously reading video ---
    while True:
        if cap is None or not cap.isOpened():
            print("Camera not connected. Retrying in 3 seconds...")
            time.sleep(3) 
            cap = cv2.VideoCapture(STREAM_URL)
            continue

        ret, frame = cap.read() 
        
        # reading fail
        if not ret:
            print("Frame lost / Stream disconnected. Reconnecting...")
            cap.release()
            time.sleep(2)
            cap = cv2.VideoCapture(STREAM_URL) 
            continue

        if frame is None or frame.size == 0:
            print("Empty frame received. Skipping.")
            continue

        try:
            frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        except cv2.error as e:
            print(f"Resize error: {e}")
            continue
        
        # --------------------------------------
        # --- person detection ---
        # --------------------------------------
        # detector model: class 0 (person)
        results = detector(frame, verbose=False, classes=[0])
        
        target_found = False 
        
        # analyze detected result
        for r in results:
            boxes = r.boxes
            
            # if there's a person
            if len(boxes) > 0:
                # find the most confident object
                best_box = max(boxes, key=lambda x: x.conf[0])
                
                # to get the coordinate of frame
                x1, y1, x2, y2 = map(int, best_box.xyxy[0])
                
                # bound protection
                h, w, _ = frame.shape
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                crop = frame[y1:y2, x1:x2]
              
                # pass the noise(the frame that too small)
                if crop.size == 0 or crop.shape[0] < 10 or crop.shape[1] < 10:
                    continue

                target_found = True
                
                # visual avoiding parameters
                box_area = (x2 - x1) * (y2 - y1)      
                cover_ratio = box_area / TOTAL_FRAME_AREA
                
                # green frame
                box_color = (0, 255, 0)
                status_text = "Tracking"

                # --------------------------------------
                # --- fallen detection ---
                # --------------------------------------
                try:
                    cls_res = classifier(crop, verbose=False)[0]
                    
                    if cls_res.probs:
                        top1_idx = cls_res.probs.top1
                        posture_name = cls_res.names[top1_idx] 
                        posture_conf = cls_res.probs.top1conf.item() 

                        if posture_name == FALL_LABEL and posture_conf > FALL_CONF_THRESHOLD:
                            box_color = (0, 0, 255) # red frame
                            status_text = f"FALL !!! STOP !!!"
                            
                            # publish alert
                            if (time.time() - last_alert_time) > 60.0:
                                print(f"Someone falls!!!")
                                
                                client.publish(TOPIC_ALERT, "fall_detected")                                
                                client.publish(TOPIC_MODE, "manual") 
                                client.publish(TOPIC_CMD, "0,0")

                                zone = send_simulated_location()
                                print(f"Dispatch UAV to: {zone}")
                                
                                last_alert_time = time.time()
                                is_emergency_stop = True # lock the car
                        else:
                            # not confident enough
                            if posture_name == FALL_LABEL:
                                status_text = f"Safe ({posture_conf:.2f})" 
                            else:
                                status_text = f"{posture_name} ({posture_conf:.2f})"
                            
                            is_emergency_stop = False #unlock
                except:
                    pass

                # put on label on the streaming
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(frame, status_text, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, box_color, 2)
                # --------------------------------------
                # --- follow logic ---
                # --------------------------------------
                
                # --- Kp computation ---
                cx = (x1 + x2) // 2
                error = cx - CENTER_X 
                cv2.circle(frame, (cx, (y1+y2)//2), 5, (0, 255, 255), -1)

                turn_correction = int(error * KP)
                    
                # differential speed
                p_left = BASE_SPEED + turn_correction
                p_right = BASE_SPEED - turn_correction
                
                # limit
                p_left = max(-MAX_SPEED, min(MAX_SPEED, p_left))
                p_right = max(-MAX_SPEED, min(MAX_SPEED, p_right))
                
                # --- state machine ---
                # default
                final_left = 0
                final_right = 0
                status_text = "WAIT"
                text_color = (255, 255, 255)

                if cover_ratio > DANGER_RATIO:
                    # too close
                    status_text = "BACK"
                    text_color = (0, 0, 255)
                    final_left, final_right = -180, -180 
                        
                elif cover_ratio > SAFE_RATIO:
                    # safe
                    status_text = "STOP"
                    text_color = (0, 255, 0) 
                    final_left, final_right = 0, 0
                        
                elif box_area < MIN_AREA:
                    # too far
                    # to get the PWM
                    status_text = "FOLLOW"
                    text_color = (255, 255, 0)
                    final_left = p_left
                    final_right = p_right
                        
                else:
                   # others
                    status_text = "HOLD"
                    final_left, final_right = 0, 0

                # --- publish and display ---
                
                cmd_str = f"{final_left},{final_right}"
                send_drive_cmd(cmd_str) 
                cv2.putText(frame, status_text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)

                info_str = f"L:{final_left} R:{final_right} Err:{error}"
                cv2.putText(frame, info_str, (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                print(f"[{status_text}] {cmd_str} | Error: {error}")
                               
        if not target_found:
            if not is_emergency_stop:
                send_drive_cmd("0,0") # stop
            cv2.putText(frame, "SEARCHING...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # draw the support line
        cv2.line(frame, (CENTER_X - DEAD_ZONE, 0), (CENTER_X - DEAD_ZONE, 480), (255, 255, 0), 1)
        cv2.line(frame, (CENTER_X + DEAD_ZONE, 0), (CENTER_X + DEAD_ZONE, 480), (255, 255, 0), 1)

        # update image global variable
        with lock:
            outputFrame = frame.copy()
        
        # ESC: exit
        #info_debug = f"Area: {int(box_area)} | Ratio: {cover_ratio:.2f}"
        #cv2.putText(frame, info_debug, (10, 380), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        cv2.imshow("Monitor", frame)
        if cv2.waitKey(1) == 27: break

    cap.release()
    cv2.destroyAllWindows()

# ==========================================
# 4. Flask
# ==========================================
def generate_mjpeg():
    global outputFrame, lock
    while True:
        with lock:
            if outputFrame is None: continue
            # encode the image in JPG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
            if not flag: continue
        # MJPEG
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

# define the route
@app.route("/video_feed")
def video_feed():
    return Response(generate_mjpeg(), mimetype = "multipart/x-mixed-replace; boundary=frame")

# ==========================================
# 5. main
# ==========================================
if __name__ == '__main__':
    t = threading.Thread(target=processing_thread)
    t.daemon = True
    t.start()
    
    print("System start！")
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)