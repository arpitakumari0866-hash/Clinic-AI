import sqlite3
import hashlib
import os

DB_PATH = "clinic.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_tables():
    conn = get_conn()
    c = conn.cursor()

    # Users table (both doctors and patients)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL,  -- 'doctor' or 'patient'
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Doctor profiles
    c.execute("""
    CREATE TABLE IF NOT EXISTS doctor_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        department TEXT NOT NULL,
        qualification TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Patient profiles
    c.execute("""
    CREATE TABLE IF NOT EXISTS patient_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        age INTEGER,
        gender TEXT,
        blood_group TEXT,
        phone TEXT,
        address TEXT,
        medical_history TEXT,
        allergies TEXT,
        current_medications TEXT,
        emergency_contact TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    # Symptom submissions
    c.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_user_id INTEGER NOT NULL,
        department TEXT NOT NULL,
        symptoms TEXT NOT NULL,
        language TEXT DEFAULT 'English',
        notes TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

# --- AUTH ---

def register_user(email, password, role, name):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password, role, name) VALUES (?, ?, ?, ?)",
                  (email.lower().strip(), hash_password(password), role, name))
        conn.commit()
        return c.lastrowid, None
    except sqlite3.IntegrityError:
        return None, "Email already registered."
    finally:
        conn.close()

def login_user(email, password):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, role, name FROM users WHERE email=? AND password=?",
              (email.lower().strip(), hash_password(password)))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "role": row[1], "name": row[2]}, None
    return None, "Invalid email or password."

# --- PROFILES ---

def save_doctor_profile(user_id, department, qualification):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO doctor_profiles (user_id, department, qualification)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET department=excluded.department, qualification=excluded.qualification
    """, (user_id, department, qualification))
    conn.commit()
    conn.close()

def save_patient_profile(user_id, age, gender, blood_group, phone, address,
                          medical_history, allergies, current_medications, emergency_contact):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO patient_profiles
            (user_id, age, gender, blood_group, phone, address, medical_history, allergies, current_medications, emergency_contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            age=excluded.age, gender=excluded.gender, blood_group=excluded.blood_group,
            phone=excluded.phone, address=excluded.address, medical_history=excluded.medical_history,
            allergies=excluded.allergies, current_medications=excluded.current_medications,
            emergency_contact=excluded.emergency_contact
    """, (user_id, age, gender, blood_group, phone, address,
          medical_history, allergies, current_medications, emergency_contact))
    conn.commit()
    conn.close()

def get_patient_profile(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT u.name, u.email, pp.age, pp.gender, pp.blood_group, pp.phone,
               pp.address, pp.medical_history, pp.allergies, pp.current_medications, pp.emergency_contact
        FROM users u
        LEFT JOIN patient_profiles pp ON u.id = pp.user_id
        WHERE u.id = ?
    """, (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "name": row[0], "email": row[1], "age": row[2], "gender": row[3],
            "blood_group": row[4], "phone": row[5], "address": row[6],
            "medical_history": row[7], "allergies": row[8],
            "current_medications": row[9], "emergency_contact": row[10]
        }
    return None

def get_doctor_profile(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT u.name, u.email, dp.department, dp.qualification
        FROM users u
        LEFT JOIN doctor_profiles dp ON u.id = dp.user_id
        WHERE u.id = ?
    """, (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"name": row[0], "email": row[1], "department": row[2], "qualification": row[3]}
    return None

# --- SUBMISSIONS ---

def insert_submission(patient_user_id, department, symptoms, language, notes):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO submissions (patient_user_id, department, symptoms, language, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (patient_user_id, department, symptoms, language, notes))
    conn.commit()
    conn.close()

def fetch_all_submissions():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.id, u.name, u.email,
               pp.age, pp.gender, pp.blood_group, pp.phone,
               pp.medical_history, pp.allergies, pp.current_medications,
               s.department, s.symptoms, s.notes, s.language, s.submitted_at
        FROM submissions s
        JOIN users u ON s.patient_user_id = u.id
        LEFT JOIN patient_profiles pp ON u.id = pp.user_id
        ORDER BY s.submitted_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def fetch_submissions_by_department(department):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.id, u.name, u.email,
               pp.age, pp.gender, pp.blood_group, pp.phone,
               pp.medical_history, pp.allergies, pp.current_medications,
               s.department, s.symptoms, s.notes, s.language, s.submitted_at
        FROM submissions s
        JOIN users u ON s.patient_user_id = u.id
        LEFT JOIN patient_profiles pp ON u.id = pp.user_id
        WHERE s.department = ?
        ORDER BY s.submitted_at DESC
    """, (department,))
    rows = c.fetchall()
    conn.close()
    return rows

def fetch_patient_submissions(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, department, symptoms, notes, language, submitted_at
        FROM submissions WHERE patient_user_id = ?
        ORDER BY submitted_at DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows
