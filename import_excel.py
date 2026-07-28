import pandas as pd
import mysql.connector

# =========================
# CONFIG
# =========================
xlsx_path = "data/hospital.xlsx"

db_config = {
    "host": "localhost",
    "user": "root",
    "password": ".....",
    "database": "....."
}
# =========================
# HELPER FUNCTIONS
# =========================
def clean(value):
    """แปลง NaN → None และตัดช่องว่าง"""
    if pd.isna(value):
        return None
    return str(value).strip()

def clean_floor(value):
    """แก้ปัญหา 1.0 → 1"""
    if pd.isna(value):
        return None

    # ถ้าเป็น float เช่น 1.0
    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return str(value).strip()

# =========================
# READ EXCEL
# =========================
try:
    df_departments = pd.read_excel(xlsx_path, sheet_name="departments")
    df_aliases = pd.read_excel(xlsx_path, sheet_name="alias")
except Exception as e:
    print("อ่านไฟล์ Excel ไม่สำเร็จ:", e)
    exit()

# =========================
# CONNECT DATABASE
# =========================
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
except Exception as e:
    print("เชื่อมต่อฐานข้อมูลไม่ได้:", e)
    exit()
# =========================
# INSERT departments
# =========================
for _, row in df_departments.iterrows():
    cursor.execute("""
        INSERT INTO departments
        (canonical_name, building, floor, phone_number, internal_number)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            building=VALUES(building),
            floor=VALUES(floor),
            phone_number=VALUES(phone_number),
            internal_number=VALUES(internal_number)
    """, (
        clean(row["canonical_name"]),
        clean(row["building"]),
        clean_floor(row["floor"]),
        clean(row["phone_number"]),
        clean(row["internal_number"])
    ))
# =========================
# INSERT aliases
# =========================
for _, row in df_aliases.iterrows():
    cursor.execute("""
        INSERT IGNORE INTO department_aliases
        (canonical_name, alias)
        VALUES (%s, %s)
    """, (
        clean(row["canonical_name"]),
        clean(row["alias"])
    ))
# =========================
# COMMIT & CLOSE
# =========================
conn.commit()
cursor.close()
conn.close()

print("Import Excel → MySQL สำเร็จ")
