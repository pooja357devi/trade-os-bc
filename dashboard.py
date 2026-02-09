from dotenv import load_dotenv
import os
from datetime import datetime
import re

load_dotenv()

import streamlit as st
import pandas as pd
from supabase import create_client
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------------------------------
# Setup
# --------------------------------------------------
st.set_page_config(page_title="Trade-OS BC", layout="wide")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def normalize_email(email):
    return email.strip().lower()


def is_valid_email(email):
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email))


# --------------------------------------------------
# Session Init
# --------------------------------------------------
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.role = None
    st.session_state.client_id = None
    st.session_state.show_register = False
    st.session_state.editing_user_id = None


# --------------------------------------------------
# Login / Register Page
# --------------------------------------------------
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize session state
if "show_register" not in st.session_state:
    st.session_state.show_register = False

# CSS to make buttons look like links
st.markdown("""
<style>
.link-button {
    background: none;
    border: none;
    color: #1f77b4;
    text-decoration: underline;
    cursor: pointer;
    padding: 0;
    font-size: 14px;
}
.link-button:hover {
    color: #0d3a8a;
}
</style>
""", unsafe_allow_html=True)

if st.session_state.user_id is None:

    col1, col2, col3 = st.columns([1, 3, 1])

    with col2:
        # Fetch clients from Supabase
        clients_data = supabase.table("clients").select("id,business_name").execute().data
        client_options = {c["business_name"]: c["id"] for c in clients_data}

        if not st.session_state.show_register:

            # ---------------- LOGIN ----------------
            st.markdown("<h3 style='text-align:center;'>Login</h3>", unsafe_allow_html=True)
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")

            if st.button("Login"):
                if not email or not password:
                    st.error("All fields required")
                else:
                    email = normalize_email(email)

                    response = supabase.table("users") \
                        .select("user_id,username,password_hash,role,client_id") \
                        .eq("email", email) \
                        .limit(1) \
                        .execute()

                    if not response.data:
                        st.error("Invalid credentials")
                    else:
                        user = response.data[0]
                        if not check_password_hash(user["password_hash"], password):
                            st.error("Invalid credentials")
                        else:
                            st.session_state.user_id = str(user["user_id"])
                            st.session_state.role = user["role"]
                            st.session_state.client_id = str(user["client_id"])
                            st.success("Login successful")
                            st.rerun()

            # Inline register link (text + button inline)
            col_text, col_link = st.columns([1, 3])
            with col_text:
                st.markdown("Don't have an account?", unsafe_allow_html=True)
            with col_link:
                if st.button("Register", key="register_link"):
                    st.session_state.show_register = True
                    st.rerun()

        else:

            # ---------------- REGISTER ----------------
            st.markdown("<h3 style='text-align:center;'>Register</h3>", unsafe_allow_html=True)
            username = st.text_input("Username")
            selected_client = st.selectbox("Company", list(client_options.keys()))
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")

            if st.button("Create Account"):
                if not all([username, selected_client, email, password, confirm]):
                    st.error("All fields required")
                elif not is_valid_email(email):
                    st.error("Invalid email")
                elif password != confirm:
                    st.error("Passwords mismatch")
                elif len(password) < 8:
                    st.error("Password must be 8+ chars")
                else:
                    email = normalize_email(email)
                    client_id = client_options[selected_client]

                    existing = supabase.table("users") \
                        .select("user_id") \
                        .eq("email", email) \
                        .eq("client_id", client_id) \
                        .execute()

                    if existing.data:
                        st.error("Email already exists")
                    else:
                        supabase.table("users").insert({
                            "username": username,
                            "client_id": client_id,
                            "email": email,
                            "password_hash": generate_password_hash(password),
                            "role": "user"
                        }).execute()

                        st.success("Account created. Please login.")
                        st.session_state.show_register = False
                        st.rerun()

            # Inline back to login link (text + button inline)
            col_text, col_link = st.columns([1, 2])
            with col_text:
                st.markdown("Already have an account?", unsafe_allow_html=True)
            with col_link:
                if st.button("Back to Login", key="back_login"):
                    st.session_state.show_register = False
                    st.rerun()

    st.stop()



# --------------------------------------------------
# Logged In Dashboard
# --------------------------------------------------
user_id = st.session_state.user_id
role = st.session_state.role
client_id = st.session_state.client_id

client = supabase.table("clients").select("*").eq("id", client_id).single().execute().data

# Logout
st.sidebar.title(client['business_name'])  # dynamic company name
if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.session_state.role = None
    st.session_state.client_id = None
    st.rerun()

# --------------------------------------------------
# Terms Compliance
# --------------------------------------------------
if not client["terms_agreed_at"]:
    st.warning("⚠️ BC Compliance Required")
    if st.button("I Agree"):
        supabase.table("clients").update({
            "terms_agreed_at": datetime.utcnow().isoformat()
        }).eq("id", client["id"]).execute()
        st.rerun()
    st.stop()  # stop execution here until user agrees

# --------------------------------------------------
# Dashboard Title
# --------------------------------------------------
st.title(f"{client['business_name']} | {client['city']}, BC")

# --------------------------------------------------
# Tabs - Main Dashboard
# --------------------------------------------------
t1, t2, t3, t4 = st.tabs(["📞 Dispatch", "🚀 Marketing", "⚙️ Admin", "🧠 Logic Editor"])

# ---------------- Dispatch ----------------
with t1:
    leads = supabase.table('leads').select("*").eq('client_id', client['id']).order('created_at', desc=True).execute().data
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

# ---------------- Marketing ----------------
with t2:
    st.subheader("Local Tools")
    c1, c2 = st.columns(2)

    # Dynamic location labels
    if c1.button(f"🌧️ Rain Check ({client['city']})"):
        st.info(f"Checking forecast for {client['city']}...")

    if client['industry_type'] == 'towing':
        if c2.button("❄️ Highway Alert"):
            st.error("Blast: 'Hwy 1 / Coquihalla Warning'.")
    elif client['industry_type'] == 'plumber':
        if c2.button("🥶 Freeze Alert"):
            st.warning("Blast: 'Pipe Freeze Warning'.")

# ---------------- Admin ----------------
with t3:
    st.subheader("Account & Users")

    # Cancel Account button for all users
    if st.button("🔴 CANCEL ACCOUNT"):
        st.error("Subscription Cancelled.")

    # Admin-only User Management
    if role == "admin":
        st.markdown("---")
        st.subheader("User Management")

        # Fetch users for this company
        users = supabase.table("users") \
            .select("user_id,username,email,role") \
            .eq("client_id", client_id) \
            .execute().data

        # Table header
        col_name, col_email, col_role, col_edit, col_delete = st.columns([3, 3, 2, 1, 1])
        col_name.markdown("**Name**")
        col_email.markdown("**Email**")
        col_role.markdown("**Role**")
        col_edit.markdown("**Edit**")
        col_delete.markdown("**Delete**")

        # Table rows
        for user in users:
            col_name, col_email, col_role, col_edit, col_delete = st.columns([3, 3, 2, 1, 1])
            col_name.write(user["username"])
            col_email.write(user["email"])
            col_role.write(user["role"])

            # ------------------ Delete Logic with Confirmation ------------------
            if user["user_id"] != user_id:
                confirm_key = f"confirm_del_{user['user_id']}"  # unique key for each user

                # Step 1: Initial Delete Button
                if col_delete.button("Delete", key=f"del_{user['user_id']}"):
                    st.session_state[confirm_key] = True

                # Step 2: Confirmation
                if st.session_state.get(confirm_key):
                    st.warning(f"Are you sure you want to delete **{user['username']}**?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Yes, Delete", key=f"yes_{user['user_id']}"):
                            supabase.table("users") \
                                .delete() \
                                .eq("user_id", user["user_id"]) \
                                .eq("client_id", client_id) \
                                .execute()
                            st.success(f"User {user['username']} deleted.")
                            st.session_state[confirm_key] = False
                            st.rerun()
                    with col_no:
                        if st.button("Cancel", key=f"no_{user['user_id']}"):
                            st.session_state[confirm_key] = False
                            st.rerun()

            # ------------------ Edit Button ------------------
            if user["user_id"] != user_id and col_edit.button("Edit", key=f"edit_{user['user_id']}"):
                st.session_state.editing_user_id = user["user_id"]

        # ------------------ Edit Form ------------------
        if st.session_state.get("editing_user_id"):
            editing_user = next((u for u in users if u["user_id"] == st.session_state.editing_user_id), None)
            if editing_user:
                st.markdown("---")
                st.subheader(f"Editing User: {editing_user['username']}")

                new_username = st.text_input("Username", value=editing_user["username"])
                new_email = st.text_input("Email", value=editing_user["email"])
                new_role = st.selectbox("Role", ["user", "admin"], index=0 if editing_user["role"]=="user" else 1)

                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("Save Changes"):
                        supabase.table("users").update({
                            "username": new_username,
                            "email": new_email,
                            "role": new_role
                        }).eq("user_id", editing_user["user_id"]).execute()

                        st.success("User updated successfully!")
                        st.session_state.editing_user_id = None
                        st.rerun()

                with col_cancel:
                    if st.button("Cancel Edit"):
                        st.session_state.editing_user_id = None
                        st.rerun()

# ---------------- Logic Editor ----------------
with t4:
    st.warning("⚠️ Brain Logic (Super Admin)")
    inds = supabase.table('industry_configs').select("*").execute().data
    choice = st.selectbox("Edit Industry", [i['industry_type'] for i in inds])

    curr = next(i for i in inds if i['industry_type'] == choice)
    new_prompt = st.text_area("System Prompt", curr['system_prompt_template'], height=300)

    if st.button("Update"):
        supabase.table('industry_configs') \
            .update({"system_prompt_template": new_prompt}) \
            .eq('industry_type', choice).execute()
        st.success("Updated.")
