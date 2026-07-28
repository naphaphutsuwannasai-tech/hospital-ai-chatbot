import cv2
import os
from ultralytics import YOLO

print("[Object Detector] กำลังโหลดสมอง AI YOLOv8 เตรียมพร้อม...")

try:
    model = YOLO('yolov8n.pt')
    print("[Object Detector] โหลดสมอง AI สำเร็จ! พร้อมลุย!")
except Exception as e:
    print(f"[Object Detector] โหลดโมเดลไม่สำเร็จ: {e}")
    model = None

def detect_it_objects(image_path):
    if model is None:
        return []
        
    print(f"\n[Object Detector] กำลังส่องวัตถุด้วยดวงตา YOLOv8...")
    try:
        results = model(image_path, conf=0.5, verbose=False)
        detected_objects = []
        
        for r in results:
            for box in r.boxes:
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                confidence = float(box.conf[0])
                
                if class_name == "tv":
                    detected_objects.append("computer_monitor")
                    print(f"  -> เจอหน้าจอคอมพิวเตอร์! (ความมั่นใจ: {confidence:.2f})")
                elif class_name in ["mouse", "keyboard", "laptop", "cell phone"]:
                    detected_objects.append(class_name)
                    print(f"  -> เจอ {class_name}! (ความมั่นใจ: {confidence:.2f})")
                    
        return list(set(detected_objects))
    except Exception as e:
        print(f"[Object Detector] Error: {e}")
        return []
