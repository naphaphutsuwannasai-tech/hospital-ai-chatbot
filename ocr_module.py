import pytesseract
from PIL import Image, ImageOps, ImageFilter
import re
import os
from dotenv import load_dotenv

load_dotenv()

tesseract_path = os.getenv('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

def extract_text_from_image(image_path):
    print("\n[AI Vision] Tesseract กำลังเพ่งมองรูปภาพ...")
    try:
        img = Image.open(image_path)
        width, height = img.size
        img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        img = img.convert('L')
        img = ImageOps.invert(img)
        img = img.point(lambda x: 0 if x < 128 else 255, '1')
        img = img.filter(ImageFilter.SHARPEN)
        
        custom_config = r'--oem 3 --psm 3'
        text = pytesseract.image_to_string(img, lang='tha+eng', config=custom_config)
        
        clean_text = re.sub(r'\s+', ' ', text).strip()
        print(f"[AI Vision] ผลการอ่าน: '{clean_text}'")
        return clean_text
    except Exception as e:
        print(f"[AI Vision] Error: {e}")
        return ""
