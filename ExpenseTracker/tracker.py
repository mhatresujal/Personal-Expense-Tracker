import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import plotly.express as px

# --- Initialize session state for refresh ---
if 'refresh' not in st.session_state:
    st.session_state['refresh'] = False

# --- Database setup ---
conn = sqlite3.connect('expenses.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS expenses
                  (id INTEGER PRIMARY KEY, date TEXT, category TEXT, amount REAL, description TEXT)''')
conn.commit()

# --- Helper functions ---
def add_expense(date, category, amount, description):
    cursor.execute("INSERT INTO expenses (date, category, amount, description) VALUES (?, ?, ?, ?)",
                   (date, category, amount, description))
    conn.commit()

def get_expenses():
    df = pd.read_sql("SELECT * FROM expenses", conn)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

def delete_expense(expense_id):
    cursor.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    conn.commit()

def generate_report(df, start_date, end_date):
    filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    return filtered

# --- Streamlit UI ---
st.set_page_config(page_title="Personal Expense Tracker", layout="wide")
st.title("💸 Personal Expense Tracker Dashboard")

menu = ["Add Expense", "View Expenses", "Reports", "Statistics"]
choice = st.sidebar.selectbox("Menu", menu)

df = get_expenses()

# --- Sidebar Filters ---
if choice in ["Reports", "Statistics", "View Expenses"] and not df.empty:
    st.sidebar.subheader("Filters")
    min_date, max_date = df['date'].min(), df['date'].max()
    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)
    categories = ["All"] + df['category'].unique().tolist()
    category_filter = st.sidebar.selectbox("Category", categories)
    filtered_df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))]
    if category_filter != "All":
        filtered_df = filtered_df[filtered_df['category'] == category_filter]
else:
    filtered_df = df

# --- Add Expense ---
if choice == "Add Expense":
    st.subheader("Add New Expense")
    with st.form(key="add_expense_form"):
        date = st.date_input("Date", datetime.today())
        category = st.text_input("Category")
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        description = st.text_input("Description")
        submitted = st.form_submit_button("Add Expense")
        if submitted:
            add_expense(date.strftime("%Y-%m-%d"), category, amount, description)
            st.success("✅ Expense added successfully!")
            # Trigger refresh
            st.session_state['refresh'] = not st.session_state['refresh']

# --- View Expenses ---
elif choice == "View Expenses":
    st.subheader("All Expenses")
    if filtered_df.empty:
        st.info("No expenses found for the selected filters.")
    else:
        st.dataframe(filtered_df)
        delete_id = st.number_input("Enter ID to delete", min_value=0)
        if st.button("Delete Expense"):
            delete_expense(delete_id)
            st.success(f"Expense with ID {delete_id} deleted!")
            # Trigger refresh
            st.session_state['refresh'] = not st.session_state['refresh']

# --- Reports ---
elif choice == "Reports":
    st.subheader("Expense Reports")
    if filtered_df.empty:
        st.info("No expenses found for the selected filters.")
    else:
        total_expense = filtered_df['amount'].sum()
        weekly_expense = generate_report(df, datetime.today() - timedelta(days=7), datetime.today())['amount'].sum()
        monthly_expense = generate_report(df, datetime.today().replace(day=1), datetime.today())['amount'].sum()
        
        # --- Summary Cards ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Expenses", f"₹{total_expense:.2f}")
        col2.metric("Last 7 Days", f"₹{weekly_expense:.2f}")
        col3.metric("This Month", f"₹{monthly_expense:.2f}")
        
        st.dataframe(filtered_df)

# --- Statistics ---
elif choice == "Statistics":
    st.subheader("Expense Statistics")
    if filtered_df.empty:
        st.info("No data to show statistics.")
    else:
        # Pie chart by category
        category_sum = filtered_df.groupby('category')['amount'].sum().reset_index()
        fig1 = px.pie(category_sum, values='amount', names='category', title="Expenses by Category", hole=0.3)
        st.plotly_chart(fig1, use_container_width=True)
        
        # Monthly trend line
        filtered_df['month'] = filtered_df['date'].dt.to_period('M')
        monthly_sum = filtered_df.groupby('month')['amount'].sum().reset_index()
        monthly_sum['month'] = monthly_sum['month'].astype(str)
        fig2 = px.line(monthly_sum, x='month', y='amount', title="Monthly Expense Trend", markers=True)
        st.plotly_chart(fig2, use_container_width=True)
