import streamlit as st
import pandas as pd
import gspread
import urllib.parse
from datetime import datetime

# --- CONFIGURATION ---
SHEET_NAME = "PG_Data_Master"

# --- PAGE SETUP ---
st.set_page_config(page_title="My Finance Manager", page_icon="💰")

# --- 🔒 SECURITY SYSTEM 🔒 ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# =========================================================
#  🏁 MAIN APP STARTS HERE
# =========================================================

st.title("💰 Total Finance Manager")

# --- BACKEND FUNCTIONS ---
def get_worksheet(tab_name):
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open(SHEET_NAME)
    return sh.worksheet(tab_name)

def load_data(tab_name):
    worksheet = get_worksheet(tab_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    if tab_name == "Tenants":
        if "Promised Date" not in df.columns: df["Promised Date"] = ""
    elif tab_name == "Expenses":
        if "Type" not in df.columns: df["Type"] = "Business" 
        
    return df

def save_new_tenant(tenant_data):
    worksheet = get_worksheet("Tenants")
    row = [
        tenant_data["Tenant Name"], tenant_data["Room Number"],
        tenant_data["Phone"], tenant_data["Rent Amount"],
        str(tenant_data["Move-In Date"]), tenant_data["Last Rent Paid (Month)"],
        tenant_data["Status"], "" 
    ]
    worksheet.append_row(row)

def save_expense(expense_data):
    worksheet = get_worksheet("Expenses")
    row = [
        str(expense_data["Date"]), expense_data["Category"],
        expense_data["Amount"], expense_data["Note"],
        expense_data["Type"]
    ]
    worksheet.append_row(row)

def update_rent_payment(tenant_name, month):
    worksheet = get_worksheet("Tenants")
    cell = worksheet.find(tenant_name)
    if cell:
        worksheet.update_cell(cell.row, 6, month)
        worksheet.update_cell(cell.row, 8, "") 

def update_promise_date(tenant_name, new_date):
    worksheet = get_worksheet("Tenants")
    cell = worksheet.find(tenant_name)
    if cell:
        worksheet.update_cell(cell.row, 8, str(new_date))

# --- LOAD DATA ---
try:
    df_tenants = load_data("Tenants")
    df_expenses = load_data("Expenses")
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# --- SIDEBAR ---
if st.sidebar.button("🔒 Logout"):
    del st.session_state["password_correct"]
    st.rerun()

menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add Tenant", "Manage Rent", "Expense Tracker", "All Records"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    # 1. Calculate Business Revenue
    df_tenants['Rent Amount'] = pd.to_numeric(df_tenants['Rent Amount'], errors='coerce').fillna(0)
    total_revenue = df_tenants['Rent Amount'].sum()
    
    # 2. Separate Expenses by Type
    business_expenses = 0
    personal_expenses = 0
    home_expenses = 0
    
    if not df_expenses.empty:
        df_expenses['Amount'] = pd.to_numeric(df_expenses['Amount'], errors='coerce').fillna(0)
        if 'Type' not in df_expenses.columns:
            df_expenses['Type'] = "Business"
            
        business_expenses = df_expenses[df_expenses['Type'] == 'Business']['Amount'].sum()
        personal_expenses = df_expenses[df_expenses['Type'] == 'Personal']['Amount'].sum()
        home_expenses = df_expenses[df_expenses['Type'] == 'Home']['Amount'].sum()
    
    net_profit = total_revenue - business_expenses
    
    # 3. Display Business Stats
    st.subheader("🏢 PG Business Status")
    col1, col2, col3 = st.columns(3)
    col1.metric("Revenue", f"₹{total_revenue:,}")
    col2.metric("PG Expenses", f"₹{business_expenses:,}")
    col3.metric("Net Profit", f"₹{net_profit:,}")
    
    st.divider() 
    
    # 4. Display Private Stats
    st.subheader("🏠 Private Spending")
    colA, colB = st.columns(2)
    with colA:
        st.metric("🏠 Home/Family", f"₹{home_expenses:,}")
    with colB:
        st.metric("👤 Personal", f"₹{personal_expenses:,}")

# --- 2. ADD TENANT ---
elif menu == "Add Tenant":
    st.subheader("Add New Tenant")
    with st.form("add_tenant"):
        name = st.text_input("Name")
        room = st.text_input("Room")
        phone = st.text_input("Phone (91...)")
        rent = st.number_input("Rent", step=500)
        move_in = st.date_input("Date")
        if st.form_submit_button("Save"):
            save_new_tenant({
                "Tenant Name": name, "Room Number": room, "Phone": phone,
                "Rent Amount": rent, "Move-In Date": move_in,
                "Last Rent Paid (Month)": "None", "Status": "Active"
            })
            st.success("Saved!")
            st.rerun()

# --- 3. MANAGE RENT ---
elif menu == "Manage Rent":
    st.subheader("Rent & Reminders")
    if not df_tenants.empty:
        tenant_name = st.selectbox("Select Tenant", df_tenants["Tenant Name"].tolist())
        tenant_row = df_tenants[df_tenants["Tenant Name"] == tenant_name].iloc[0]
        phone_number = str(tenant_row["Phone"])
        rent_amt = tenant_row["Rent Amount"]
        
        if "Promised Date" in tenant_row and str(tenant_row["Promised Date"]).strip() != "":
            existing_promise = str(tenant_row["Promised Date"])
        else:
            existing_promise = None
            
        st.write("---")
        if existing_promise:
            st.warning(f"Tenant Promised: {existing_promise}")
        else:
            st.success("No delays.")

        tab_pay, tab_promise = st.tabs(["💵 Mark Paid", "🤝 Record Promise"])
        with tab_pay:
            month = st.selectbox("Select Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            if st.button("Mark as PAID"):
                update_rent_payment(tenant_name, month)
                st.success(f"Updated!")
                st.rerun()
        with tab_promise:
            new_promise_date = st.date_input("Promised Date")
            if st.button("Save Promise"):
                update_promise_date(tenant_name, new_promise_date)
                st.success(f"Saved!")
                st.rerun()

        if existing_promise:
            raw_msg = f"Hi {tenant_name}, reminder: you promised to pay rent of ₹{rent_amt} by {existing_promise}."
        else:
            raw_msg = f"Hi {tenant_name}, your rent of ₹{rent_amt} is due soon."
        
        wa_link = f"https://wa.me/{phone_number}?text={urllib.parse.quote(raw_msg)}"
        st.markdown(f"## [👉 WhatsApp Reminder]({wa_link})")

# --- 4. EXPENSE TRACKER ---
elif menu == "Expense Tracker":
    st.subheader("💸 Record New Expense")
    
    with st.form("add_expense"):
        expense_type = st.radio("Who is this expense for?", ["Business", "Home", "Personal"], horizontal=True)
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input("Date")
            amount = st.number_input("Amount (₹)", step=100)
        with col2:
            category = st.selectbox("Category", ["Electricity", "Internet", "Food/Groceries", "Repairs", "Shopping", "Fuel", "School Fees", "Other"])
            note = st.text_input("Note (Optional)")
            
        if st.form_submit_button("Save Expense"):
            save_expense({
                "Date": date, "Category": category, "Amount": amount, 
                "Note": note, "Type": expense_type
            })
            st.success(f"Saved to {expense_type} Expenses!")
            st.rerun()

# --- 5. ALL RECORDS (UPDATED WITH ROOM FILTER) ---
elif menu == "All Records":
    st.subheader("📋 All Records")
    tab1, tab2 = st.tabs(["Tenants (By Room)", "Expenses"])
    
    with tab1:
        # Get list of rooms
        if not df_tenants.empty:
            unique_rooms = sorted(df_tenants["Room Number"].astype(str).unique())
            
            # Create a Filter Box
            selected_room = st.selectbox("🔍 Filter by Room Number:", ["Show All Rooms"] + unique_rooms)
            
            # Show Data based on selection
            if selected_room == "Show All Rooms":
                st.dataframe(df_tenants.sort_values(by="Room Number"))
            else:
                filtered_df = df_tenants[df_tenants["Room Number"].astype(str) == selected_room]
                st.dataframe(filtered_df)
                st.info(f"Showing {len(filtered_df)} tenant(s) in Room {selected_room}")
        else:
            st.warning("No tenants found.")

    with tab2:
        filter_type = st.selectbox("Filter Expenses by:", ["All", "Business", "Home", "Personal"])
        if not df_expenses.empty:
            if filter_type != "All":
                st.dataframe(df_expenses[df_expenses['Type'] == filter_type])
            else:
                st.dataframe(df_expenses)