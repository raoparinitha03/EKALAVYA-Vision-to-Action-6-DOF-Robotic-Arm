
import cv2
import numpy as np
import onnxruntime as ort
import serial
import time
from flask import Flask, Response

app = Flask(__name__)
MODEL_PATH = "best.onnx"

# 1. LOAD MODEL
session = ort.InferenceSession(MODEL_PATH)
input_name = session.get_inputs()[0].name

# 2. CONNECT ARDUINO
try:
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    time.sleep(2)
    print("✅ Arduino Connected")
except:
    ser = None
    print("⚠️ Arduino Not Found")

cap = cv2.VideoCapture(0)
robot_busy = False

def generate_frames():
    global robot_busy
    while True:
        success, frame = cap.read()
        if not success: break
        
        # Pre-process
        img = cv2.resize(frame, (640, 640))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        img = np.transpose(np.expand_dims(img, 0), (0, 3, 1, 2))
        
        # Inference
        outputs = session.run(None, {input_name: img})
        data = np.squeeze(outputs[0]) # Shape [6, 8400]

        # Find best detection in rows 4 and 5 (Class Scores)
        scores = np.max(data[4:, :], axis=0)
        best_idx = np.argmax(scores)
        max_conf = scores[best_idx]

        if max_conf > 0.6 and not robot_busy:
            # FIX: raw_x is between 0.0 and 1.0
            raw_x = data[0, best_idx]
            
            # Map Class ID
            label_id = np.argmax(data[4:, best_idx])
            label = "box" if label_id == 0 else "cylinder"

            # THE CORRECTED MATH (Normalized 0.0-1.0 to 120-60 degrees)
            # 0.0 (Left) -> 120 deg
            # 0.5 (Center) -> 90 deg
            # 1.0 (Right) -> 60 deg
            angle = int(120 - (raw_x * 60))
            angle = max(min(angle, 120), 60) # Keep in safe range

            # VISUAL FEEDBACK: Draw a green line where the AI sees the object
            line_x = int(raw_x * frame.shape[1])
            cv2.line(frame, (line_x, 0), (line_x, frame.shape[0]), (0, 255, 0), 3)
            cv2.putText(frame, f"ANGLE: {angle}", (line_x + 10, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            if ser:
                print(f"🤖 TRIGGER: {label} at {angle} degrees")
                ser.write(f"S {angle} {label}\n".encode())
                robot_busy = True

        # Check for DONE from Arduino
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode().strip()
                if "DONE" in line:
                    robot_busy = False
                    print("✅ Robot Ready for next object")
            except:
                pass

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return "<html><body style='background:#111;color:white;text-align:center;'>"\
           "<h1>Robot POV</h1><img src='/video_feed' width='640'></body></html>"

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

