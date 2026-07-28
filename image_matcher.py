import imagehash
from PIL import Image
import os
from db_config import get_db

DB_FOLDER = "static/db_images"

def find_matching_image(user_image_path, threshold=20):
    print("\n[Image Matcher] กำลังเทียบเค้าโครงรูปภาพ...")
    try:
        user_hash = imagehash.phash(Image.open(user_image_path))
        best_match = None
        lowest_diff = 100 

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT kb.id as kb_id, kb.problem_name, kb.solution, kb.example_image, img.image_filename, img.image_hash 
            FROM it_kb_images img
            JOIN it_knowledgebase kb ON img.kb_id = kb.id
        """)
        db_records = cursor.fetchall()
        cursor.close()
        conn.close()

        for row in db_records:
            if row['image_hash']:
                db_hash = imagehash.hex_to_hash(row['image_hash'])
            else:
                db_img_path = os.path.join(DB_FOLDER, row['image_filename'])
                if os.path.exists(db_img_path):
                    db_hash = imagehash.phash(Image.open(db_img_path))
                else:
                    continue
                    
            difference = user_hash - db_hash
            print(f"  -> เทียบกับ {row['image_filename']} | ความต่าง: {difference}")
            
            if difference < lowest_diff and difference <= threshold:
                lowest_diff = difference
                best_match = {
                    "kb_id": row['kb_id'],
                    "problem": row['problem_name'],
                    "answer": row['solution'],
                    "example_image": row.get("example_image", "images/asset_sticker_format.jpg")
                }
                    
        if best_match:
            print(f"[Image Matcher] แมตช์สำเร็จ! (Diff: {lowest_diff})")
            return best_match
            
        return None
    except Exception as e:
        print(f"[Image Matcher] Error: {e}")
        return None
