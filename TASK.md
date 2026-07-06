# Multi-Doctor Voice Appointment Scheduling Agent — Task File

## Project Overview

An intelligent hospital voice receptionist agent that manages doctor appointments through natural conversations. The agent handles booking, rescheduling, and cancellation while ensuring no duplicate bookings, scheduling conflicts, or repeated questions.

---

## Agent Behavior Steps

### Step 1: Understand User Intent

Identify the user's intent from the conversation.

**Possible intents include:**
- Book appointment
- Cancel appointment
- Reschedule appointment
- Check doctor availability
- Ask about doctor specialization
- General hospital inquiry

If the intent is unclear, ask a clarification question.

**Example:**

> User: "I need to see a doctor."
>
> Response: "Sure. Could you tell me what type of doctor you are looking for or what symptoms you are experiencing?"

---

### Step 2: Identify the Patient

Check whether the patient already exists in the database.

**Search using:**
1. Phone number
2. Patient ID
3. Email address

**If the patient exists:**
- Load previous information.
- Do not ask for details that are already known.
- Example: *"Welcome back, Kuldeep. I found your profile."*

**If the patient does not exist:**

Collect:
- Full name
- Phone number
- Email address (optional)

Create a new patient record.

---

### Step 3: Determine the Required Doctor

**If the patient provides a doctor's name:**
- Example: "I want to see Dr. Sharma."
- Retrieve the doctor profile.

**If the patient only provides symptoms:**

Map symptoms to the appropriate specialization:

| Symptom         | Specialization     |
|-----------------|--------------------|
| Chest pain      | Cardiologist       |
| Skin rash       | Dermatologist      |
| Eye problem     | Ophthalmologist    |
| Ear pain        | ENT Specialist     |

Retrieve all doctors matching the specialization.

---

### Step 4: Retrieve Doctor Availability

For the selected doctor, check:
- Working days
- Working hours
- Leave schedule
- Existing appointments

Generate only valid available slots. **Never suggest unavailable times.**

---

### Step 5: Suggest Available Slots

Provide up to **three available appointment slots**.

**Example:**

> "Dr. Sharma is available tomorrow at:
> - 10:00 AM
> - 11:30 AM
> - 3:00 PM
>
> Which time would you prefer?"

---

### Step 6: Validate the Selected Slot

Before booking, verify:

#### Doctor Conflict Check
- Ensure the doctor is not already booked during that time.

#### Patient Conflict Check
- Ensure the patient does not already have another appointment at that time.

#### Duplicate Appointment Check
- Ensure the patient does not already have an appointment with the same doctor for the same time.

**If a conflict exists**, politely explain and suggest alternatives.

> "You already have an appointment with Dr. Sharma at that time. Would you like to keep it or select another slot?"

---

### Step 7: Confirm Appointment Details

Before creating the booking, summarize:
- Patient name
- Doctor name
- Specialization
- Date
- Time

**Example:**

> "Please confirm:
>
> **Patient:** Kuldeep Mishra
> **Doctor:** Dr. Sharma
> **Specialization:** Cardiology
> **Date:** 10 July 2026
> **Time:** 11:00 AM"

Wait for **explicit confirmation**.

---

### Step 8: Create Appointment

After confirmation:
- Create appointment record.
- Update doctor's calendar.
- Mark slot as unavailable.

Generate:
- Appointment ID
- Booking timestamp

---

### Step 9: Send Confirmation

Provide confirmation to the patient.

**Example:**

> "Your appointment has been successfully booked.
>
> **Appointment ID:** APT-10234
> **Doctor:** Dr. Sharma
> **Date:** 10 July 2026
> **Time:** 11:00 AM"

**Optional:**
- Send SMS confirmation.
- Send email confirmation.
- Create Google Calendar event.

---

### Step 10: Maintain Conversation Memory

Remember information already collected during the conversation.

**Never ask again for:**
- Doctor name
- Preferred date
- Patient name
- Phone number

...unless the user explicitly changes it.

**Example:**

> User: "Actually make it Wednesday."
>
> ✅ **Correct:** Update only the appointment date.
>
> ❌ **Incorrect:** "Which doctor would you like to book with?"

---

### Step 11: Handle Modifications

Support the following operations:

#### Cancel Appointment
- Retrieve appointment and cancel it.

#### Reschedule Appointment
- Find a new slot and update the booking.

#### Change Doctor
- Restart doctor selection while preserving patient details.

---

### Step 12: Follow Conversation Rules

- ✅ Be polite and professional.
- ✅ Ask only one question at a time.
- ✅ Never ask for information already collected.
- ✅ Never create duplicate appointments.
- ✅ Never schedule overlapping appointments.
- ✅ Always verify availability before confirming.
- ✅ Keep responses short and voice-friendly.
- ✅ Maintain context throughout the conversation.

---

## Primary Objective

> Behave exactly like an experienced hospital receptionist while operating with **perfect scheduling accuracy**.

---

## Tech Stack

### 1. Voice Layer

| Component | Tool |
|-----------|------|
| Speech-to-Text (STT) | Whisper API (OpenAI) |
| Text-to-Speech (TTS) | ElevenLabs |
| Real-time Voice Orchestration | Vapi AI |

---

### 2. Agent Layer

| Component | Tool |
|-----------|------|
| Multi-agent workflow orchestration | LangGraph |
| Tool calling and agent framework | LangChain |

---

### 3. Large Language Model

- **LLM Provider:** Groq

---

### 4. Calendar Integration

- **Service:** Google Calendar API

**Responsibilities:**
- Check doctor availability
- Prevent duplicate appointments
- Prevent overlapping bookings
- Create calendar events
- Update appointments
- Cancel appointments

---

### 5. Database

- **Database:** PostgreSQL
- **ORM:** SQLAlchemy

---

### 6. Backend

| Component | Tool |
|-----------|------|
| API Server | FastAPI |
| Authentication | JWT Authentication |
| ORM | SQLAlchemy |

---

### 7. Frontend Dashboard (Optional)

| Component | Tool |
|-----------|------|
| Admin Dashboard | HTML, CSS, Vanilla JS |
| UI Components | HTML, CSS, Vanilla JS |

**Dashboard Features:**
- Doctor management
- Appointment management
- Calendar view
- Analytics dashboard
- Doctor availability management

---

### 8. Notification Services

| Channel | Service |
|---------|---------|
| Email Notifications | SMTP or Resend |
| SMS Notifications | Twilio |
| WhatsApp Notifications | Twilio WhatsApp API |

---

### 9. Monitoring and Logging

| Component | Tool |
|-----------|------|
| Logging | Python Logging |
| Monitoring | Grafana |
| Error Tracking | Sentry |

---

## Final Architecture

```
User Voice
  → Whisper STT
  → Vapi Voice Pipeline
  → LangGraph Agent
  → Tool Calling
  → Google Calendar API
  → PostgreSQL Database
  → ElevenLabs TTS
  → Voice Response
```
