from dotenv import load_dotenv
import os

load_dotenv()  # <-- MUST be before getenv

import os
import re
import time
import requests
import stripe
import pytz
import openai
from datetime import datetime
from fastapi import FastAPI, Form
from twilio.rest import Client as TwilioClient
from supabase import create_client

app = FastAPI()

# --- CONFIG ---
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
twilio_client = TwilioClient(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN"))
openai.api_key = os.getenv("OPENAI_KEY")
stripe.api_key = os.getenv("STRIPE_KEY")


# --- UTILS ---
def get_industry_config(industry_type):
    data = supabase.table('industry_configs').select("*").eq('industry_type', industry_type).execute().data
    if data: return data[0]
    return {
        "system_prompt_template": "You are a helpful assistant.",
        "safety_keywords": [], "safety_response": "", "vision_instruction": "Describe image."
    }


def redact_pci(text):
    return re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[REDACTED_PCI]', text)


def save_evidence(media_url, client_id, phone):
    try:
        r = requests.get(media_url)
        filename = f"{phone}_{int(time.time())}.jpg"
        supabase.storage.from_("evidence").upload(filename, r.content, {"content-type": "image/jpeg"})
        return supabase.storage.from_("evidence").get_public_url(filename)
    except:
        return media_url


# --- SMS HANDLER ---
@app.post("/webhook/sms")
async def sms_handler(Body: str = Form(""), From: str = Form(...), To: str = Form(...), MessageSid: str = Form(...),
                      NumMedia: int = Form(0), MediaUrl0: str = Form(None)):
    # 1. GLOBAL BLOCKS (Bill 96 + SHAFT)
    qc_codes = ['514', '438', '450', '579', '418', '581', '819', '873']
    if any(From.replace('+91', '').startswith(c) for c in qc_codes): return "Blocked: Quebec"

    forbidden = ["cbd", "vape", "loan", "gun"]
    if any(w in Body.lower() for w in forbidden): return "Blocked: SHAFT"

    # 2. BLACKLIST & WRONG NUMBER
    if "wrong number" in Body.lower(): return "Blocked: Wrong Number"

    # 3. CLIENT LOOKUP & HUMAN TAKEOVER
    client = supabase.table('clients').select("*").eq('phone_number', To).execute().data[0]
    lead = supabase.table('leads').select("*").eq('customer_phone', From).execute().data

    if lead and lead[0]['ai_paused_until']:
        if datetime.fromisoformat(lead[0]['ai_paused_until']) > datetime.now(pytz.utc):
            return "Paused: Human Intervention"

    # 4. SILENCE CHECK
    if Body.strip().lower() in ['thanks', 'ok', 'got it', 'bye']: return "Silent"

    # 5. INDUSTRY & SAFETY LOGIC
    config = get_industry_config(client['industry_type'])

    if any(k in Body.lower() for k in config['safety_keywords']):
        twilio_client.messages.create(body=config['safety_response'], from_=To, to=From)
        supabase.table('compliance_logs').insert({"violation_type": "Safety Stop", "content": Body}).execute()
        return "Safety Stop"

    # 6. CONTEXT BUILDER (BC Wide)
    safe_body = redact_pci(Body[:500])
    # Most of BC is America/Vancouver, but code supports client specific timezone if needed
    bc_tz = pytz.timezone(client['timezone'])
    now_bc = datetime.now(bc_tz)
    is_after_hours = now_bc.hour > 18 or now_bc.weekday() >= 5

    system_instruction = config['system_prompt_template']
    system_instruction += f"\nCONTEXT: Client is in {client['city']}, BC. Time: {now_bc.strftime('%I:%M %p')}. "

    if is_after_hours: system_instruction += "PRICING: Mention 'After-Hours Rates' apply. "

    system_instruction += """
    LEGAL RULES (BC LAWS):
    1. LIEN ACT: Say "Visit Concluded", never "Job Complete".
    2. NEGLIGENCE: Say "Request Sent", never "Help is on the way".
    3. INSURANCE: Say "Technician", never "Employee".
    4. PAYMENT: If Invoice > $10k, mention "10% Statutory Holdback".
    """

    # 7. AI EXECUTION
    if NumMedia > 0:
        perm_url = save_evidence(MediaUrl0, client['id'], From)
        messages = [{"role": "user", "content": [{"type": "text", "text": "Analyze."},
                                                 {"type": "image_url", "image_url": {"url": perm_url}}]}]
    else:
        messages = [{"role": "user", "content": safe_body}]

    messages.insert(0, {"role": "system", "content": system_instruction})

    response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages, max_tokens=300, temperature=0.3)
    reply = response.choices[0].message.content

    # 8. SEND & LOG
    twilio_client.messages.create(body=reply, from_=To, to=From)

    tokens = response.usage.total_tokens
    supabase.table('usage_logs').insert(
        {"client_id": client['id'], "tokens": tokens, "cost_est": (tokens / 1000) * 0.002}).execute()

    if lead:
        old_hist = lead[0]['conversation_history']
        new_hist = f"{old_hist} | User: {safe_body} | AI: {reply}"[-5000:]
        supabase.table('leads').update({"conversation_history": new_hist, "last_message_sid": MessageSid}).eq(
            'customer_phone', From).execute()

    return "OK"


@app.get("/health")
def health(): return {"status": "alive"}
