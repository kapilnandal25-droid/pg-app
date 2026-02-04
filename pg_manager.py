import streamlit as st
import pandas as pd
import gspread

# --- CONFIGURATION ---
SHEET_NAME = "PG_Data_Master"  # Must match your Google Sheet Name exactly

# --- BACKEND FUNCTIONS (GOOGLE SHEETS) ---
def connect_to_sheet():
    # Connect using the secrets you saved in Streamlit Cloud
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open(SHEET_NAME)
    return sh.sheet1

def load_data():
    worksheet = connect_to_sheet()
    data = worksheet.get_all_records()
    
    if not data:
        # Return empty dataframe with columns if sheet is empty
        return pd.DataFrame(columns=[
            "Tenant Name", "Room Number", "Phone", 
            "Rent Amount", "Move-In Date", "Last Rent Paid (Month)", "Status"
        ])
    
    return pd.DataFrame(data)

def save_new_tenant(tenant_data):
    worksheet = connect_to_sheet()
    # Convert dictionary values to a list
    row = [
        tenant_data["Tenant Name"],
        tenant_data["Room Number"],
        tenant_data["Phone"],
        tenant_data["Rent Amount"],
        str(tenant_data["Move-In Date"]),
        tenant_data["Last Rent Paid (Month)"],
        tenant_data["Status"]
    ]
    # Append row to Google Sheet
    worksheet.append_row(row)

def update_rent_payment(tenant_name, month):
    worksheet = connect_to_sheet()
    # Find the cell to update (This is a simple search)
    cell = worksheet.find(tenant_name)
    if cell:
        # Assuming "Last Rent Paid" is the 6th column (Column F)
        worksheet.update_cell(cell.row, 6, month)

# --- USER INTERFACE ---
st.set_page_config(page_title="PG Manager Cloud", page_icon="☁️")
st.title("☁️ My PG Management System (Live)")

# Load data fresh from Google Sheets
try:
    df = load_data()
except Exception as e:
    st.error(f"Error connecting to Google Sheets: {e}")
    st.stop()

# Sidebar Menu
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add New Tenant", "Manage Payments", "Tenant List"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.subheader("Business Overview")
    
    total_tenants = len(df)
    # Ensure Rent Amount is numeric for calculation
    df['Rent Amount'] = pd.to_numeric(df['Rent Amount'], errors='coerce').fillna(0)
    total_revenue = df['Rent Amount'].sum()
    
    col1, col2 = st.columns(2)
    col1.metric("Total Tenants", total_tenants)
    col2.metric("Monthly Revenue", f"₹{total_revenue:,}")

# --- 2. ADD NEW TENANT ---
elif menu == "Add New Tenant":
    st.subheader("Register New Customer")
    with st.form("add_tenant_form"):
        name = st.text_input("Full Name")
        room = st.text_input("Room Number")
        phone = st.text_input("Phone Number")
        rent = st.number_input("Monthly Rent Amount", min_value=0, step=500)
        move_in = st.date_input("Move-In Date")
        
        submitted = st.form_submit_button("Add Tenant to Cloud")
        
        if submitted:
            if name and room:
                new_data = {
                    "Tenant Name": name,
                    "Room Number": room,
                    "Phone": phone,
                    "Rent Amount": rent,
                    "Move-In Date": move_in,
                    "Last Rent Paid (Month)": "None",
                    "Status": "Active"
                }
                save_new_tenant(new_data)
                st.success(f"{name} saved to Google Sheet!")
                st.rerun()
            else:
                st.warning("Please fill in Name and Room Number.")

# --- 3. MANAGE PAYMENTS ---
elif menu == "Manage Payments":
    st.subheader("Update Rent Status")
    
    if df.empty:
        st.info("No tenants found.")
    else:
        tenant_list = df["Tenant Name"].tolist()
        selected_tenant = st.selectbox("Select Tenant", tenant_list)
        
        months = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
        selected_month = st.selectbox("Select Month to Mark Paid", months)
        
        if st.button("Mark as PAID"):
            update_rent_payment(selected_tenant, selected_month)
            st.success(f"Updated Google Sheet for {selected_tenant}")
            st.rerun()

# --- 4. TENANT LIST ---
elif menu == "Tenant List":
    st.subheader("Master Database (From Google Sheets)")
    st.dataframe(df)
    
    if st.button("Refresh Data"):
        st.rerun()