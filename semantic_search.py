from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from db_config import get_db
import re

def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\sก-๙]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

semantic_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

entries = []
entry_vectors = None

def load_departments():
    global entries, entry_vectors

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    cursor.execute("SELECT * FROM department_aliases")
    aliases = cursor.fetchall()

    cursor.close()
    conn.close()

    entries.clear()
    texts = []

    for dept in departments:
        text = normalize_text(dept["canonical_name"])
        entry = {
            "dept": dept,
            "text": dept["canonical_name"],
            "type": "canonical"
        }
        entries.append(entry)
        texts.append(text)
        entries.append(entry)
        texts.append(text)

    for a in aliases:
        dept = next(
            (d for d in departments if d["id"] == a["department_id"] or d["canonical_name"] == a.get("canonical_name")),
            None
        )

        if dept:
            text = normalize_text(a["alias"])
            entries.append({
                "dept": dept,
                "text": a["alias"],
                "type": "alias"
            })
            texts.append(text)

    entry_vectors = semantic_model.encode(texts, normalize_embeddings=True)

    print("Total departments:", len(departments))
    print("Total aliases:", len(aliases))
    print("Total entries:", len(entries))
    print("Vector shape:", entry_vectors.shape)

def ai_search(query, top_k=3):
    global entry_vectors, entries

    if entry_vectors is None or len(entries) == 0:
        return None, 0

    print(f"\n--- เริ่มค้นหาแผนกจากคำว่า: '{query}' ---")

    query_normalized = normalize_text(query)
    ai_best_match = None
    ai_best_score = 0

    try:
        query_vector = semantic_model.encode([query_normalized], normalize_embeddings=True)
        scores = cosine_similarity(query_vector, entry_vectors)[0]
        top_indices = np.argsort(scores)[::-1][:top_k]

        best_index = top_indices[0]
        ai_best_score = scores[best_index]
        ai_best_match = entries[best_index]

        print(f"[1. AI Result] AI เดาว่าเป็น: '{ai_best_match['text']}' (ความมั่นใจ: {ai_best_score:.4f})")

    except Exception as e:
        print("Semantic search error:", e)
        return None, 0

    query_lower = query.lower()
    sorted_entries = sorted(entries, key=lambda x: len(x['text']), reverse=True)
    rule_based_match = None

    for entry in sorted_entries:
        alias_word = entry["text"].lower()
        if alias_word in query_lower:
            rule_based_match = entry
            break 

    if rule_based_match:
        print(f"[2. Rule-Based Override] ตรวจพบคำคีย์เวิร์ด: '{rule_based_match['text']}'")
        return rule_based_match["dept"], 1.0

    if ai_best_score >= 0.75:
        print(f"[2. AI Confirmed] ไม่มีคีย์เวิร์ดเป๊ะๆ -> ยอมรับผลลัพธ์จาก AI")
        return ai_best_match["dept"], ai_best_score
    
    print(f"-> คะแนน AI ต่ำเกินไป ({ai_best_score:.4f}) ตอบ unknown")
    return None, ai_best_score
