from dotenv import load_dotenv
import os

load_dotenv()  # MUST be before getenv

import streamlit as st
from supabase import create_client

import streamlit as st
import pandas as pd
from supabase import create_client
import os

st.set_page_config(page_title="Trade-OS BC", layout="wide")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

st.sidebar.title("Trade-OS BC Login")
clients = supabase.table('clients').select("*").execute().data
selected = st.sidebar.selectbox("Account", [c['business_name'] for c in clients])

if selected:
    client = next(c for c in clients if c['business_name'] == selected)

    # LEGAL GATE (British Columbia)
    if not client['terms_agreed_at']:
        st.warning("⚠️ BC COMPLIANCE REQUIRED")
        st.markdown("""
        *TERMS OF SERVICE (Province of BC):*
        1. *Liability:* Cap limited to 1 month fees.
        2. *Privacy:* Data processed in Canada/USA.
        3. *Regulatory:* You must hold valid Trade Tickets (Gas/Electric) where required.
        """)
        if st.button("I AGREE"):
            supabase.table('clients').update({'terms_agreed_at': 'now()'}).eq('id', client['id']).execute()
            st.rerun()
        st.stop()

    st.title(f"{client['business_name']} | {client['city']}, BC")

    t1, t2, t3, t4 = st.tabs(["📞 Dispatch", "🚀 Marketing", "⚙️ Admin", "🧠 Logic Editor"])

    with t1:
        leads = supabase.table('leads').select("*").eq('client_id', client['id']).order('created_at',
                                                                                        desc=True).execute().data


        df = pd.DataFrame(leads)

        expected_cols = ['customer_phone', 'status', 'last_message_sid']

        # Ensure columns exist even if table is empty
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None

        st.dataframe(df[expected_cols], use_container_width=True)

        # HUMAN TAKEOVER
        if st.button("⏸️ PAUSE AI (1 Hour)"):
            st.success("AI Paused. You can text manually now.")

    with t2:
        st.subheader("Local Tools")
        c1, c2 = st.columns(2)
        # Dynamic location labels
        if c1.button(f"🌧️ Rain Check ({client['city']})"):
            st.info(f"Checking forecast for {client['city']}...")

        if client['industry_type'] == 'towing':
            if c2.button("❄️ Highway Alert"): st.error("Blast: 'Hwy 1 / Coquihalla Warning'.")
        elif client['industry_type'] == 'plumber':
            if c2.button("🥶 Freeze Alert"): st.warning("Blast: 'Pipe Freeze Warning'.")

    with t3:
        if st.button("🔴 CANCEL ACCOUNT"):
            st.error("Subscription Cancelled.")

    with t4:
        st.warning("⚠️ Brain Logic (Super Admin)")
        inds = supabase.table('industry_configs').select("*").execute().data
        choice = st.selectbox("Edit Industry", [i['industry_type'] for i in inds])

        curr = next(i for i in inds if i['industry_type'] == choice)
        new_prompt = st.text_area("System Prompt", curr['system_prompt_template'], height=300)

        if st.button("Update"):
            supabase.table('industry_configs').update({"system_prompt_template": new_prompt}).eq('industry_type',
                                                                                                 choice).execute()
            st.success("Updated.")