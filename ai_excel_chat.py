import random
from semantic_search import load_departments, ai_search
from intent_classifier import detect_intent
from db_config import get_db

load_departments()

it_kb_cache = []

def load_it_knowledgebase():
    global it_kb_cache
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT kb.id, kb.problem_name, kb.solution, 
                   GROUP_CONCAT(kw.keyword SEPARATOR ',') as keywords
            FROM it_knowledgebase kb
            LEFT JOIN it_kb_keywords kw ON kb.id = kw.kb_id
            GROUP BY kb.id
        """)
        it_kb_cache = cursor.fetchall()
        cursor.close()
        conn.close()
        print("[AI] Loaded IT Knowledgebase into cache.")
    except Exception as e:
        print(f"[AI] IT DB Load Error: {e}")

load_it_knowledgebase()

ABBR_MAP = {
    "er": "ฉุกเฉิน", "it": "ไอที", "คอม": "คอมพิวเตอร์",
    "เวช": "เวชระเบียน", "เด็ก": "กุมารเวช", "ฟัน": "ทันตกรรม",
    "ตา": "จักษุ", "ปัย": "ไป", "ยุ": "อยู่", "รัย": "อะไร",
    "เบอ": "เบอร์", "โท": "โทร", "เดก": "เด็ก"
}

def preprocess_query(text):
    words = text.lower().strip().split()
    processed = [ABBR_MAP.get(w, w) for w in words]
    return " ".join(processed)

def check_it_problem(text):
    text_lower = text.lower()
    for row in it_kb_cache:
        if not row['keywords']: continue
        keywords = [k.strip().lower() for k in row['keywords'].split(',')]
        for kw in keywords:
            if kw != "" and kw in text_lower:
                return row['solution'], row['problem_name'], row['id']
    return None, None, None

def search_department(text):
    text = preprocess_query(text)
    print(f"\n--- เริ่มวิเคราะห์ข้อความ: '{text}' ---")

    it_solution, problem_name, kb_id = check_it_problem(text)
    
    if it_solution:
        print(f"Debug -> Matched IT Problem: {problem_name}")
        mock_row = {"canonical_name": problem_name, "kb_id": kb_id}
        return it_solution, "it_support", mock_row, 1.0

    row, score = ai_search(text)
    intent = "unknown"
    answer = ""

    if not row or score < 0.75:
        answer = random.choice([
            "ขออภัยครับ ไม่พบข้อมูลแผนก หรือปัญหา IT ที่ระบุ ลองพิมพ์ใหม่อีกครั้งนะครับ",
            "ยังไม่พบข้อมูลนี้ในระบบ รบกวนอธิบายรายละเอียดเพิ่มเติมอีกนิดครับ"
        ])
        return answer, "unknown", None, score

    intent = detect_intent(text)
    dept_name = row['canonical_name']
    phone = row.get('phone_number')
    ext = row.get('internal_number')
    building = row.get('building')
    floor = row.get('floor')

    if intent == "phone":
        if not phone: answer = f"ขออภัยครับ ขณะนี้ยังไม่มีข้อมูลเบอร์ติดต่อของ {dept_name}"
        elif ext: answer = f"เบอร์ติดต่อของ {dept_name} คือ {phone} ต่อ {ext}"
        else: answer = f"เบอร์ติดต่อของ {dept_name} คือ {phone}"
    elif intent == "location":
        if not building and not floor: answer = f"ขออภัยครับ ขณะนี้ยังไม่มีข้อมูลตำแหน่งที่ตั้งของ {dept_name}"
        elif building and floor: answer = f"{dept_name} อยู่ที่อาคาร {building} ชั้น {floor}"
        elif building: answer = f"{dept_name} อยู่ที่อาคาร {building}"
        else: answer = f"{dept_name} อยู่ที่ชั้น {floor}"
    else:
        sentences = []
        if building and floor: sentences.append(f"{dept_name} อยู่ที่อาคาร {building} ชั้น {floor}")
        elif building: sentences.append(f"{dept_name} อยู่ที่อาคาร {building}")
        if phone: sentences.append(f"เบอร์ติดต่อ {phone}" + (f" ต่อ {ext}" if ext else ""))
        answer = " ".join(sentences) if sentences else f"มีข้อมูลของ {dept_name} ในระบบ แต่ยังไม่มีรายละเอียดเพิ่มเติม"

    return answer, intent, row, score
