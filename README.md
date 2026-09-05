# Kyra: Voice-Enabled Patient Assistant

**Status:** Completed

## Purpose

A voice-enabled patient assistant for Kyron Medical Group. Patients chat with an AI assistant named Kyra through a web interface, schedule appointments with the right specialist, and switch to a phone call without losing conversation context. Built as a full-stack application with a liquid-glass UI, real-time AI chat, semantic doctor matching, and a voice AI handoff system.

## Methods Used

* Conversational AI for scheduling and intake
* Semantic doctor matching from natural-language symptoms
* Chat-to-phone handoff with preserved context
* Graceful degradation when optional services are unconfigured

## Technologies

| Layer | Technology | Why |
|---|---|---|
| Backend | Python / Flask | API routing and business logic |
| AI (Chat) | OpenAI GPT-4o | Conversational intelligence and semantic doctor matching (via `openai` SDK) |
| AI (Voice) | Vapi.ai + OpenAI GPT-4o | Orchestrates the phone-call pipeline and places the calls |
| Speech-to-text | Deepgram Nova-2 | Call transcription |
| Text-to-speech | ElevenLabs | Voice synthesis |
| SMS | Twilio | Appointment text confirmations |
| Email | SendGrid (HTTP API) | Appointment confirmation emails |
| Database | SQLite | Doctors, availability, patients, appointments, chat + call sessions |
| Hosting | AWS EC2 + Nginx + Let's Encrypt | Production deployment with HTTPS |

## Required Libraries

```
flask==3.0.3
flask-cors==4.0.1
python-dotenv==1.0.1
requests==2.32.3
gunicorn==22.0.0
twilio==9.3.7
openai==1.51.0
```

## Project Description

### What it does

**Appointment scheduling** - Patients describe their health concern in natural language. The AI figures out which specialist they need (orthopedics for knee pain, cardiology for chest issues, etc.) and shows real available time slots. After collecting the patient's info, it books the appointment and sends a confirmation email.

**Doctor matching** - Instead of making patients pick from a dropdown, the AI interprets what they say and matches them to one of five specialists. Say "my knee has been hurting" and it routes you to Dr. Chen in Orthopedics. Say "I've been getting migraines" and it sends you to Dr. Nguyen in Neurology.

**Chat-to-phone handoff** - A patient can start chatting on the web, then click "Continue by phone" to receive an actual phone call from the same AI. The voice assistant picks up the conversation with full context: what was already discussed, which doctor was matched, and what times were offered, so the patient does not have to repeat themselves. If a call drops, the next call acknowledges the disconnection and resumes.

**Practice info & prescriptions** - Patients can ask about office hours, the practice address, or a prescription refill status through the same conversational interface.

### Architecture

```
Patient (Browser)
    ↓
Liquid Glass Chat UI
    ↓
Flask API Server
    ├── OpenAI GPT-4o (chat intelligence + doctor matching)
    ├── SQLite (appointments, patients, chat + call sessions)
    ├── SendGrid (email confirmations)
    ├── Twilio (SMS confirmations)
    └── Vapi.ai (voice handoff - places the call)
            ├── Deepgram Nova-2 (speech-to-text)
            ├── OpenAI GPT-4o (LLM for voice)
            └── ElevenLabs (text-to-speech)
```

### Doctors & specialties

The system comes pre-loaded with five specialists, each with 45 days of availability (weekdays, 5-8 slots per day):

* **Dr. Sarah Chen** - Orthopedics (joints, bones, back, spine, fractures)
* **Dr. Raj Patel** - Cardiology (heart, blood pressure, chest, cardiac)
* **Dr. Elena Martinez** - Dermatology (skin, rash, acne, eczema, moles)
* **Dr. James Thompson** - Gastroenterology (stomach, digestive, acid reflux, IBS)
* **Dr. Lisa Nguyen** - Neurology (headaches, migraines, seizures, numbness)

### Safety

The AI is designed with healthcare safety as a priority:

* **Never provides medical advice** - it empathizes with symptoms but always directs patients to schedule with a doctor.
* **Emergency detection** - if a patient mentions chest pain, difficulty breathing, or severe bleeding, the AI immediately tells them to call 911.
* **No diagnoses** - the AI matches patients to specialists based on body part or concern, but never speculates about conditions.
* **Data handling** - patient information is collected only for scheduling purposes.

## To Use

### Running locally

```bash
git clone https://github.com/priyanka-0207/Kyra.git
cd Kyra
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Add your API keys:

```bash
cp .env.example .env
nano .env          # Add OPENAI_API_KEY at minimum
```

Start the app:

```bash
python app.py
```

Open `http://localhost:5000`.

The app works with just an OpenAI API key for chat. Voice calling requires Vapi.ai setup, email confirmations require SendGrid, and SMS confirmations require Twilio. Each service degrades gracefully - if a key is missing, that feature logs to the console instead of crashing.

### Environment variables

```
OPENAI_API_KEY=          # Required - powers chat + voice LLM
OPENAI_MODEL=            # Optional - defaults to gpt-4o
FLASK_SECRET_KEY=        # Optional - session secret
VAPI_API_KEY=            # Required for phone calls
VAPI_PHONE_NUMBER_ID=    # Required for phone calls
VAPI_ASSISTANT_ID=       # Vapi assistant reference
SENDGRID_API_KEY=        # Required for confirmation emails
TWILIO_ACCOUNT_SID=      # Required for SMS confirmations
TWILIO_AUTH_TOKEN=       # Required for SMS confirmations
TWILIO_PHONE_NUMBER=     # Twilio sender number
```

## Project Structure

```
kyron-medical/
├── app.py             # Flask backend - routes, AI logic, database, notifications
├── templates/
│   └── index.html     # Liquid glass chat UI with animations
├── requirements.txt   # Python dependencies (7 packages)
├── .env               # API keys (not committed)
├── kyron_medical.db   # SQLite database (auto-created)
└── README.md
```

## Author

Priyanka Bhutada
