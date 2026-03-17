# Kyra
# AI Patient Assistant

A smart, voice-enabled patient assistant for Kyron Medical Group. Patients can chat with an AI assistant named Kyra through a modern web interface, schedule appointments with the right specialist, and seamlessly switch to a phone call without losing any conversation context.

Built as a full-stack application with a liquid glass UI, real-time AI chat, semantic doctor matching, and a voice AI handoff system.

## Live Demo

🌐 **Web App:** [https://your-domain.com](https://your-domain.com)  
📞 **AI Phone Line:** +1 (xxx) xxx-xxxx

## What It Does

**Appointment Scheduling** — Patients describe their health concern in natural language. The AI figures out which specialist they need (orthopedics for knee pain, cardiology for chest issues, etc.) and shows real available time slots. After collecting the patient's info, it books the appointment and sends a confirmation email.

**Doctor Matching** — Instead of making patients pick from a dropdown, the AI understands what they're saying and matches them to one of five specialists. Say "my knee has been hurting" and it routes you to Dr. Chen in Orthopedics. Say "I've been getting migraines" and it sends you to Dr. Nguyen in Neurology.

**Chat-to-Phone Handoff** — The standout feature. A patient can start chatting on the web, then click "Continue by phone" to receive an actual phone call from the same AI. The voice assistant picks up the conversation with full context — it knows what you already discussed, which doctor was matched, what times were offered. No repeating yourself.

**Practice Info & Prescriptions** — Patients can ask about office hours, the practice address, or check on a prescription refill status, all through the same conversational interface.

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Backend** | Python / Flask | Lightweight, fast to build, handles the API routing and business logic |
| **AI (Chat)** | Google Gemini 2.5 Flash | Powers the conversational intelligence and semantic doctor matching |
| **AI (Voice)** | Vapi.ai + OpenAI | Orchestrates the phone call pipeline — speech-to-text, LLM, text-to-speech |
| **Voice** | Deepgram Nova 2 (STT) + Vapi built-in (TTS) | Transcription and voice synthesis for natural phone conversations |
| **Database** | SQLite | Stores doctors, availability slots, patient records, appointments, and chat sessions |
| **Email** | SendGrid | Sends appointment confirmation emails |
| **Hosting** | AWS EC2 + Nginx + Let's Encrypt | Production deployment with HTTPS |

## Architecture

```
Patient (Browser)
    ↓
Liquid Glass Chat UI
    ↓
Flask API Server
    ├── Gemini AI (chat intelligence + doctor matching)
    ├── SQLite (appointments, patients, sessions)
    ├── SendGrid (email confirmations)
    └── Vapi.ai (voice handoff)
            ├── Deepgram (speech-to-text)
            ├── OpenAI (LLM for voice)
            └── Vapi TTS (text-to-speech)
```

## Doctors & Specialties

The system comes pre-loaded with five specialists, each with 45 days of availability (weekdays, 5-8 slots per day):

- **Dr. Sarah Chen** — Orthopedics (joints, bones, back, spine, fractures)
- **Dr. Raj Patel** — Cardiology (heart, blood pressure, chest, cardiac)
- **Dr. Elena Martinez** — Dermatology (skin, rash, acne, eczema, moles)
- **Dr. James Thompson** — Gastroenterology (stomach, digestive, acid reflux, IBS)
- **Dr. Lisa Nguyen** — Neurology (headaches, migraines, seizures, numbness)

## Safety

The AI is designed with healthcare safety as a priority:

- **Never provides medical advice** — it empathizes with symptoms but always directs patients to schedule with a doctor
- **Emergency detection** — if a patient mentions chest pain, difficulty breathing, or severe bleeding, the AI immediately tells them to call 911
- **No diagnoses** — the AI matches patients to specialists based on body part/concern, but never speculates about conditions
- **Data handling** — patient information is collected only for scheduling purposes

## Running Locally

git clone https://github.com/yourusername/kyron-medical.git
cd kyron-medical
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Add your API keys
cp .env.example .env
nano .env  # Add GEMINI_API_KEY at minimum

# Start the app
python app.py
# Open http://localhost:5000

The app works with just a Gemini API key for chat. Voice calling requires Vapi.ai setup, and email confirmations require SendGrid. Each service degrades gracefully — if a key is missing, that feature logs to the console instead of crashing.

## Environment Variables

GEMINI_API_KEY=         # Required — powers the chat AI
VAPI_API_KEY=           # Required for phone calls
VAPI_PHONE_NUMBER_ID=   # Required for phone calls
SENDGRID_API_KEY=       # Required for confirmation emails


## Project Structure

kyron-medical/
├── app.py              # Flask backend — routes, AI logic, database, notifications
├── templates/
│   └── index.html      # Liquid glass chat UI with animations
├── requirements.txt    # Python dependencies (5 packages)
├── .env                # API keys (not committed)
├── kyron_medical.db    # SQLite database (auto-created)
└── README.md
