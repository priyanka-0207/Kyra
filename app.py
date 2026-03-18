"""
Kyron Medical - Patient AI Assistant Backend
Flask + OpenAI GPT-4o + Vapi Voice AI
"""

import os
import json
import uuid
import sqlite3
import random
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import requests
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "kyron-dev-secret-change-in-prod")
CORS(app, supports_credentials=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID")
VAPI_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")

def openai_chat(messages: list, system_prompt: str = "", max_tokens: int = 1024) -> str:
    openai_messages = []

    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})

    for msg in messages:
        openai_messages.append({"role": msg["role"], "content": msg["content"]})

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )

        return response.choices[0].message.content or "I'm sorry, I couldn't process that. Could you try again?"

    except Exception as e:
        error_msg = str(e)
        print(f"[OPENAI ERROR] {error_msg}")

        if "rate_limit" in error_msg.lower() or "429" in error_msg:
            return "I'm getting a lot of requests right now. Please try again in a moment."
        if "timeout" in error_msg.lower():
            return "I'm taking a bit longer than usual. Could you try again?"

        return "Something went wrong on my end. Please try again."


def openai_simple(prompt: str, max_tokens: int = 200) -> str:
    return openai_chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
    )

DB_PATH = "kyron_medical.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            body_parts TEXT NOT NULL,
            bio TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS availabilities (
            id TEXT PRIMARY KEY,
            doctor_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            is_booked INTEGER DEFAULT 0,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            first_name TEXT, last_name TEXT,
            dob TEXT, phone TEXT, email TEXT,
            sms_opt_in INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            doctor_id TEXT NOT NULL,
            availability_id TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'confirmed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            patient_id TEXT,
            messages TEXT DEFAULT '[]',
            context TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS call_session_map (
            call_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            phone_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS phone_session_map (
            phone_number TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def seed_doctors_and_availabilities():
    conn = get_db()
    if conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0] > 0:
        conn.close()
        return

    doctors = [
        {
            "id": "dr-chen", "name": "Dr. Sarah Chen",
            "specialty": "Orthopedics",
            "body_parts": "knee,hip,shoulder,elbow,wrist,ankle,joint,bone,back,spine,neck,leg,arm,fracture,sprain,arthritis,tendon,ligament,musculoskeletal",
            "bio": "Board-certified orthopedic surgeon with 15 years of experience in sports medicine and joint reconstruction.",
        },
        {
            "id": "dr-patel", "name": "Dr. Raj Patel",
            "specialty": "Cardiology",
            "body_parts": "heart,chest,cardiovascular,blood pressure,hypertension,palpitations,arrhythmia,cholesterol,cardiac,coronary,circulation,pulse,heartbeat",
            "bio": "Fellowship-trained cardiologist specializing in preventive cardiology and heart failure management.",
        },
        {
            "id": "dr-martinez", "name": "Dr. Elena Martinez",
            "specialty": "Dermatology",
            "body_parts": "skin,rash,acne,mole,eczema,psoriasis,dermatitis,hives,wart,lesion,itching,sunburn,melanoma,hair loss,scalp,nail,fungal",
            "bio": "Dermatologist with expertise in medical and cosmetic dermatology, skin cancer screening, and chronic skin conditions.",
        },
        {
            "id": "dr-thompson", "name": "Dr. James Thompson",
            "specialty": "Gastroenterology",
            "body_parts": "stomach,abdomen,digestive,intestine,colon,liver,gallbladder,acid reflux,heartburn,nausea,bloating,constipation,diarrhea,ibs,crohn,ulcer,gut,bowel,gastric",
            "bio": "Gastroenterologist focused on inflammatory bowel disease, liver disorders, and advanced endoscopy.",
        },
        {
            "id": "dr-nguyen", "name": "Dr. Lisa Nguyen",
            "specialty": "Neurology",
            "body_parts": "brain,head,headache,migraine,seizure,numbness,tingling,dizziness,vertigo,memory,tremor,nerve,neurological,concussion,neuropathy,stroke,epilepsy",
            "bio": "Neurologist specializing in headache disorders, epilepsy management, and neurodegenerative diseases.",
        },
    ]

    for doc in doctors:
        conn.execute(
            "INSERT INTO doctors (id, name, specialty, body_parts, bio) VALUES (?, ?, ?, ?, ?)",
            (doc["id"], doc["name"], doc["specialty"], doc["body_parts"], doc["bio"]),
        )

    today = datetime.now().date()
    time_slots = [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00",
    ]

    for doc in doctors:
        for day_offset in range(1, 46):
            date = today + timedelta(days=day_offset)
            if date.weekday() >= 5:
                continue
            random.seed(hash(f"{doc['id']}-{date}"))
            day_slots = random.sample(time_slots, k=random.randint(5, 8))
            for t in sorted(day_slots):
                conn.execute(
                    "INSERT INTO availabilities (id, doctor_id, date, time, is_booked) VALUES (?, ?, ?, ?, 0)",
                    (str(uuid.uuid4()), doc["id"], date.isoformat(), t),
                )

    conn.commit()
    conn.close()
    print("[SEED] Doctors and availability slots created.")
PRACTICE_INFO = {
    "name": "Kyron Medical Group",
    "address": "450 Brookline Avenue, Suite 300, Boston, MA 02215",
    "phone": "(617) 555-0199",
    "hours": {
        "Monday-Friday": "8:00 AM - 5:00 PM",
        "Saturday": "9:00 AM - 1:00 PM",
        "Sunday": "Closed",
    },
}

def build_system_prompt():
    conn = get_db()
    doctors = conn.execute("SELECT * FROM doctors").fetchall()
    conn.close()

    docs_info = "\n".join(
        [f"- {d['name']} ({d['specialty']}): treats {d['body_parts'].replace(',', ', ')}" for d in doctors]
    )
    hours = ", ".join([f"{k}: {v}" for k, v in PRACTICE_INFO["hours"].items()])

    return f"""You are Kyra, a friendly and professional AI patient assistant for Kyron Medical Group. You help patients with:

1. **Appointment Scheduling** - Collect patient info, match to the right doctor, and book
2. **Prescription Refills** - Check refill status and help patients request refills
3. **Practice Information** - Share hours, address, contact details
4. **Appointment Management** - Help cancel or reschedule existing appointments

## Practice Information
- Name: {PRACTICE_INFO['name']}
- Address: {PRACTICE_INFO['address']}
- Phone: {PRACTICE_INFO['phone']}
- Hours: {hours}

## Available Doctors
{docs_info}

## Critical Rules
- NEVER provide medical advice, diagnoses, or treatment recommendations
- NEVER say anything that could be interpreted as a medical opinion
- If a patient describes symptoms, empathize but direct them to schedule with the appropriate doctor
- If someone mentions chest pain, difficulty breathing, severe bleeding, or any emergency: immediately tell them to call 911
- Be warm, empathetic, and conversational — not robotic
- Keep responses concise (2-3 sentences when possible)

## Appointment Scheduling Flow
1. Ask what body part or concern they have
2. Match to the appropriate doctor
3. Collect: first name, last name, date of birth, phone number, email
4. Show available times for the matched doctor
5. Confirm the booking and mention that a confirmation email will be sent

When you need to perform an action, respond with a JSON object in this format:
{{"function": "function_name", "args": {{...}}}}

Available functions:
- match_doctor: {{"function": "match_doctor", "args": {{"concern": "description"}}}}
- get_availability: {{"function": "get_availability", "args": {{"doctor_id": "dr-xxx", "preferred_day": "optional day like Tuesday"}}}}
- book_appointment: {{"function": "book_appointment", "args": {{"patient_first": "...", "patient_last": "...", "dob": "...", "phone": "...", "email": "...", "doctor_id": "...", "availability_id": "...", "reason": "...", "sms_opt_in": 0}}}}
- get_practice_info: {{"function": "get_practice_info", "args": {{}}}}
- check_prescription: {{"function": "check_prescription", "args": {{"patient_name": "...", "medication": "..."}}}}
- lookup_appointments: {{"function": "lookup_appointments", "args": {{"phone": "...", "email": "..."}}}}
- cancel_appointment: {{"function": "cancel_appointment", "args": {{"appointment_id": "..."}}}}
- estimate_wait: {{"function": "estimate_wait", "args": {{"doctor_id": "dr-xxx"}}}}

Be natural in conversation. Don't show the JSON to the patient."""


def match_doctor(concern: str) -> dict:
    conn = get_db()
    doctors = conn.execute("SELECT id, name, specialty, body_parts FROM doctors").fetchall()
    conn.close()

    docs_list = [{"id": d["id"], "name": d["name"], "specialty": d["specialty"], "body_parts": d["body_parts"]} for d in doctors]

    result_text = openai_simple(
        f"""Given this patient concern: "{concern}"
And these available doctors: {json.dumps(docs_list)}

Which doctor is the best match? If none treat this concern, say "none".
Respond with ONLY a JSON object: {{"doctor_id": "...", "reason": "brief reason"}} or {{"doctor_id": "none", "reason": "We don't have a specialist for that"}}"""
    )

    try:
        if "{" in result_text:
            json_str = result_text[result_text.index("{"):result_text.rindex("}") + 1]
            result = json.loads(json_str)
            if result["doctor_id"] != "none":
                conn = get_db()
                doc = conn.execute("SELECT * FROM doctors WHERE id = ?", (result["doctor_id"],)).fetchone()
                conn.close()
                if doc:
                    result["doctor_name"] = doc["name"]
                    result["specialty"] = doc["specialty"]
            return result
    except (json.JSONDecodeError, KeyError, ValueError):
        pass

    return {"doctor_id": "none", "reason": "Unable to determine the right specialist. Let me connect you with our front desk."}


def get_availability(doctor_id: str, preferred_day: str = None) -> list:
    conn = get_db()
    slots = conn.execute(
        """SELECT a.id, a.date, a.time, d.name as doctor_name
           FROM availabilities a JOIN doctors d ON a.doctor_id = d.id
           WHERE a.doctor_id = ? AND a.is_booked = 0 AND a.date >= date('now')
           ORDER BY a.date, a.time LIMIT 30""",
        (doctor_id,),
    ).fetchall()
    conn.close()

    results = [dict(s) for s in slots]

    if preferred_day:
        day_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
        target = day_map.get(preferred_day.lower().strip())
        if target is not None:
            results = [s for s in results if datetime.fromisoformat(s["date"]).weekday() == target]

    return results[:10]


def book_appointment(patient_data: dict, doctor_id: str, availability_id: str, reason: str) -> dict:
    conn = get_db()

    patient_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO patients (id, first_name, last_name, dob, phone, email, sms_opt_in) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (patient_id, patient_data["first_name"], patient_data["last_name"],
         patient_data["dob"], patient_data["phone"], patient_data["email"],
         patient_data.get("sms_opt_in", 0)),
    )

    conn.execute("UPDATE availabilities SET is_booked = 1 WHERE id = ?", (availability_id,))

    slot = conn.execute("SELECT * FROM availabilities WHERE id = ?", (availability_id,)).fetchone()
    doctor = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()

    appt_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO appointments (id, patient_id, doctor_id, availability_id, reason) VALUES (?, ?, ?, ?, ?)",
        (appt_id, patient_id, doctor_id, availability_id, reason),
    )
    conn.commit()
    conn.close()

    appt = {
        "appointment_id": appt_id,
        "patient_name": f"{patient_data['first_name']} {patient_data['last_name']}",
        "doctor_name": doctor["name"], "specialty": doctor["specialty"],
        "date": slot["date"], "time": slot["time"],
        "reason": reason, "address": PRACTICE_INFO["address"],
    }

    send_email_confirmation(patient_data["email"], appt)
    if patient_data.get("sms_opt_in"):
        send_sms_confirmation(patient_data["phone"], appt)

    return appt


def cancel_appointment(appointment_id: str) -> dict:
    conn = get_db()
    appt = conn.execute(
        """SELECT a.*, av.date, av.time, d.name as doctor_name
           FROM appointments a
           JOIN availabilities av ON a.availability_id = av.id
           JOIN doctors d ON a.doctor_id = d.id
           WHERE a.id = ?""",
        (appointment_id,),
    ).fetchone()

    if not appt:
        conn.close()
        return {"success": False, "message": "Appointment not found."}

    conn.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (appointment_id,))
    conn.execute("UPDATE availabilities SET is_booked = 0 WHERE id = ?", (appt["availability_id"],))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Appointment with {appt['doctor_name']} on {appt['date']} at {appt['time']} has been cancelled.",
    }


def lookup_patient_appointments(phone: str = None, email: str = None) -> list:
    conn = get_db()
    if phone:
        cleaned = phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "").replace("+1", "")
        patients = conn.execute(
            "SELECT * FROM patients WHERE REPLACE(REPLACE(REPLACE(phone, '-', ''), '(', ''), ')', '') LIKE ?",
            (f"%{cleaned}%",),
        ).fetchall()
    elif email:
        patients = conn.execute("SELECT * FROM patients WHERE email = ?", (email,)).fetchall()
    else:
        conn.close()
        return []

    appts = []
    for p in patients:
        rows = conn.execute(
            """SELECT a.*, av.date, av.time, d.name as doctor_name, d.specialty
               FROM appointments a
               JOIN availabilities av ON a.availability_id = av.id
               JOIN doctors d ON a.doctor_id = d.id
               WHERE a.patient_id = ? AND a.status != 'cancelled'
               ORDER BY av.date, av.time""",
            (p["id"],),
        ).fetchall()
        appts.extend([dict(r) for r in rows])

    conn.close()
    return appts


def estimate_next_available(doctor_id: str) -> dict:
    conn = get_db()
    slot = conn.execute(
        """SELECT a.date, a.time, d.name
           FROM availabilities a JOIN doctors d ON a.doctor_id = d.id
           WHERE a.doctor_id = ? AND a.is_booked = 0 AND a.date >= date('now')
           ORDER BY a.date, a.time LIMIT 1""",
        (doctor_id,),
    ).fetchone()

    this_week = conn.execute(
        "SELECT COUNT(*) FROM availabilities WHERE doctor_id = ? AND is_booked = 0 AND date >= date('now') AND date <= date('now', '+7 days')",
        (doctor_id,),
    ).fetchone()[0]

    conn.close()

    if not slot:
        return {"available": False, "message": "No availability in the next 45 days."}

    days = (datetime.fromisoformat(slot["date"]).date() - datetime.now().date()).days
    return {
        "available": True, "next_date": slot["date"], "next_time": slot["time"],
        "doctor_name": slot["name"], "days_until": days, "this_week_slots": this_week,
        "urgency_note": "Same-week availability!" if days <= 5 else f"Earliest opening is in {days} days.",
    }

def send_email_confirmation(email: str, appt: dict):
    if not SENDGRID_API_KEY:
        print(f"[EMAIL STUB] Would send to {email}: {appt['doctor_name']} on {appt['date']}")
        return
    try:
        requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
            json={
                "personalizations": [{"to": [{"email": email}]}],
                "from": {"email": "appointments@kyronmedical.com", "name": "Kyron Medical Group"},
                "subject": f"Appointment Confirmed - {appt['doctor_name']} on {appt['date']}",
                "content": [{"type": "text/html", "value": f"""
                    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
                    <div style="background:linear-gradient(135deg,#0D9488,#0F766E);padding:24px;border-radius:12px 12px 0 0">
                    <h1 style="color:white;margin:0">Appointment Confirmed</h1></div>
                    <div style="padding:24px;background:#f9fafb;border-radius:0 0 12px 12px">
                    <p>Hi {appt['patient_name']},</p>
                    <p>Your appointment has been scheduled:</p>
                    <div style="background:white;padding:16px;border-radius:8px;border-left:4px solid #0D9488">
                    <p><strong>Doctor:</strong> {appt['doctor_name']} ({appt['specialty']})</p>
                    <p><strong>Date:</strong> {appt['date']}</p>
                    <p><strong>Time:</strong> {appt['time']}</p>
                    <p><strong>Reason:</strong> {appt['reason']}</p>
                    <p><strong>Location:</strong> {appt['address']}</p></div>
                    <p style="margin-top:16px;color:#6b7280;font-size:14px">
                    Call {PRACTICE_INFO['phone']} to reschedule.</p></div></div>"""}],
            },
        )
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


def send_sms_confirmation(phone: str, appt: dict):
    if not TWILIO_SID:
        print(f"[SMS STUB] Would send to {phone}: {appt['doctor_name']} on {appt['date']}")
        return
    try:
        from twilio.rest import Client
        Client(TWILIO_SID, TWILIO_AUTH).messages.create(
            body=f"Kyron Medical: Appointment with {appt['doctor_name']} confirmed for {appt['date']} at {appt['time']}. Location: {appt['address']}. Call {PRACTICE_INFO['phone']} to reschedule.",
            from_=TWILIO_PHONE, to=phone,
        )
    except Exception as e:
        print(f"[SMS ERROR] {e}")

def execute_function(func_call: dict, ctx: dict) -> str:
    name = func_call.get("function")
    args = func_call.get("args", {})

    if name == "match_doctor":
        result = match_doctor(args.get("concern", ""))
        if result["doctor_id"] != "none":
            ctx["matched_doctor_id"] = result["doctor_id"]
            return f"Great match: {result['doctor_name']} ({result['specialty']}). {result['reason']}. Checking availability now."
        return f"{result['reason']} Would you like help with something else?"

    elif name == "get_availability":
        doc_id = args.get("doctor_id") or ctx.get("matched_doctor_id")
        if not doc_id:
            return "I need to match you with a doctor first. What's your concern?"
        slots = get_availability(doc_id, args.get("preferred_day"))
        if not slots:
            return "No slots match that preference. Want to try a different day?"
        ctx["available_slots"] = slots
        lines = [f"  {i+1}. {s['date']} ({datetime.fromisoformat(s['date']).strftime('%A')}) at {s['time']}" for i, s in enumerate(slots[:8])]
        return f"Available times with {slots[0]['doctor_name']}:\n" + "\n".join(lines) + "\n\nWhich works best? You can also ask for a specific day."

    elif name == "book_appointment":
        patient = {k: args.get(k, "") for k in ("first_name", "last_name", "dob", "phone", "email")}
        patient["first_name"] = args.get("patient_first", patient.get("first_name", ""))
        patient["last_name"] = args.get("patient_last", patient.get("last_name", ""))
        patient["sms_opt_in"] = args.get("sms_opt_in", 0)
        result = book_appointment(patient, args.get("doctor_id") or ctx.get("matched_doctor_id"), args.get("availability_id"), args.get("reason", "General consultation"))
        ctx["last_appointment"] = result
        ctx["patient_first_name"] = patient["first_name"]
        sms_note = " You'll also get a text confirmation." if patient.get("sms_opt_in") else ""
        return f"Booked! {result['doctor_name']} ({result['specialty']}) on {result['date']} at {result['time']}. Location: {result['address']}. Confirmation email sent to {patient['email']}.{sms_note}"

    elif name == "get_practice_info":
        hrs = "\n".join([f"  {k}: {v}" for k, v in PRACTICE_INFO["hours"].items()])
        return f"Kyron Medical Group\nAddress: {PRACTICE_INFO['address']}\nPhone: {PRACTICE_INFO['phone']}\nHours:\n{hrs}"

    elif name == "check_prescription":
        return f"Your {args.get('medication', 'medication')} refill is being processed and should be ready at your pharmacy within 24-48 hours. Call {PRACTICE_INFO['phone']} if you need it sooner."

    elif name == "lookup_appointments":
        appts = lookup_patient_appointments(phone=args.get("phone"), email=args.get("email"))
        if not appts:
            return "No upcoming appointments found. Would you like to schedule one?"
        lines = [f"- {a['doctor_name']} on {a['date']} at {a['time']} ({a['status']}) [ID: {a['id'][:8]}]" for a in appts]
        ctx["patient_appointments"] = appts
        return "Your appointments:\n" + "\n".join(lines)

    elif name == "cancel_appointment":
        result = cancel_appointment(args.get("appointment_id", ""))
        return result["message"]

    elif name == "estimate_wait":
        doc_id = args.get("doctor_id") or ctx.get("matched_doctor_id")
        if not doc_id:
            return "Which doctor would you like to check availability for?"
        est = estimate_next_available(doc_id)
        if not est["available"]:
            return est["message"]
        return f"{est['doctor_name']}'s next opening: {est['next_date']} at {est['next_time']} ({est['days_until']} days). {est['urgency_note']} {est['this_week_slots']} slots this week."

    return "I'm not sure how to handle that. Let me help another way."

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "").strip()
    session_id = data.get("session_id") or str(uuid.uuid4())

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    conn = get_db()
    sess = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()

    if sess:
        messages = json.loads(sess["messages"])
        ctx = json.loads(sess["context"])
    else:
        messages = []
        ctx = {}
        conn.execute("INSERT INTO chat_sessions (id, messages, context) VALUES (?, '[]', '{}')", (session_id,))
        conn.commit()

    messages.append({"role": "user", "content": user_message})

    system_prompt = build_system_prompt()
    if ctx:
        system_prompt += f"\n\nCurrent session context: {json.dumps(ctx)}"

    try:
        assistant_text = openai_chat(messages[-20:], system_prompt=system_prompt)

        if '{"function"' in assistant_text:
            try:
                start = assistant_text.index('{"function"')
                brace_count = 0
                end = start
                for i in range(start, len(assistant_text)):
                    if assistant_text[i] == "{": brace_count += 1
                    elif assistant_text[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break

                func_call = json.loads(assistant_text[start:end])
                func_result = execute_function(func_call, ctx)

                messages.append({"role": "assistant", "content": assistant_text})
                messages.append({"role": "user", "content": f"[SYSTEM: Function result — {func_result}. Respond naturally to the patient with this info. Do NOT show JSON.]"})

                assistant_text = openai_chat(messages[-20:], system_prompt=system_prompt)
                messages.pop()  
                messages.pop() 

            except (json.JSONDecodeError, ValueError):
                pass

        messages.append({"role": "assistant", "content": assistant_text})

        conn.execute(
            "UPDATE chat_sessions SET messages = ?, context = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(messages), json.dumps(ctx), session_id),
        )
        conn.commit()
        conn.close()

        return jsonify({"response": assistant_text, "session_id": session_id, "context": ctx})

    except Exception as e:
        conn.close()
        print(f"[CHAT ERROR] {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500


@app.route("/api/voice-handoff", methods=["POST"])
def voice_handoff():
    data = request.json
    phone = data.get("phone_number")
    session_id = data.get("session_id")

    if not phone or not session_id:
        return jsonify({"error": "Phone number and session ID required"}), 400

    conn = get_db()
    sess = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    if not sess:
        conn.close()
        return jsonify({"error": "Session not found"}), 404

    messages = json.loads(sess["messages"])
    ctx = json.loads(sess["context"])

    recent = messages[-10:]
    transcript = "\n".join([f"{'Patient' if m['role']=='user' else 'Kyra'}: {m['content']}" for m in recent])

    is_callback = ctx.get("call_dropped", False)
    if is_callback:
        ctx["call_dropped"] = False

    conn.execute("INSERT OR REPLACE INTO phone_session_map (phone_number, session_id, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (phone, session_id))
    conn.execute("UPDATE chat_sessions SET context = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(ctx), session_id))
    conn.commit()
    conn.close()

    vapi_prompt = f"""You are Kyra, a friendly AI assistant for Kyron Medical Group continuing a web chat conversation.
{"IMPORTANT: Previous call was disconnected. Acknowledge warmly and resume." if is_callback else ""}

Previous conversation:
{transcript}

Context: {json.dumps(ctx)}

Rules: NEVER provide medical advice. Be warm and professional. Help with scheduling, prescriptions, practice info.
Practice: Kyron Medical Group, 450 Brookline Ave Suite 300, Boston MA 02215. Phone: (617) 555-0199. Hours: Mon-Fri 8-5, Sat 9-1."""

    first_msg = (
        f"I'm sorry about that disconnection, {ctx.get('patient_first_name', '')}! I still have everything from our conversation. Let me pick up where we left off."
        if is_callback
        else f"Hi {ctx.get('patient_first_name', 'there')}! This is Kyra from Kyron Medical, picking up right where we left off from our chat."
    )

    if not VAPI_API_KEY:
        return jsonify({"success": True, "message": f"[DEV] Would call {phone}", "is_callback": is_callback, "call_id": f"dev-{uuid.uuid4()}"})

    try:
        resp = requests.post(
            "https://api.vapi.ai/call",
            headers={"Authorization": f"Bearer {VAPI_API_KEY}", "Content-Type": "application/json"},
            json={
                "phoneNumberId": VAPI_PHONE_NUMBER_ID,
                "customer": {"number": phone},
                "assistant": {
                    "model": {
                        "provider": "openai",
                        "model": OPENAI_MODEL,
                        "messages": [{"role": "system", "content": vapi_prompt}],
                    },
                    "voice": {"provider": "11labs", "voiceId": "21m00Tcm4TlvDq8ikWAM"},
                    "firstMessage": first_msg,
                    "transcriber": {"provider": "deepgram", "model": "nova-2"},
                },
            },
        )

        if resp.status_code in (200, 201):
            result = resp.json()
            conn = get_db()
            conn.execute("INSERT OR REPLACE INTO call_session_map (call_id, session_id, phone_number) VALUES (?, ?, ?)", (result.get("id"), session_id, phone))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "call_id": result.get("id"), "is_callback": is_callback})
        else:
            return jsonify({"error": "Failed to initiate call", "details": resp.text}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/vapi-webhook", methods=["POST"])
def vapi_webhook():
    data = request.json
    msg = data.get("message", {})
    event_type = msg.get("type")

    if event_type == "end-of-call-report":
        call_id = msg.get("call", {}).get("id", "")
        transcript = msg.get("transcript", "")
        ended_reason = msg.get("endedReason", "unknown")

        conn = get_db()
        mapping = conn.execute("SELECT * FROM call_session_map WHERE call_id = ?", (call_id,)).fetchone()
        if mapping:
            sess = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (mapping["session_id"],)).fetchone()
            if sess:
                messages = json.loads(sess["messages"])
                context = json.loads(sess["context"])
                messages.append({"role": "assistant", "content": f"[Voice call ended ({ended_reason}). Transcript: {transcript[:500]}]"})

                dropped = ended_reason in ("assistant-error", "phone-call-provider-closed-websocket", "silence-timed-out", "network-error")
                if dropped:
                    context["call_dropped"] = True

                conn.execute("UPDATE chat_sessions SET messages = ?, context = ? WHERE id = ?",
                    (json.dumps(messages), json.dumps(context), mapping["session_id"]))
                conn.commit()
        conn.close()

    elif event_type == "function-call":
        func_name = msg.get("functionCall", {}).get("name")
        func_args = msg.get("functionCall", {}).get("parameters", {})
        result = execute_function({"function": func_name, "args": func_args}, {})
        return jsonify({"result": result})

    elif event_type == "assistant-request":
        caller = msg.get("call", {}).get("customer", {}).get("number", "")
        conn = get_db()
        mapping = conn.execute("SELECT * FROM phone_session_map WHERE phone_number = ? ORDER BY updated_at DESC LIMIT 1", (caller,)).fetchone()

        ctx = {}
        transcript = ""
        name = "there"

        if mapping:
            sess = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (mapping["session_id"],)).fetchone()
            if sess:
                msgs = json.loads(sess["messages"])
                ctx = json.loads(sess["context"])
                name = ctx.get("patient_first_name", "there")
                recent = [m for m in msgs[-10:] if "[Voice call" not in m.get("content", "")]
                transcript = "\n".join([f"{'Patient' if m['role']=='user' else 'Kyra'}: {m['content']}" for m in recent])

        conn.close()
        has_history = bool(transcript)

        return jsonify({"assistant": {
            "model": {
                "provider": "openai", "model": OPENAI_MODEL,
                "messages": [{"role": "system", "content": f"""You are Kyra from Kyron Medical Group.
{"Returning patient. Previous conversation:" if has_history else "New caller."}
{transcript}
Context: {json.dumps(ctx)}
Rules: NEVER give medical advice. Be warm. Help with scheduling, prescriptions, practice info.
{"Reference the previous conversation naturally." if has_history else "Introduce yourself and ask how to help."}
Practice: 450 Brookline Ave Suite 300, Boston MA. (617) 555-0199. Mon-Fri 8-5, Sat 9-1."""}],
            },
            "voice": {"provider": "11labs", "voiceId": "21m00Tcm4TlvDq8ikWAM"},
            "firstMessage": f"Welcome back, {name}! This is Kyra from Kyron Medical. I remember our conversation — how can I help?" if has_history else "Thank you for calling Kyron Medical! I'm Kyra, your AI assistant. How can I help you today?",
            "transcriber": {"provider": "deepgram", "model": "nova-2"},
        }})

    return jsonify({"status": "ok"})


@app.route("/api/doctors", methods=["GET"])
def list_doctors():
    conn = get_db()
    docs = conn.execute("SELECT id, name, specialty, bio FROM doctors").fetchall()
    conn.close()
    return jsonify([dict(d) for d in docs])


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id):
    conn = get_db()
    sess = conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if not sess:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"id": sess["id"], "messages": json.loads(sess["messages"]), "context": json.loads(sess["context"])})

init_db()
seed_doctors_and_availabilities()

if __name__ == "__main__":
    app.run(debug=True, port=5000)