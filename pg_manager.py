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
        return pd.DataFrame() 

def save_new_tenant(tenant_data):
    worksheet = get_worksheet("Tenants")
    row = [
        tenant_data["Tenant Name"], tenant_data["Room Number"],
        tenant_data["Phone"], tenant_data["Rent Amount"],
        str(tenant_data["Move-In Date"]), tenant_data["Last Rent Paid (Month)"],
        tenant_data["Status"], "", "" 
    ]
    worksheet.append_row(row)

def save_rent_payment(tenant_name, month, paid_amt, balance, room):
    paid_amt = int(paid_amt)
    balance = int(balance)
    
    ws_tenants = get_worksheet("Tenants")
    cell = ws_tenants.find(tenant_name)
    if cell:
        ws_tenants.update_cell(cell.row, 6, month) 
        ws_tenants.update_cell(cell.row, 8, "") 
        ws_tenants.update_cell(cell.row, 9, balance)
        
    ws_history = get_worksheet("Rent_History")
    today = datetime.now().strftime("%Y-%m-%d")
    ws_history.append_row([today, tenant_name, month, paid_amt, balance])

def save_loan(loan_data):
    ws = get_worksheet("Loans")
    amount = int(loan_data["Amount"])
    ws.append_row([str(loan_data["Date"]), loan_data["Type"], loan_data["Person"], amount, "Pending", loan_data["Note"]])

def update_loan_balance(person_name, original_amount, repay_amount, l_type, old_note):
    ws = get_worksheet("Loans")
    records = ws.get_all_records()
    
    original_amount = int(original_amount)
    repay_amount = int(repay_amount)
    new_balance = original_amount - repay_amount
    
    for i, r in enumerate(records):
        # HELPER: Check both "Person" and "Person Name" to match sheet
        sheet_person = str(r.get("Person") or r.get("Person Name"))
        
        if sheet_person == person_name and str(r["Amount"]) == str(original_amount) and r["Type"] == l_type and r["Status"] == "Pending":
            
            row_num = i + 2
            today_str = datetime.now().strftime("%d-%b")
            
            if new_balance <= 0:
                ws.update_cell(row_num, 5, "Cleared") 
                ws.update_cell(row_num, 4, 0)
            else:
                ws.update_cell(row_num, 4, new_balance)
                new_note = f"{old_note} | Paid {repay_amount} on {today_str}"
                ws.update_cell(row_num, 6, new_note)
            return

def save_expense(expense_data):
    worksheet = get_worksheet("Expenses")
    amount = int(expense_data["Amount"])
    worksheet.append_row([str(expense_data["Date"]), expense_data["Category"], amount, expense_data["Note"], expense_data["Type"]])

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

menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add Tenant", "Manage Rent", "Debt Tracker (Udhaar)", "Expense Tracker", "All Records"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    # 1. Revenue
    if not df_tenants.empty and 'Rent Amount' in df_tenants.columns:
        df_tenants['Rent Amount'] = pd.to_numeric(df_tenants['Rent Amount'], errors='coerce').fillna(0)
        total_revenue = df_tenants['Rent Amount'].sum()
    else:
        total_revenue = 0
    
    # 2. Expenses
    business_exp = 0
    personal_exp = 0
    if not df_expenses.empty:
        df_expenses['Amount'] = pd.to_numeric(df_expenses['Amount'], errors='coerce').fillna(0)
        if 'Type' not in df_expenses.columns: df_expenses['Type'] = "Business"
        business_exp = df_expenses[df_expenses['Type'] == 'Business']['Amount'].sum()
        personal_exp = df_expenses[df_expenses['Type'].isin(['Personal', 'Home'])]['Amount'].sum()
    
    # 3. Loans
    to_collect = 0
    to_pay = 0
    if not df_loans.empty:
        df_loans['Amount'] = pd.to_numeric(df_loans['Amount'], errors='coerce').fillna(0)
        pending_loans = df_loans[df_loans['Status'] == 'Pending']
        to_collect = pending_loans[pending_loans['Type'] == 'Given (Lent)']['Amount'].sum()
        to_pay = pending_loans[pending_loans['Type'] == 'Taken (Borrow)']['Amount'].sum()

    st.subheader("🏢 Business Snapshot")
    c1, c2, c3 = st.columns(3)
    c1.metric("Revenue", f"₹{int(total_revenue):,}")
    c2.metric("Expenses", f"₹{int(business_exp):,}")
    c3.metric("Profit", f"₹{int(total_revenue - business_exp):,}")
    
    st.divider()
    
    st.subheader("📒 Debt & Personal")
    c4, c5, c6 = st.columns(3)
    c4.metric("Personal Spent", f"₹{int(personal_exp):,}")
    c5.metric("I need to Collect", f"₹{int(to_collect):,}", delta_color="normal")
    c6.metric("I need to Pay", f"₹{int(to_pay):,}", delta_color="inverse")

# --- 2. ADD TENANT ---
elif menu == "Add Tenant":
    st.subheader("Add New Tenant")
    with st.form("add_tenant"):
        name = st.text_input("Name")
        room = st.text_input("Room Number")
        phone = st.text_input("Phone (Start with 91...)")
        rent = st.number_input("Rent Amount", step=500)
        move_in = st.date_input("Move-In Date")
        
        if st.form_submit_button("Save New Tenant"):
            save_new_tenant({
                "Tenant Name": name, "Room Number": room, "Phone": phone,
                "Rent Amount": rent, "Move-In Date": move_in,
                "Last Rent Paid (Month)": "None", "Status": "Active"
            })
            st.success("Tenant Added Successfully!")
            st.balloons()
            st.rerun()

# --- 3. MANAGE RENT ---
elif menu == "Manage Rent":
    st.subheader("Rent Collection")
    
    if not df_tenants.empty:
        current_month_short = datetime.now().strftime("%b").lower() 
        tenant_options = []
        raw_names = []
        
        if "Room Number" in df_tenants.columns:
            df_tenants = df_tenants.sort_values(by="Room Number")
            
        for index, row in df_tenants.iterrows():
            name = row["Tenant Name"]
            room = row["Room Number"]
            last_paid = str(row["Last Rent Paid (Month)"]).lower()
            if current_month_short in last_paid:
                display_name = f"{name} (Room {room}) ✅"
            else:
                display_name = f"{name} (Room {room})"
            tenant_options.append(display_name)
            raw_names.append(name)
            
        selected_display = st.selectbox("Select Tenant", tenant_options)
        real_name_index = tenant_options.index(selected_display)
        tenant_name = raw_names[real_name_index]
        
        row = df_tenants[df_tenants["Tenant Name"] == tenant_name].iloc[0]
        rent_amt = int(row["Rent Amount"])
        phone = str(row["Phone"])
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

        with st.form("rent_pay"):
            st.write("### 💵 Record Payment")
            col_a, col_b = st.columns(2)
            month = col_a.selectbox("For Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            total_due = rent_amt + old_balance
            paid_amount = col_b.number_input("Amount Received", value=total_due, step=500)
            
            if st.form_submit_button("Save Payment"):
                new_balance = total_due - paid_amount
                save_rent_payment(tenant_name, month, int(paid_amount), int(new_balance), row["Room Number"])
                st.balloons()
                st.success("Full Payment Recorded!")
                st.rerun()

        st.write("---")
        st.write("### 💬 WhatsApp Options")
        msg_full = f"Hi {tenant_name}, your rent of ₹{total_due} is due. Please pay soon."
        link_full = f"https://wa.me/{phone}?text={urllib.parse.quote(msg_full)}"
        if old_balance > 0:
            msg_bal = f"Hi {tenant_name}, you have a pending balance of ₹{old_balance}. Please clear it."
            link_bal = f"https://wa.me/{phone}?text={urllib.parse.quote(msg_bal)}"
            st.markdown(f"[👉 **Remind about Balance (₹{old_balance})**]({link_bal})")
        st.markdown(f"[👉 **Send Rent Reminder**]({link_full})")

# --- 4. DEBT TRACKER (ROBUST FIX) ---
elif menu == "Debt Tracker (Udhaar)":
    st.subheader("📒 Manage Debts & Loans")
    
    with st.expander("➕ Add New Loan Record", expanded=False):
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
            
    st.write("---")
    st.write("### ⏳ Active Loans")
    
    if not df_loans.empty:
        # --- ROBUST FIX: Auto-rename 'Person Name' to 'Person' ---
        if "Person Name" in df_loans.columns:
            df_loans = df_loans.rename(columns={"Person Name": "Person"})
        # ---------------------------------------------------------
        
        pending_df = df_loans[df_loans['Status'] == 'Pending']
        
        if not pending_df.empty:
            for index, row in pending_df.iterrows():
                # Safe Access using .get() to prevent crashes
                p_name = row.get("Person") or row.get("Person Name") or "Unknown"
                p_amt = row.get("Amount", 0)
                p_type = row.get("Type", "Loan")
                p_date = row.get("Date", "")
                p_note = row.get("Note", "")

                with st.expander(f"**{p_name}** |  {p_type}  |  ₹{p_amt}"):
                    st.caption(f"Date: {p_date} | Note: {p_note}")
                    
                    col_pay1, col_pay2 = st.columns([2, 1])
                    pay_amt = col_pay1.number_input("Amount Paid Now", min_value=0, max_value=int(p_amt), key=f"pay_{index}")
                    
                    if col_pay2.button("Update Record", key=f"btn_{index}"):
                        if pay_amt > 0:
                            update_loan_balance(p_name, p_amt, pay_amt, p_type, p_note)
                            st.success("Updated!")
                            st.rerun()
                        else:
                            st.warning("Enter amount > 0")
        else:
            st.success("No pending loans! You are debt free.")
    else:
        st.info("No records found.")

# --- 5. EXPENSE TRACKER ---
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

# --- 6. ALL RECORDS ---
elif menu == "All Records":
    tab1, tab2, tab3, tab4 = st.tabs(["Tenants", "Rent History", "Expenses", "Loans"])
    with tab1:
        st.dataframe(df_tenants)
    with tab2:
        try:
            df_hist = load_data("Rent_History")
            st.dataframe(df_hist)
        except:
            st.warning("No history yet.")
    with tab3:
        st.dataframe(df_expenses)
    with tab4:
        st.dataframe(df_loans)