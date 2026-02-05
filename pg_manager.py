import streamlit as st
import pandas as pd
import gspread

# --- CONFIGURATION ---
SHEET_NAME = "PG_Data_Master"

# --- BACKEND FUNCTIONS ---
def get_worksheet(tab_name):
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open(SHEET_NAME)
    return sh.worksheet(tab_name)

def load_data(tab_name):
    worksheet = get_worksheet(tab_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def save_new_tenant(tenant_data):
    worksheet = get_worksheet("Tenants")
    row = [
        tenant_data["Tenant Name"], tenant_data["Room Number"],
        tenant_data["Phone"], tenant_data["Rent Amount"],
        str(tenant_data["Move-In Date"]), tenant_data["Last Rent Paid (Month)"],
        tenant_data["Status"]
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

# --- USER INTERFACE ---
st.set_page_config(page_title="PG Manager Pro", page_icon="📱")
st.title("📱 PG Manager: WhatsApp Edition")

try:
    df_tenants = load_data("Tenants")
    df_expenses = load_data("Expenses")
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

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
        st.caption("⚠️ IMPORTANT: Add country code (91) before number, no + symbol.")
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

# --- 3. MANAGE RENT (UPDATED WITH WHATSAPP) ---
elif menu == "Manage Rent":
    st.subheader("Record Rent & Send Reminders")
    
    if not df_tenants.empty:
        # Select Tenant
        tenant_name = st.selectbox("Select Tenant", df_tenants["Tenant Name"].tolist())
        
        # Get Tenant Details automatically
        tenant_row = df_tenants[df_tenants["Tenant Name"] == tenant_name].iloc[0]
        phone_number = str(tenant_row["Phone"])
        rent_amt = tenant_row["Rent Amount"]
        
        col1, col2 = st.columns(2)
        
        # Payment Section
        with col1:
            st.write("### 💵 Mark Paid")
            month = st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            if st.button("Mark as PAID"):
                update_rent_payment(tenant_name, month)
                st.success("Updated!")
        
        # WhatsApp Section
        with col2:
            st.write("### 💬 Reminder")
            # Create the message
            msg = f"Hi {tenant_name}, this is a reminder that your rent of ₹{rent_amt} for this month is due. Please pay soon to avoid late fees. Thanks!"
            
            # Create the WhatsApp Link
            # Uses https://wa.me/NUMBER?text=MESSAGE format
            wa_link = f"https://wa.me/{phone_number}?text={msg}"
            
            st.markdown(f"[👉 **Click to Send WhatsApp**]({wa_link})")
            st.caption("Clicking this opens WhatsApp on your phone.")

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