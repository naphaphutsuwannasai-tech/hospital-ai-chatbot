import os
import shutil
import logging
from logging.handlers import RotatingFileHandler
import imagehash
from flask import Flask, request, jsonify, send_file, session, render_template, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image

from semantic_search import load_departments
from ai_excel_chat import search_department, load_it_knowledgebase
from db_config import get_db
from ocr_module import extract_text_from_image
from image_matcher import find_matching_image
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_ai_hospital_key")

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('static/db_images', exist_ok=True)

# ---------------------------------------------------------
# ระบบ Logging (Thread-safe)
# ---------------------------------------------------------
log_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log_handler = RotatingFileHandler("chat.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
log_handler.setFormatter(log_formatter)
app_logger = logging.getLogger("HospitalAIChat")
app_logger.setLevel(logging.INFO)
app_logger.addHandler(log_handler)

print("Loading AI Data & Departments...")
load_departments()
load_it_knowledgebase()
print("Departments loaded.")

def log_chat(user_query, intent, department_name, score, response, image_path=None, dept_id=None, kb_id=None):
    try:
        app_logger.info(f"[USER: {user_query}] -> [INTENT: {intent}] [DEPT: {department_name}]")
        conn = get_db()
        cursor = conn.cursor()
        sql = """INSERT INTO question_logs 
                 (question, ai_result, found, intent, score, matched_dept, matched_department_id, matched_kb_id, image_path) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        is_found = 1 if (department_name and department_name != "Unknown") or intent == "it_support" else 0
        cursor.execute(sql, (user_query, response, is_found, intent, float(score) if score else 0.0, 
                             department_name, dept_id, kb_id, image_path))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        app_logger.error(f"Log Error DB: {e}")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    return send_file("index.html")

@app.route("/ask")
def ask():
    q = request.args.get("q", "").strip()
    if not q: return jsonify({"answer": "กรุณาพิมพ์คำถาม"})
    if len(q) < 2: return jsonify({"answer": "ข้อความสั้นเกินไปค่ะ", "intent": "unknown", "department": "Unknown", "score": 0.0})

    try:
        escalate_words = ["ทำไม่ได้", "ทำแล้วไม่ได้", "ทำตามแล้วไม่ได้", "แก้ไขไม่ได้", "ซ่อมไม่ได้", "ยังไม่หาย", "ยังใช้ไม่ได้", "ลองแล้วไม่ได้", "ลองแล้วเปิดไม่ติด", "ลองแล้วไม่ติด", "ยังไม่ติด", "ไม่ได้ผล"]
        is_escalate = any(word in q.replace(" ", "") for word in escalate_words)

        dept_id = None
        kb_id = None

        if is_escalate:
            intent = "escalate_to_it"
            score = 1.0
            dept_name = "Unknown"
            final_answer = ""
        else:
            result = search_department(q)
            final_answer, intent, department, score = result[0], result[1], result[2], result[3]
            dept_name = department.get("canonical_name", "Unknown") if isinstance(department, dict) else "Unknown"
            if isinstance(department, dict):
                dept_id = department.get("id") if "id" in department and "kb_id" not in department else None
                kb_id = department.get("kb_id")

        if intent == "escalate_to_it":
            remembered_problem = session.get('last_problem', 'อุปกรณ์ไอที')
            remembered_image = session.get('last_asset_image', 'images/asset_sticker_format.jpg')
            failed_fix_response = f"""
                <div style='font-family: sans-serif; line-height: 1.6; color: #333;'>
                    <p style='color: #d9534f; font-weight: bold;'>เบื้องต้นถ้าแก้ไขไม่ได้ รบกวนเปิด Ticket นะคะ</p>
                    <p>อาการที่บันทึกไว้: <b>{remembered_problem}</b></p>
                    <p style='margin-top: 15px; font-weight: bold;'>วิธีดูเลขครุภัณฑ์สำหรับปัญหานี้:</p>
                    <div style='text-align: center; border: 2px solid #5cb85c; border-radius: 8px; padding: 10px; background-color: #f0fff0;'>
                        <img src='/static/{remembered_image}' style='max-width: 100%; border-radius: 4px; border: 1px solid #ddd;'>
                    </div>
                </div>
            """
            session.pop('last_problem', None)
            session.pop('last_asset_image', None)
            log_chat(q, "escalate_to_it", "IT Support", float(score), "แนะนำการเปิด Ticket")
            return jsonify({"answer": failed_fix_response, "intent": "escalate_to_it", "department": "IT Support", "score": float(score)})

        if dept_name != "Unknown": session['last_problem'] = dept_name
        log_chat(q, intent, dept_name, score, final_answer, dept_id=dept_id, kb_id=kb_id)
        return jsonify({"answer": final_answer, "intent": intent, "department": dept_name, "score": float(score) if score else 0.0})
    except Exception as e:
        app_logger.error(f"/ask Exception: {e}")
        return jsonify({"answer": "เกิดข้อผิดพลาด"}), 500

@app.route("/api/ask-multimodal", methods=["POST"])
def ask_multimodal():
    user_text = request.form.get("q", "").strip()
    image_file = request.files.get("image")
    combined_query = user_text
    filepath = None
    extracted_text = ""

    if image_file and image_file.filename != '':
        if not allowed_file(image_file.filename):
            return jsonify({"answer": "รองรับไฟล์รูปภาพเท่านั้นค่ะ"}), 400
            
        filename = secure_filename(image_file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace('\\', '/')
        image_file.save(filepath)
        try:
            img = Image.open(filepath)
            if img.mode != 'RGB': img = img.convert('RGB')
            img.thumbnail((600, 600))
            img.save(filepath, format='JPEG', quality=80, optimize=True)
        except Exception as e: 
            app_logger.error(f"Image Optimization Error: {e}")

        if user_text == "":
            try:
                matched_image_data = find_matching_image(filepath)
                if matched_image_data:
                    session['last_problem'] = matched_image_data["problem"]
                    session['last_asset_image'] = matched_image_data.get("example_image", "images/asset_sticker_format.jpg")
                    final_answer = matched_image_data["answer"]
                    problem_name = matched_image_data["problem"]
                    kb_id = matched_image_data["kb_id"]
                    log_chat(f"[IMAGE MATCH] {problem_name}", "it_support", problem_name, 1.0, final_answer, filepath, kb_id=kb_id)
                    return jsonify({"extracted_text": f"[จดจำรูปภาพได้: {problem_name}]", "matched_dept": problem_name, "answer": final_answer, "score": 1.0})
            except Exception as e: 
                app_logger.error(f"Image Matcher Error: {e}")

        if user_text == "":
            try:
                from object_detector import detect_it_objects
                found_objects = detect_it_objects(filepath)
                if found_objects:
                    conn = get_db()
                    cursor = conn.cursor(dictionary=True)
                    target_object = found_objects[0]
                    cursor.execute("SELECT * FROM it_categories WHERE object_detected = %s", (target_object,))
                    cat_data = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    if cat_data:
                        formal_name = cat_data['formal_category_name']
                        example_text = cat_data['example_description']
                        final_answer = f"ตรวจพบ **{formal_name}**<br>ตัวอย่างแจ้งซ่อม: *{example_text}*"
                        log_chat(f"[OBJECT MATCH] เจอ {target_object}", "it_support", formal_name, 1.0, final_answer, filepath)
                        return jsonify({"extracted_text": f"[ตรวจพบ {target_object}]", "matched_dept": formal_name, "answer": final_answer, "score": 1.0})
            except Exception as e: 
                app_logger.error(f"YOLO Detector Error: {e}")

        extracted_text = extract_text_from_image(filepath)
        if extracted_text: combined_query = f"{user_text} {extracted_text}".strip()

    if not combined_query:
        if filepath: return jsonify({"extracted_text": "", "matched_dept": "Unknown", "answer": "ไม่พบข้อมูลจากภาพค่ะ", "score": 0})
        return jsonify({"answer": "ส่งรูปด้วยค่ะ"}), 400

    try:
        escalate_words = ["ทำไม่ได้", "ทำแล้วไม่ได้", "ทำตามแล้วไม่ได้", "แก้ไขไม่ได้", "ซ่อมไม่ได้", "ยังไม่หาย", "ยังใช้ไม่ได้", "ลองแล้วไม่ได้", "ลองแล้วเปิดไม่ติด", "ลองแล้วไม่ติด", "ยังไม่ติด", "ไม่ได้ผล"]
        is_escalate = any(word in combined_query.replace(" ", "") for word in escalate_words)
        
        dept_id = None
        kb_id = None

        if is_escalate:
            intent = "escalate_to_it"
            score = 1.0
            dept_name = "Unknown"
            final_answer = ""
        else:
            result = search_department(combined_query)
            final_answer, intent, department, score = result[0], result[1], result[2], result[3]
            dept_name = department.get("canonical_name", "Unknown") if isinstance(department, dict) else "Unknown"
            if isinstance(department, dict):
                dept_id = department.get("id") if "id" in department and "kb_id" not in department else None
                kb_id = department.get("kb_id")

        if intent == "escalate_to_it":
            remembered_problem = session.get('last_problem', 'อุปกรณ์ไอที')
            remembered_image = session.get('last_asset_image', 'images/asset_sticker_format.jpg')
            failed_fix_response = f"""<div style='font-family: sans-serif; line-height: 1.6; color: #333;'>
                    <p style='color: #d9534f; font-weight: bold;'>เบื้องต้นถ้าแก้ไขไม่ได้ รบกวนเปิด Ticket นะคะ</p>
                    <p>อาการที่บันทึกไว้: <b>{remembered_problem}</b></p>
                    <p style='margin-top: 15px; font-weight: bold;'>วิธีดูเลขครุภัณฑ์สำหรับปัญหานี้:</p>
                    <div style='text-align: center; border: 2px solid #5cb85c; border-radius: 8px; padding: 10px; background-color: #f0fff0;'>
                        <img src='/static/{remembered_image}' style='max-width: 100%; border-radius: 4px; border: 1px solid #ddd;'>
                    </div></div>"""
            session.pop('last_problem', None)
            session.pop('last_asset_image', None)
            log_chat(f"[ESCALATE] ทำไม่ได้", "escalate_to_it", "IT Support", float(score), "แนะนำการเปิด Ticket", filepath)
            return jsonify({"extracted_text": combined_query, "matched_dept": "IT Support", "answer": failed_fix_response, "score": float(score)})

        if dept_name != "Unknown": session['last_problem'] = dept_name
        display_answer = final_answer
        if filepath and extracted_text:
            display_answer = f"พบข้อมูล <b>'{dept_name}'</b><br>{final_answer}"
        
        log_type = "[MULTIMODAL]" if filepath else "[TEXT]"
        log_chat(f"{log_type} {combined_query}", intent, dept_name, score, display_answer, filepath, dept_id, kb_id)
        
        return jsonify({"answer": display_answer, "intent": intent, "extracted_text": combined_query, "matched_dept": dept_name, "score": float(score) if score else 0.0})
    except Exception as e:
        app_logger.error(f"/api/ask-multimodal Exception: {e}")
        return jsonify({"answer": "เกิดข้อผิดพลาด"}), 500

@app.route("/admin")
def admin_panel():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT kb.*, 
               GROUP_CONCAT(DISTINCT kw.keyword SEPARATOR ',') as keywords,
               GROUP_CONCAT(DISTINCT img.image_filename SEPARATOR ',') as image_filename
        FROM it_knowledgebase kb
        LEFT JOIN it_kb_keywords kw ON kb.id = kw.kb_id
        LEFT JOIN it_kb_images img ON kb.id = img.kb_id
        GROUP BY kb.id ORDER BY kb.id DESC
    """)
    knowledge_data = cursor.fetchall()
    
    cursor.execute("SELECT * FROM question_logs WHERE image_path IS NOT NULL ORDER BY id DESC LIMIT 30")
    user_logs = cursor.fetchall()
    cursor.execute("SELECT * FROM departments ORDER BY canonical_name ASC")
    departments = cursor.fetchall()
    cursor.execute("SELECT * FROM department_aliases ORDER BY alias ASC")
    aliases = cursor.fetchall()
    cursor.execute("SELECT * FROM it_categories ORDER BY id ASC")
    ai_categories = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("admin.html", knowledge_data=knowledge_data, user_logs=user_logs, departments=departments, aliases=aliases, ai_categories=ai_categories)

@app.route("/admin/kb/add", methods=["POST"])
def admin_kb_add():
    p_name = request.form.get("problem_name")
    sol = request.form.get("solution")
    keywords = request.form.get("keywords", "")
    img_file = request.files.get("image_file")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO it_knowledgebase (problem_name, solution, example_image) VALUES (%s, %s, %s)", 
                   (p_name, sol, 'images/asset_sticker_format.jpg'))
    kb_id = cursor.lastrowid
    
    if img_file and img_file.filename != '':
        filename = secure_filename(img_file.filename)
        filepath = os.path.join('static/db_images', filename)
        img_file.save(filepath)
        
        try:
            img_hash = str(imagehash.phash(Image.open(filepath)))
        except: img_hash = None
            
        cursor.execute("INSERT INTO it_kb_images (kb_id, image_filename, image_hash) VALUES (%s, %s, %s)", (kb_id, filename, img_hash))
        
    if keywords:
        for kw in [k.strip() for k in keywords.split(',') if k.strip()]:
            cursor.execute("INSERT INTO it_kb_keywords (kb_id, keyword) VALUES (%s, %s)", (kb_id, kw))
            
    conn.commit()
    cursor.close()
    conn.close()
    load_it_knowledgebase()
    return redirect(url_for('admin_panel'))

@app.route("/admin/kb/delete/<int:id>")
def admin_kb_delete(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM it_knowledgebase WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    load_it_knowledgebase()
    return redirect(url_for('admin_panel'))

@app.route("/admin/teach", methods=["POST"])
def admin_teach():
    log_img_path = request.form.get("log_image_path").replace('\\', '/')
    kb_id = request.form.get("kb_id")
    filename = os.path.basename(log_img_path)
    new_path = os.path.join('static/db_images', filename)
   
    if os.path.exists(log_img_path):
        shutil.copy(log_img_path, new_path)
        try:
            img_hash = str(imagehash.phash(Image.open(new_path)))
        except: img_hash = None
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO it_kb_images (kb_id, image_filename, image_hash) VALUES (%s, %s, %s)", (kb_id, filename, img_hash))
        conn.commit()
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_panel'))

@app.route("/admin/dept/add", methods=["POST"])
def admin_dept_add():
    c_name = request.form.get("canonical_name")
    bldg = request.form.get("building")
    flr = request.form.get("floor")
    phone = request.form.get("phone_number")
    internal = request.form.get("internal_number")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO departments (canonical_name, building, floor, phone_number, internal_number) VALUES (%s, %s, %s, %s, %s)", (c_name, bldg, flr, phone, internal))
    conn.commit()
    cursor.close()
    conn.close()
    load_departments()
    return redirect(url_for('admin_panel'))

@app.route("/admin/dept/delete/<int:id>")
def admin_dept_delete(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM departments WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    load_departments()
    return redirect(url_for('admin_panel'))

@app.route("/admin/alias/add", methods=["POST"])
def admin_alias_add():
    c_name = request.form.get("canonical_name")
    alias = request.form.get("alias")
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM departments WHERE canonical_name = %s", (c_name,))
    dept = cursor.fetchone()
    if dept:
        cursor.execute("INSERT INTO department_aliases (department_id, alias) VALUES (%s, %s)", (dept['id'], alias))
        conn.commit()
    cursor.close()
    conn.close()
    load_departments()
    return redirect(url_for('admin_panel'))

@app.route("/admin/alias/delete/<int:id>")
def admin_alias_delete(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM department_aliases WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    load_departments()
    return redirect(url_for('admin_panel'))

if __name__ == "__main__":
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    if FLASK_ENV == "development":
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
    else:
        from waitress import serve
        print("Starting server on http://0.0.0.0:5000 (Production Mode)")
        serve(app, host="0.0.0.0", port=5000, threads=6)
