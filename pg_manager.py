import streamlit as st
import pandas as pd
import gspread
import urllib.parse
from datetime import datetime

# --- CONFIGURATION ---
SHEET_NAME = "PG_Data_Master"

# --- PAGE SETUP (Browser Tab Name) ---
# CHANGE "PG Manager Pro" below to your app name
st.set_page_config(page_title="Nandal Boys PG", page_icon="🔒")

# --- 🔒 SECURITY SYSTEM 🔒 ---
def check_password():
    """Returns True if the user had entered the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't keep password in memory
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input again
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()  # STOP here if password is wrong. Don't load anything else!

# =========================================================
#  🏁 MAIN APP STARTS HERE (Only loads if password is okay)
# =========================================================

# CHANGE "My PG Dashboard" below to your Main Title
st.title("🤝 Nandal Boys PG")

# --- BACKEND FUNCTIONS ---
def get_worksheet(tab_name):
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open(SHEET_NAME)
    return sh.worksheet(tab_name)

def load_data(tab_name):
    worksheet = get_worksheet(tab_name)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    if "Promised Date" not in df.columns and tab_name == "Tenants":
        df["Promised Date"] = ""
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
        expense_data["Amount"], expense_data["Note"]
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

# --- SIDEBAR & MENU ---
if st.sidebar.button("🔒 Logout"):
    del st.session_state["password_correct"]
    st.rerun()

menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add Tenant", "Manage Rent", "Expense Tracker", "All Records"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.subheader("💰 Financial Health")
    df_tenants['Rent Amount'] = pd.to_numeric(df_tenants['Rent Amount'], errors='coerce').fillna(0)
    total_revenue = df_tenants['Rent Amount'].sum()
    
    if not df_expenses.empty:
        df_expenses['Amount'] = pd.to_numeric(df_expenses['Amount'], errors='coerce').fillna(0)
        total_expenses = df_expenses['Amount'].sum()
    else:
        total_expenses = 0
        
    net_profit = total_revenue - total_expenses
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Revenue", f"₹{total_revenue:,}")
    col2.metric("Expenses", f"₹{total_expenses:,}")
    col3.metric("Profit", f"₹{net_profit:,}")

# --- 2. ADD TENANT ---
elif menu == "Add Tenant":
    st.subheader("Add New Tenant")
    with st.form("add_tenant"):
        name = st.text_input("Name")
        room = st.text_input("Room")
        phone = st.text_input("Phone (Format: 919876543210)")
        st.caption("⚠️ Add 91, no + symbol.")
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
    st.subheader("Record Promises & Send Reminders")
    
    if not df_tenants.empty:
        tenant_name = st.selectbox("Select Tenant", df_tenants["Tenant Name"].tolist())
        tenant_row = df_tenants[df_tenants["Tenant Name"] == tenant_name].iloc[0]
        phone_number = str(tenant_row["Phone"])
        rent_amt = tenant_row["Rent Amount"]
        move_in_str = str(tenant_row["Move-In Date"])
        
        if "Promised Date" in tenant_row and str(tenant_row["Promised Date"]).strip() != "":
            existing_promise = str(tenant_row["Promised Date"])
        else:
            existing_promise = None

        try:
            move_in_date = datetime.strptime(move_in_str, "%Y-%m-%d")
            due_day = move_in_date.day
            current_month_name = datetime.now().strftime("%B")
            due_date_text = f"{due_day}th {current_month_name}"
        except:
            due_date_text = "5th of this month" 

        st.write("---")
        col_info1, col_info2 = st.columns(2)
        col_info1.info(f"📅 **Due Date:** {due_date_text}")
        if existing_promise:
            col_info2.warning(f"🤝 **Promised:** {existing_promise}")
        else:
            col_info2.success("✅ No delay.")

        tab_pay, tab_promise = st.tabs(["💵 Mark Paid", "🤝 Record Promise"])
        
        with tab_pay:
            month = st.selectbox("Select Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            if st.button("Mark as PAID"):
                update_rent_payment(tenant_name, month)
                st.balloons()
                st.success(f"Updated!")
                st.rerun()

        with tab_promise:
            new_promise_date = st.date_input("Tenant Promised Date")
            if st.button("Save Promise"):
                update_promise_date(tenant_name, new_promise_date)
                st.success(f"Saved!")
                st.rerun()

        st.write("---")
        st.subheader("💬 Send Smart Reminder")
        
        if existing_promise:
            raw_msg = f"Hi {tenant_name}, this is a reminder that you promised to pay your rent of ₹{rent_amt} by {existing_promise}. Please clear it today. Thanks!"
        else:
            raw_msg = f"Hi {tenant_name}, your rent of ₹{rent_amt} is due on {due_date_text}. Please pay on time. Thanks!"

        encoded_msg = urllib.parse.quote(raw_msg)
        wa_link = f"https://wa.me/{phone_number}?text={encoded_msg}"
        st.markdown(f"## [👉 Click to Send WhatsApp]({wa_link})")

# --- 4. EXPENSE TRACKER ---
elif menu == "Expense Tracker":
    st.subheader("💸 Record Expense")
    with st.form("add_expense"):
        date = st.date_input("Date")
        category = st.selectbox("Category", ["Electricity", "Internet", "Cleaning", "Repairs", "Other"])
        amount = st.number_input("Amount", step=100)
        note = st.text_input("Note")
        if st.form_submit_button("Save"):
            save_expense({"Date": date, "Category": category, "Amount": amount, "Note": note})
            st.success("Saved!")
            st.rerun()

# --- 5. ALL RECORDS ---
elif menu == "All Records":
    st.dataframe(df_tenants)
    st.dataframe(df_expenses)