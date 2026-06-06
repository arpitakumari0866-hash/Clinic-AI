from flask import Flask, render_template, request, redirect, session, url_for, flash
from data_base import (
    create_tables, register_user, login_user,
    save_doctor_profile, save_patient_profile,
    get_patient_profile, get_doctor_profile,
    insert_submission, fetch_all_submissions,
    fetch_submissions_by_department, fetch_patient_submissions
)
from functools import wraps

app = Flask(__name__)
app.secret_key = "clinic_secret_key_2024"

create_tables()

# ─── TRANSLATIONS ────────────────────────────────────────────────────────────

translations = {
    "English":  {"yes": "Yes", "no": "No", "review": "Review Answers", "submit": "Submit to Doctor"},
    "Hindi":    {"yes": "हाँ", "no": "नहीं", "review": "उत्तर देखें", "submit": "डॉक्टर को भेजें"},
    "Kannada":  {"yes": "ಹೌದು", "no": "ಇಲ್ಲ", "review": "ಉತ್ತರ ಪರಿಶೀಲಿಸಿ", "submit": "ಡಾಕ್ಟರ್‌ಗೆ ಕಳುಹಿಸಿ"},
    "Tamil":    {"yes": "ஆம்", "no": "இல்லை", "review": "பதில் சரிபார்க்கவும்", "submit": "மருத்துவருக்கு அனுப்பு"},
    "Telugu":   {"yes": "అవును", "no": "కాదు", "review": "సమాధానాలు చూడండి", "submit": "డాక్టర్‌కు పంపండి"},
    "Malayalam":{"yes": "അതെ", "no": "ഇല്ല", "review": "ഉത്തരങ്ങൾ പരിശോധിക്കുക", "submit": "ഡോക്ടറിലേക്ക് അയക്കുക"},
    "Marathi":  {"yes": "होय", "no": "नाही", "review": "उत्तरे तपासा", "submit": "डॉक्टरकडे पाठवा"},
}

lang_map = {
    "Hindi": "hi", "Kannada": "kn", "Tamil": "ta",
    "Telugu": "te", "Malayalam": "ml", "Marathi": "mr"
}

department_symptoms = {
    "General":      ["fever","cough","fatigue","headache","nausea","vomiting","dizziness","body_pain","loss_of_appetite","weight_loss"],
    "Gynecology":   ["irregular_periods","missed_periods","heavy_bleeding","spotting","pelvic_pain","abdominal_pain","vaginal_discharge","pain_during_intercourse","breast_pain","hormonal_imbalance"],
    "Orthopedic":   ["joint_pain","back_pain","neck_pain","muscle_pain","stiffness","swelling","difficulty_walking","bone_pain","limited_movement","posture_problem"],
    "Cardiology":   ["chest_pain","shortness_of_breath","palpitations","high_blood_pressure","low_blood_pressure","fatigue","dizziness","swelling_in_legs","chest_tightness","irregular_heartbeat"],
    "Neurology":    ["headache","dizziness","memory_loss","confusion","seizures","numbness","weakness","blurred_vision","speech_problem","balance_issue"],
    "Pediatric":    ["fever","cough","runny_nose","vomiting","diarrhea","skin_rash","irritability","loss_of_appetite","sleep_problem","weight_loss"],
    "ENT":          ["ear_pain","hearing_loss","ringing_in_ears","sore_throat","runny_nose","sinus_pressure","nose_bleed","voice_change","difficulty_swallowing","common_cold"],
    "Oncology":     ["unexplained_weight_loss","persistent_fatigue","lump_or_mass","persistent_pain","persistent_cough","unusual_bleeding","skin_changes","difficulty_swallowing","chronic_fever","night_sweats"],
    "Dermatology":  ["skin_rash","itching","acne","hair_loss","dry_skin","skin_discoloration","nail_changes","blisters","wound_not_healing","excessive_sweating"],
    "Psychiatry":   ["anxiety","depression","mood_swings","sleep_disorder","panic_attacks","social_withdrawal","concentration_problems","appetite_changes","irritability","intrusive_thoughts"],
}

cache = {}

def translate_text(text, lang):
    clean = text.replace("_", " ").capitalize()
    if lang == "English":
        return clean
    key = text + lang
    if key in cache:
        return cache[key]
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='auto', target=lang_map[lang]).translate(clean)
        cache[key] = translated
        return translated
    except:
        return clean

# ─── AUTH DECORATORS ─────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def doctor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "doctor":
            flash("Access denied.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated

def patient_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "patient":
            flash("Access denied.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated

# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    if "user_id" in session:
        if session.get("role") == "doctor":
            return redirect(url_for("doctor_dashboard"))
        else:
            return redirect(url_for("patient_home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user, error = login_user(email, password)
        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["name"] = user["name"]
            if user["role"] == "doctor":
                return redirect(url_for("doctor_dashboard"))
            else:
                return redirect(url_for("patient_home"))
        flash(error, "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        role = request.form["role"]
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        user_id, error = register_user(email, password, role, name)
        if error:
            flash(error, "error")
            return render_template("signup.html", departments=list(department_symptoms.keys()))

        if role == "doctor":
            department = request.form.get("department", "General")
            qualification = request.form.get("qualification", "")
            save_doctor_profile(user_id, department, qualification)
        else:
            age = request.form.get("age", "")
            gender = request.form.get("gender", "")
            blood_group = request.form.get("blood_group", "")
            phone = request.form.get("phone", "")
            address = request.form.get("address", "")
            medical_history = request.form.get("medical_history", "")
            allergies = request.form.get("allergies", "")
            current_medications = request.form.get("current_medications", "")
            emergency_contact = request.form.get("emergency_contact", "")
            save_patient_profile(user_id, age, gender, blood_group, phone, address,
                                  medical_history, allergies, current_medications, emergency_contact)

        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html", departments=list(department_symptoms.keys()))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── PATIENT ROUTES ───────────────────────────────────────────────────────────

@app.route("/patient")
@login_required
@patient_required
def patient_home():
    profile = get_patient_profile(session["user_id"])
    submissions = fetch_patient_submissions(session["user_id"])
    return render_template("patient_home.html",
                           profile=profile,
                           submissions=submissions,
                           departments=list(department_symptoms.keys()))


@app.route("/patient/profile", methods=["GET", "POST"])
@login_required
@patient_required
def patient_profile():
    if request.method == "POST":
        save_patient_profile(
            session["user_id"],
            request.form.get("age", ""),
            request.form.get("gender", ""),
            request.form.get("blood_group", ""),
            request.form.get("phone", ""),
            request.form.get("address", ""),
            request.form.get("medical_history", ""),
            request.form.get("allergies", ""),
            request.form.get("current_medications", ""),
            request.form.get("emergency_contact", "")
        )
        flash("Profile updated successfully!", "success")
        return redirect(url_for("patient_home"))
    profile = get_patient_profile(session["user_id"])
    return render_template("patient_profile.html", profile=profile)


@app.route("/patient/start", methods=["POST"])
@login_required
@patient_required
def start_consultation():
    session["language"] = request.form["language"]
    session["department"] = request.form["department"]
    session["answers"] = []
    session["q_index"] = 0
    session["patient_notes"] = request.form.get("notes", "")
    return redirect(url_for("questions"))


@app.route("/questions", methods=["GET", "POST"])
@login_required
@patient_required
def questions():
    dept = session.get("department")
    lang = session.get("language", "English")
    questions_list = department_symptoms.get(dept, [])
    index = session.get("q_index", 0)

    if request.method == "POST":
        ans = request.form.get("answer")
        answers = session.get("answers", [])
        if index < len(answers):
            answers[index] = ans
        else:
            answers.append(ans)
        session["answers"] = answers
        session["q_index"] = index + 1
        index = session["q_index"]

    if index >= len(questions_list):
        return redirect(url_for("review"))

    question = translate_text(questions_list[index], lang)
    t = translations.get(lang, translations["English"])
    prev_answer = session["answers"][index] if index < len(session.get("answers", [])) else None

    return render_template("questions.html",
                           question=question,
                           index=index + 1,
                           total=len(questions_list),
                           t=t,
                           prev_answer=prev_answer,
                           dept=dept)


@app.route("/review")
@login_required
@patient_required
def review():
    dept = session.get("department")
    lang = session.get("language", "English")
    t = translations.get(lang, translations["English"])
    questions_list = department_symptoms.get(dept, [])
    answers = session.get("answers", [])

    review_data = []
    for i, symptom in enumerate(questions_list):
        ans_raw = answers[i] if i < len(answers) else "no"
        answer = t["yes"] if ans_raw == "yes" else t["no"]
        review_data.append({"symptom": translate_text(symptom, lang), "answer": answer, "index": i})

    return render_template("review.html", review_data=review_data, t=t, dept=dept, lang=lang)


@app.route("/edit/<int:index>")
@login_required
@patient_required
def edit(index):
    session["q_index"] = index
    return redirect(url_for("questions"))


@app.route("/submit")
@login_required
@patient_required
def submit():
    dept = session.get("department")
    answers = session.get("answers", [])
    lang = session.get("language", "English")
    notes = session.get("patient_notes", "")
    questions_list = department_symptoms.get(dept, [])

    symptoms_text = ""
    for i, symptom in enumerate(questions_list):
        ans = "Yes" if i < len(answers) and answers[i] == "yes" else "No"
        symptoms_text += f"{symptom}: {ans}, "

    insert_submission(session["user_id"], dept, symptoms_text.rstrip(", "), lang, notes)

    # Clear consultation session data
    for k in ["language", "department", "answers", "q_index", "patient_notes"]:
        session.pop(k, None)

    flash("Your symptoms have been submitted to your doctor!", "success")
    return redirect(url_for("patient_home"))


# ─── DOCTOR ROUTES ────────────────────────────────────────────────────────────

@app.route("/doctor")
@login_required
@doctor_required
def doctor_dashboard():
    profile = get_doctor_profile(session["user_id"])
    dept = profile.get("department") if profile else None

    if dept:
        data = fetch_submissions_by_department(dept)
    else:
        data = fetch_all_submissions()

    patients = []
    for row in data:
        symptoms_dict = {}
        for part in row[11].split(", "):
            if ": " in part:
                k, v = part.split(": ", 1)
                symptoms_dict[k.replace("_", " ").capitalize()] = v

        patients.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "age": row[3],
            "gender": row[4],
            "blood_group": row[5],
            "phone": row[6],
            "medical_history": row[7],
            "allergies": row[8],
            "current_medications": row[9],
            "department": row[10],
            "symptoms": symptoms_dict,
            "notes": row[12],
            "language": row[13],
            "submitted_at": row[14],
        })

    return render_template("doctor_dashboard.html",
                           profile=profile,
                           patients=patients,
                           dept=dept)


if __name__ == "__main__":
    app.run(debug=True)
