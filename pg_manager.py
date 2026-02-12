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
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    def password_entered():
        if st.session_state["password"] == st.secrets["auth"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.text_input("Enter Password", type="password", on_change=password_entered, key="password")
        return False
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
    try:
        worksheet = get_worksheet(tab_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df
    except:
        return pd.DataFrame() # Return empty if tab missing

def save_rent_payment(tenant_name, month, paid_amt, balance, room):
    # 1. Update Tenant Status (Main Sheet)
    ws_tenants = get_worksheet("Tenants")
    cell = ws_tenants.find(tenant_name)
    if cell:
        # Col 6 = Last Paid Month, Col 8 = Promise Date (Clear it), Col 9 = Balance
        ws_tenants.update_cell(cell.row, 6, month) 
        ws_tenants.update_cell(cell.row, 8, "") 
        ws_tenants.update_cell(cell.row, 9, balance)
        
    # 2. Save to History (For Month-wise Record)
    ws_history = get_worksheet("Rent_History")
    today = datetime.now().strftime("%Y-%m-%d")
    ws_history.append_row([today, tenant_name, month, paid_amt, balance])

def save_loan(loan_data):
    ws = get_worksheet("Loans")
    ws.append_row([str(loan_data["Date"]), loan_data["Type"], loan_data["Person"], loan_data["Amount"], "Pending", loan_data["Note"]])

def save_expense(expense_data):
    worksheet = get_worksheet("Expenses")
    worksheet.append_row([str(expense_data["Date"]), expense_data["Category"], expense_data["Amount"], expense_data["Note"], expense_data["Type"]])

def update_promise_date(tenant_name, new_date):
    ws = get_worksheet("Tenants")
    cell = ws.find(tenant_name)
    if cell:
        ws.update_cell(cell.row, 8, str(new_date))

# --- LOAD DATA ---
try:
    df_tenants = load_data("Tenants")
    df_expenses = load_data("Expenses")
    df_loans = load_data("Loans")
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# --- SIDEBAR ---
if st.sidebar.button("🔒 Logout"):
    del st.session_state["password_correct"]
    st.rerun()

menu = st.sidebar.selectbox("Menu", ["Dashboard", "Manage Rent", "Debt Tracker (Udhaar)", "Expense Tracker", "All Records"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    # Revenue Calculation
    df_tenants['Rent Amount'] = pd.to_numeric(df_tenants['Rent Amount'], errors='coerce').fillna(0)
    total_revenue = df_tenants['Rent Amount'].sum()
    
    # Expense Calculation
    business_exp = 0
    personal_exp = 0
    if not df_expenses.empty:
        df_expenses['Amount'] = pd.to_numeric(df_expenses['Amount'], errors='coerce').fillna(0)
        if 'Type' not in df_expenses.columns: df_expenses['Type'] = "Business"
        business_exp = df_expenses[df_expenses['Type'] == 'Business']['Amount'].sum()
        personal_exp = df_expenses[df_expenses['Type'].isin(['Personal', 'Home'])]['Amount'].sum()
    
    # Loan Calculation
    to_collect = 0
    to_pay = 0
    if not df_loans.empty:
        df_loans['Amount'] = pd.to_numeric(df_loans['Amount'], errors='coerce').fillna(0)
        pending_loans = df_loans[df_loans['Status'] == 'Pending']
        to_collect = pending_loans[pending_loans['Type'] == 'Given (Lent)']['Amount'].sum()
        to_pay = pending_loans[pending_loans['Type'] == 'Taken (Borrow)']['Amount'].sum()

    st.subheader("🏢 Business Snapshot")
    c1, c2, c3 = st.columns(3)
    c1.metric("Revenue", f"₹{total_revenue:,}")
    c2.metric("Expenses", f"₹{business_exp:,}")
    c3.metric("Profit", f"₹{total_revenue - business_exp:,}")
    
    st.divider()
    
    st.subheader("📒 Debt & Personal")
    c4, c5, c6 = st.columns(3)
    c4.metric("Personal Spent", f"₹{personal_exp:,}")
    c5.metric("I need to Collect", f"₹{to_collect:,}", delta_color="normal")
    c6.metric("I need to Pay", f"₹{to_pay:,}", delta_color="inverse")

# --- 2. MANAGE RENT (UPDATED) ---
elif menu == "Manage Rent":
    st.subheader("Rent Collection")
    
    if not df_tenants.empty:
        # Get Current Month to check for ticks
        current_month_short = datetime.now().strftime("%b").lower() # e.g. "feb"
        
        # Helper: Create list with Tick Marks
        tenant_options = []
        raw_names = []
        
        # Sort by Room Number first
        if "Room Number" in df_tenants.columns:
            df_tenants = df_tenants.sort_values(by="Room Number")
            
        for index, row in df_tenants.iterrows():
            name = row["Tenant Name"]
            room = row["Room Number"]
            last_paid = str(row["Last Rent Paid (Month)"]).lower()
            
            # Tick Logic: If last paid month matches current month (or user typed full name)
            if current_month_short in last_paid:
                display_name = f"{name} (Room {room}) ✅"
            else:
                display_name = f"{name} (Room {room})"
            
            tenant_options.append(display_name)
            raw_names.append(name)
            
        # Select Tenant
        selected_display = st.selectbox("Select Tenant", tenant_options)
        
        # Find the real name from the selection
        real_name_index = tenant_options.index(selected_display)
        tenant_name = raw_names[real_name_index]
        
        # Get Data
        row = df_tenants[df_tenants["Tenant Name"] == tenant_name].iloc[0]
        rent_amt = row["Rent Amount"]
        phone = str(row["Phone"])
        
        # Check Balance (Column I might be empty initially)
        try:
            old_balance = int(row["Balance"])
        except:
            old_balance = 0
            
        st.write("---")
        c1, c2 = st.columns(2)
        c1.info(f"🏠 Rent Amount: ₹{rent_amt}")
        if old_balance > 0:
            c2.error(f"⚠️ Previous Balance: ₹{old_balance}")
        else:
            c2.success("✅ No previous balance")

        # --- PAYMENT FORM ---
        with st.form("rent_pay"):
            st.write("### 💵 Record Payment")
            col_a, col_b = st.columns(2)
            month = col_a.selectbox("For Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            
            # Auto-fill amount (Rent + Old Balance)
            total_due = rent_amt + old_balance
            paid_amount = col_b.number_input("Amount Received", value=total_due, step=500)
            
            if st.form_submit_button("Save Payment"):
                new_balance = total_due - paid_amount
                save_rent_payment(tenant_name, month, paid_amount, new_balance, row["Room Number"])
                
                if new_balance > 0:
                    st.warning(f"Saved! Tenant still owes ₹{new_balance}")
                else:
                    st.balloons()
                    st.success("Full Payment Recorded!")
                st.rerun()

        # --- WHATSAPP REMINDER ---
        st.write("---")
        st.write("### 💬 WhatsApp Options")
        
        # Option 1: Full Payment
        msg_full = f"Hi {tenant_name}, your rent of ₹{total_due} is due. Please pay soon."
        link_full = f"https://wa.me/{phone}?text={urllib.parse.quote(msg_full)}"
        
        # Option 2: Balance Reminder
        if old_balance > 0:
            msg_bal = f"Hi {tenant_name}, you have a pending balance of ₹{old_balance}. Please clear it."
            link_bal = f"https://wa.me/{phone}?text={urllib.parse.quote(msg_bal)}"
            st.markdown(f"[👉 **Remind about Balance (₹{old_balance})**]({link_bal})")
        
        st.markdown(f"[👉 **Send Rent Reminder**]({link_full})")

# --- 3. DEBT TRACKER (NEW) ---
elif menu == "Debt Tracker (Udhaar)":
    st.subheader("📒 Manage Debts & Loans")
    
    with st.form("add_loan"):
        col1, col2 = st.columns(2)
        l_type = col1.selectbox("Type", ["Given (Lent)", "Taken (Borrow)"])
        l_person = col2.text_input("Person Name")
        
        col3, col4 = st.columns(2)
        l_amount = col3.number_input("Amount", step=100)
        l_date = col4.date_input("Date")
        l_note = st.text_input("Note (Optional)")
        
        if st.form_submit_button("Save Record"):
            save_loan({"Date": l_date, "Type": l_type, "Person": l_person, "Amount": l_amount, "Note": l_note})
            st.success("Saved!")
            st.rerun()
            
    # Show Table
    if not df_loans.empty:
        st.write("---")
        st.write("### Pending List")
        pending_df = df_loans[df_loans['Status'] == 'Pending']
        st.dataframe(pending_df)
    else:
        st.info("No records found.")

# --- 4. EXPENSE TRACKER ---
elif menu == "Expense Tracker":
    st.subheader("💸 Record Expense")
    with st.form("add_expense"):
        expense_type = st.radio("Who is this expense for?", ["Business", "Home", "Personal"], horizontal=True)
        col1, col2 = st.columns(2)
        date = col1.date_input("Date")
        amount = col2.number_input("Amount", step=100)
        category = st.selectbox("Category", ["Electricity", "Food/Groceries", "Repairs", "Shopping", "Fuel", "School Fees", "Other"])
        note = st.text_input("Note")
        
        if st.form_submit_button("Save"):
            save_expense({"Date": date, "Category": category, "Amount": amount, "Note": note, "Type": expense_type})
            st.success("Saved!")
            st.rerun()

# --- 5. ALL RECORDS ---
elif menu == "All Records":
    tab1, tab2, tab3, tab4 = st.tabs(["Tenants", "Rent History (Month-wise)", "Expenses", "Loans"])
    
    with tab1:
        st.dataframe(df_tenants)
    with tab2:
        # Load History Tab
        try:
            df_hist = load_data("Rent_History")
            st.dataframe(df_hist)
        except:
            st.warning("No history yet.")
    with tab3:
        st.dataframe(df_expenses)
    with tab4:
        st.dataframe(df_loans)