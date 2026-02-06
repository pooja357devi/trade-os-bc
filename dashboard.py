from dotenv import load_dotenv
import os

load_dotenv()  # MUST be before getenv

import streamlit as st
import pandas as pd
from supabase import create_client
from werkzeug.security import generate_password_hash, check_password_hash
import re

st.set_page_config(page_title="Trade-OS BC", layout="wide")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Helpers
def normalize_email(email):
    return email.strip().lower()

def is_valid_email(email):
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email))

# Check if user is logged in
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
    st.session_state.role = None
    st.session_state.client_id = None
    st.session_state.show_register = False
    st.session_state.editing_user_id = None

# Handle query params for actions
if 'action' in st.query_params:
    action = st.query_params['action']
    if action == 'register':
        st.session_state.show_register = True
    elif action == 'login':
        st.session_state.show_register = False
    st.query_params.clear()
    st.rerun()

# Login/Register Page
if st.session_state.user_id is None:
    # Add CSS for centering and max-width
    st.markdown("""
    <style>
    .login-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>Trade-OS BC Login</h1>", unsafe_allow_html=True)
    
    # Center the forms
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        if not st.session_state.show_register:
            # Login Form
            st.subheader("Login")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login"):
                if not email or not password:
                    st.error("All fields are required")
                else:
                    email = normalize_email(email)
                    response = supabase.table("users").select("*").eq("email", email).limit(1).execute()

                    if not response.data:
                        st.error("Invalid email or password")
                    else:
                        user = response.data[0]
                        if not check_password_hash(user["password"], password):
                            st.error("Invalid email or password")
                        else:
                            st.session_state.user_id = str(user["user_id"])
                            st.session_state.role = user["role"]
                            st.session_state.client_id = str(user["client_id"])
                            st.success("Login successful!")
                            st.rerun()

            st.markdown('<p>Don\'t have an account? <a href="?action=register" style="color:blue;text-decoration:underline;">Register here</a></p>', unsafe_allow_html=True)
        
        else:
            # Register Form
            st.subheader("Register")
            username = st.text_input("Username", key="reg_username")
            clients_data = supabase.table('clients').select("*").execute().data
            client_options = {c['business_name']: c['id'] for c in clients_data}
            selected_client = st.selectbox("Company", list(client_options.keys()), key="reg_client")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")

            if st.button("Register"):
                if not all([username, selected_client, email, password, confirm]):
                    st.error("All fields are required")
                elif not is_valid_email(email):
                    st.error("Invalid email format")
                elif password != confirm:
                    st.error("Passwords do not match")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters")
                else:
                    email = normalize_email(email)
                    existing = supabase.table("users").select("user_id").eq("email", email).limit(1).execute()

                    if existing.data:
                        st.error("Email already registered")
                    else:
                        client_id = client_options[selected_client]
                        supabase.table("users").insert({
                            "username": username,
                            "client_id": client_id,
                            "email": email,
                            "password": generate_password_hash(password),
                            "role": "user"
                        }).execute()
                        st.success("Registration successful. Please login.")
                        st.session_state.show_register = False
                        st.rerun()

            st.markdown('<p>Already have an account? <a href="?action=login" style="color:blue;text-decoration:underline;">Login here</a></p>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    
    st.stop()

# Logged in user
user_id = st.session_state.user_id
role = st.session_state.role
client_id = st.session_state.client_id

# Get client info
client = supabase.table('clients').select("*").eq('id', client_id).single().execute().data

st.sidebar.title("Trade-OS BC")
if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.session_state.role = None
    st.session_state.client_id = None
    st.session_state.editing_user_id = None
    st.rerun()

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

    st.dataframe(df[expected_cols], width='stretch')

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
    
    if role == 'admin':
        st.subheader("Admin Panel - User Management")
        
        users = supabase.table('users').select("user_id, username, email, role").eq('client_id', client_id).execute().data
        
        if users:
            st.write("### Users")
            # Header
            col1, col2, col3, col4, col5 = st.columns([3,3,2,1,1])
            col1.write("**Username**")
            col2.write("**Email**")
            col3.write("**Role**")
            col4.write("**Edit**")
            col5.write("**Delete**")
            
            for user in users:
                col1, col2, col3, col4, col5 = st.columns([3,3,2,1,1])
                col1.write(user['username'])
                col2.write(user['email'])
                col3.write(user['role'])
                
                with col4:
                    if st.button("Edit", key=f"edit_{user['user_id']}"):
                        st.session_state.editing_user_id = user['user_id']
                
                with col5:
                    if user['user_id'] != user_id:  # Prevent self-delete
                        if st.button("Delete", key=f"del_{user['user_id']}", type="secondary"):
                            supabase.table('users').delete().eq('user_id', user['user_id']).execute()
                            st.success(f"Deleted user {user['username']}")
                            st.rerun()
                    else:
                        st.write("N/A")
            
            # Edit forms below
            editing_user_id = st.session_state.get('editing_user_id')
            if editing_user_id:
                # Find the user being edited
                user_to_edit = next((u for u in users if u['user_id'] == editing_user_id), None)
                if user_to_edit:
                    st.write(f"### Edit {user_to_edit['username']}")
                    new_username = st.text_input("Username", value=user_to_edit['username'], key=f"uname_{editing_user_id}")
                    new_email = st.text_input("Email", value=user_to_edit['email'], key=f"email_{editing_user_id}")
                    new_role = st.selectbox("Role", ["user", "admin"], index=0 if user_to_edit['role'] == "user" else 1, key=f"role_{editing_user_id}")
                    
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("Save", key=f"save_{editing_user_id}"):
                            supabase.table('users').update({
                                'username': new_username,
                                'email': new_email,
                                'role': new_role
                            }).eq('user_id', editing_user_id).execute()
                            st.success("User updated")
                            st.session_state.editing_user_id = None
                            st.rerun()
                    with col_cancel:
                        if st.button("Cancel", key=f"cancel_{editing_user_id}"):
                            st.session_state.editing_user_id = None
                            st.rerun()
        else:
            st.write("No users found.")

with t4:
    if role == 'admin':
        st.warning("⚠️ Brain Logic (Super Admin)")
        inds = supabase.table('industry_configs').select("*").execute().data
        choice = st.selectbox("Edit Industry", [i['industry_type'] for i in inds])

        curr = next(i for i in inds if i['industry_type'] == choice)
        new_prompt = st.text_area("System Prompt", curr['system_prompt_template'], height=300)

        if st.button("Update"):
            supabase.table('industry_configs').update({"system_prompt_template": new_prompt}).eq('industry_type',
                                                                                                 choice).execute()
            st.success("Updated.")
    else:
        st.warning("Admin access required")