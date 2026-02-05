import streamlit as st
import pandas as pd
import gspread

# --- CONFIGURATION ---
SHEET_NAME = "PG_Data_Master"  # Your Google Sheet Name

# --- BACKEND FUNCTIONS ---
def get_worksheet(tab_name):
    # Connect to a specific tab (Tenants or Expenses)
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open(SHEET_NAME)
    return sh.worksheet(tab_name)

def load_data(tab_name):
    worksheet = get_worksheet(tab_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def save_new_tenant(tenant_data):
    worksheet = get_worksheet("Tenants") # Specifically save to Tenants tab
    row = [
        tenant_data["Tenant Name"], tenant_data["Room Number"],
        tenant_data["Phone"], tenant_data["Rent Amount"],
        str(tenant_data["Move-In Date"]), tenant_data["Last Rent Paid (Month)"],
        tenant_data["Status"]
    ]
    worksheet.append_row(row)

def save_expense(expense_data):
    worksheet = get_worksheet("Expenses") # Specifically save to Expenses tab
    row = [
        str(expense_data["Date"]),
        expense_data["Category"],
        expense_data["Amount"],
        expense_data["Note"]
    ]
    worksheet.append_row(row)

def update_rent_payment(tenant_name, month):
    worksheet = get_worksheet("Tenants")
    cell = worksheet.find(tenant_name)
    if cell:
        worksheet.update_cell(cell.row, 6, month)

# --- USER INTERFACE ---
st.set_page_config(page_title="PG Manager Pro", page_icon="📈")
st.title("📈 PG Business Manager 2.0")

# Load Data safely
try:
    df_tenants = load_data("Tenants")
    df_expenses = load_data("Expenses")
except Exception as e:
    st.error(f"Error connecting to Google Sheets. Did you create the 'Expenses' tab? Error: {e}")
    st.stop()

# Sidebar
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add Tenant", "Manage Rent", "Expense Tracker", "All Records"])

# --- 1. DASHBOARD (PROFIT & LOSS) ---
if menu == "Dashboard":
    st.subheader("💰 Financial Health")
    
    # Calculate Revenue (Rent)
    df_tenants['Rent Amount'] = pd.to_numeric(df_tenants['Rent Amount'], errors='coerce').fillna(0)
    total_revenue = df_tenants['Rent Amount'].sum()
    
    # Calculate Expenses
    if not df_expenses.empty:
        df_expenses['Amount'] = pd.to_numeric(df_expenses['Amount'], errors='coerce').fillna(0)
        total_expenses = df_expenses['Amount'].sum()
    else:
        total_expenses = 0
        
    net_profit = total_revenue - total_expenses
    
    # Display Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Expected Revenue", f"₹{total_revenue:,}")
    col2.metric("Total Expenses", f"₹{total_expenses:,}")
    col3.metric("Net Profit", f"₹{net_profit:,}", delta_color="normal")
    
    if net_profit > 0:
        st.success("You are profitable! 🎉")
    else:
        st.warning("Expenses are higher than revenue. ⚠️")

# --- 2. ADD TENANT ---
elif menu == "Add Tenant":
    st.subheader("Add New Tenant")
    with st.form("add_tenant"):
        name = st.text_input("Name")
        room = st.text_input("Room")
        phone = st.text_input("Phone")
        rent = st.number_input("Rent", step=500)
        move_in = st.date_input("Date")
        if st.form_submit_button("Save Tenant"):
            save_new_tenant({
                "Tenant Name": name, "Room Number": room, "Phone": phone,
                "Rent Amount": rent, "Move-In Date": move_in,
                "Last Rent Paid (Month)": "None", "Status": "Active"
            })
            st.success("Tenant Added!")
            st.rerun()

# --- 3. MANAGE RENT ---
elif menu == "Manage Rent":
    st.subheader("Record Rent Payment")
    if not df_tenants.empty:
        tenant = st.selectbox("Tenant", df_tenants["Tenant Name"].tolist())
        month = st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        if st.button("Mark Paid"):
            update_rent_payment(tenant, month)
            st.success("Updated!")

# --- 4. EXPENSE TRACKER ---
elif menu == "Expense Tracker":
    st.subheader("💸 Record an Expense")
    with st.form("add_expense"):
        date = st.date_input("Date")
        category = st.selectbox("Category", ["Electricity Bill", "Internet", "Maid/Cleaning", "Repairs", "Groceries", "Other"])
        amount = st.number_input("Amount (₹)", min_value=0, step=100)
        note = st.text_input("Note (Optional)")
        
        if st.form_submit_button("Add Expense"):
            save_expense({
                "Date": date, "Category": category, 
                "Amount": amount, "Note": note
            })
            st.success("Expense Saved!")
            st.rerun()

# --- 5. ALL RECORDS ---
elif menu == "All Records":
    tab1, tab2 = st.tabs(["Tenants", "Expenses"])
    with tab1:
        st.dataframe(df_tenants)
    with tab2:
        st.dataframe(df_expenses)