import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- CONFIGURATION ---
DATA_FILE = "pg_data.csv"

# --- BACKEND FUNCTIONS ---
def load_data():
    if not os.path.exists(DATA_FILE):
        # Create a new dataframe if file doesn't exist
        df = pd.DataFrame(columns=[
            "Tenant Name", "Room Number", "Phone", 
            "Rent Amount", "Move-In Date", "Last Rent Paid (Month)", "Status"
        ])
        df.to_csv(DATA_FILE, index=False)
        return df
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- USER INTERFACE ---
st.set_page_config(page_title="PG Manager", page_icon="🏠")
st.title("🏠 My PG Management System")

# Load data
df = load_data()

# Sidebar Menu
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Add New Tenant", "Manage Payments", "Tenant List"])

# --- 1. DASHBOARD ---
if menu == "Dashboard":
    st.subheader("Business Overview")
    
    # Calculate Metrics
    total_tenants = len(df)
    total_revenue = df['Rent Amount'].sum() if not df.empty else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tenants", total_tenants)
    col2.metric("Monthly Revenue Potential", f"₹{total_revenue:,}")
    
    # Quick Alert for Unpaid Rent
    st.write("---")
    st.subheader("⚠️ Payment Alerts")
    current_month = datetime.now().strftime("%B")
    
    # Simple logic: If 'Last Rent Paid' is not current month, flag them
    if not df.empty:
        unpaid_tenants = df[df["Last Rent Paid (Month)"] != current_month]
        if not unpaid_tenants.empty:
            st.error(f"{len(unpaid_tenants)} tenants have not paid for {current_month} yet!")
            st.dataframe(unpaid_tenants[["Tenant Name", "Room Number", "Phone"]])
        else:
            st.success("Everyone has paid for this month!")

# --- 2. ADD NEW TENANT ---
elif menu == "Add New Tenant":
    st.subheader("Register New Customer")
    with st.form("add_tenant_form"):
        name = st.text_input("Full Name")
        room = st.text_input("Room Number")
        phone = st.text_input("Phone Number")
        rent = st.number_input("Monthly Rent Amount", min_value=0, step=500)
        move_in = st.date_input("Move-In Date")
        
        submitted = st.form_submit_button("Add Tenant")
        
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
                df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                save_data(df)
                st.success(f"{name} added successfully!")
            else:
                st.warning("Please fill in Name and Room Number.")

# --- 3. MANAGE PAYMENTS ---
elif menu == "Manage Payments":
    st.subheader("Update Rent Status")
    
    if df.empty:
        st.info("No tenants found. Go to 'Add New Tenant' first.")
    else:
        # Select Tenant
        tenant_list = df["Tenant Name"].tolist()
        selected_tenant = st.selectbox("Select Tenant", tenant_list)
        
        # Select Month
        months = ["January", "February", "March", "April", "May", "June", 
                  "July", "August", "September", "October", "November", "December"]
        current_month_index = datetime.now().month - 1
        selected_month = st.selectbox("Select Month to Mark Paid", months, index=current_month_index)
        
        if st.button("Mark as PAID"):
            # Update the specific row
            df.loc[df["Tenant Name"] == selected_tenant, "Last Rent Paid (Month)"] = selected_month
            save_data(df)
            st.success(f"Rent marked as PAID for {selected_tenant} ({selected_month})")
            st.balloons()

# --- 4. TENANT LIST ---
elif menu == "Tenant List":
    st.subheader("Master Database")
    st.dataframe(df)
    
    # Delete Option
    st.write("---")
    st.write("**Remove Tenant**")
    if not df.empty:
        t_to_delete = st.selectbox("Select Tenant to Remove", df["Tenant Name"].unique())
        if st.button("Delete Tenant"):
            df = df[df["Tenant Name"] != t_to_delete]
            save_data(df)
            st.warning(f"{t_to_delete} has been removed.")
            st.rerun()