import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
import os
import sqlite3

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Smart Expense Tracker", layout="wide")

DB_FILE = "tracker.db"

# --------- SESSION STATE FOR EXIT ---------
if "exited" not in st.session_state:
    st.session_state.exited = False

# ---------------- HEALTH / FEEDBACK HELPERS ----------------
HEALTHY_CATEGORIES = {
    "Groceries",
    "Healthcare",
    "Medicine",
    "Gym",
    "Fitness",
    "Sports",
}

UNHEALTHY_CATEGORIES = {
    "Fast Food",
    "Junk Food",
    "Alcohol",
    "Smoking",
    "Sweets",
}

# Expanded category list to include health-related options
CATEGORY_DISPLAY = [
    "Food",
    "Groceries",
    "Fast Food",
    "Healthcare",
    "Medicine",
    "Gym",
    "Fitness",
    "Sports",
    "Travel",
    "Shopping",
    "Bills",
    "Others",
]

# ---------------- DATABASE HELPERS ----------------
def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            amount REAL,
            description TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS budget (
            month TEXT PRIMARY KEY,
            budget REAL
        )
        """
    )
    return conn


def load_expenses() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT
            id AS ID,
            date AS Date,
            category AS Category,
            amount AS Amount,
            description AS Description
        FROM expenses
        ORDER BY date ASC, id ASC
        """,
        conn,
    )
    conn.close()
    return df


def save_expense(date_value, category, amount, description):
    conn = get_conn()
    conn.execute(
        "INSERT INTO expenses(date, category, amount, description) VALUES (?, ?, ?, ?)",
        (str(date_value), category, float(amount), description),
    )
    conn.commit()
    conn.close()


def delete_expense_by_id(row_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM expenses WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()


def load_budget() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT
            month AS Month,
            budget AS Budget
        FROM budget
        ORDER BY month ASC
        """,
        conn,
    )
    conn.close()
    return df


def save_budget_row(month: str, budget_amount: float):
    conn = get_conn()
    conn.execute(
        """
        INSERT OR REPLACE INTO budget(month, budget)
        VALUES (?, ?)
        """,
        (month, float(budget_amount)),
    )
    conn.commit()
    conn.close()


def clear_all_data():
    conn = get_conn()
    conn.execute("DELETE FROM expenses")
    conn.execute("DELETE FROM budget")
    conn.commit()
    conn.close()


# ---------------- HEALTH / FEEDBACK LOGIC ----------------
def get_health_tag(cat: str) -> str:
    if cat in HEALTHY_CATEGORIES:
        return "healthy"
    if cat in UNHEALTHY_CATEGORIES:
        return "unhealthy"
    if cat == "Food":
        return "neutral"
    return "neutral"


def generate_health_feedback(month_df: pd.DataFrame) -> str:
    exp_df = month_df[month_df["Category"] != "Income"].copy()
    if exp_df.empty:
        return "No expenses recorded this month, so no lifestyle feedback yet."

    exp_df["HealthTag"] = exp_df["Category"].apply(get_health_tag)

    total_spent = exp_df["Amount"].sum()
    healthy_spent = exp_df[exp_df["HealthTag"] == "healthy"]["Amount"].sum()
    unhealthy_spent = exp_df[exp_df["HealthTag"] == "unhealthy"]["Amount"].sum()

    healthy_pct = (healthy_spent / total_spent) * 100 if total_spent > 0 else 0
    unhealthy_pct = (unhealthy_spent / total_spent) * 100 if total_spent > 0 else 0

    if unhealthy_pct >= 50:
        return (
            f"You spent about {unhealthy_pct:.0f}% of your expenses on unhealthy items. "
            "Consider reducing fast food, alcohol, or junk purchases and think about "
            "taking or reviewing a health insurance plan."
        )
    elif healthy_pct >= 50:
        return (
            f"Great job! Around {healthy_pct:.0f}% of your expenses are on healthy areas "
            "like groceries, healthcare, or fitness. Your spending pattern looks "
            "supportive of a healthy lifestyle."
        )
    else:
        return (
            "Your spending is mixed between healthy and other categories. Try to shift "
            "more expenses towards healthcare, groceries, and fitness, and reduce "
            "unhealthy categories over time."
        )


def generate_income_feedback(month_df: pd.DataFrame) -> str:
    income = month_df[month_df["Category"] == "Income"]["Amount"].sum()
    expense = month_df[month_df["Category"] != "Income"]["Amount"].sum()

    if income == 0 and expense == 0:
        return "No income or expenses recorded for this month."
    if income == 0 and expense > 0:
        return "You recorded expenses but no income this month. Make sure to log your income or review your earning sources."
    if income > 0 and expense == 0:
        return "You recorded income but no expenses this month. Log your real‑life spending to get accurate tracking."

    savings = income - expense
    savings_pct = (savings / income) * 100 if income > 0 else 0

    if savings < 0:
        return (
            f"Your expenses exceeded your income by ₹ {abs(savings):,.0f}. "
            "Try to cut down non‑essential spending or find ways to increase income."
        )
    elif savings_pct < 10:
        return (
            f"You saved only about {savings_pct:.0f}% of your income. "
            "Aim to save at least 20% of your monthly income if possible."
        )
    else:
        return (
            f"Good job! You saved about {savings_pct:.0f}% of your income this month. "
            "Keep building this habit and consider investing or building an emergency fund."
        )


# ---------------- EXIT SCREEN -------------
def show_exit_screen():
    st.title("💰 Smart Expense Tracker")
    st.subheader("🚪 Exit App")
    st.success("Thank you for using our expense tracker, visit again!")
    st.info(
        "You can close this browser tab or stop the Streamlit app from your IDE/terminal."
    )

    if st.button("🔁 Restart App"):
        st.session_state.exited = False
        st.rerun()

    st.stop()


if st.session_state.exited:
    show_exit_screen()

# ---------------- UI ----------------
st.title("💰 Smart Expense Tracker")

menu = st.sidebar.radio(
    "App Menu",
    [
        "🏠 Dashboard",
        "🎯 Set Budget",
        "💵 Add Income",
        "💸 Add Expense",
        "📜 Expense History",
        "✂️ Delete Expense",
        "📊 Statistics",
        "🧠 Smart Insights & Feedback",
        "🚪 Exit App",
    ],
)

st.sidebar.divider()
if st.sidebar.button("🗑 Clear All Data"):
    clear_all_data()
    st.sidebar.success("All data cleared! Refresh app.")

if menu == "🚪 Exit App":
    st.session_state.exited = True
    show_exit_screen()

# ---------------- DASHBOARD ----------------
if menu == "🏠 Dashboard":
    st.subheader("📊 Overview")

    df = load_expenses()
    budget_df = load_budget()

    if df.empty:
        st.info("No data available. Start by adding income and expenses.")
        st.stop()

    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    income = df[df["Category"] == "Income"]["Amount"].sum()
    expense = df[df["Category"] != "Income"]["Amount"].sum()
    balance = income - expense

    # Normalize month format to YYYY-MM
    today_month = str(pd.Timestamp.today().to_period("M"))
    if not budget_df.empty:
        budget_df["Month"] = budget_df["Month"].astype(str)
    budget_row = budget_df[budget_df["Month"] == today_month]
    budget = float(budget_row.iloc[0]["Budget"]) if not budget_row.empty else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Balance", f"₹ {balance:,.0f}")
    c2.metric("🟢 Total Income", f"₹ {income:,.0f}")
    c3.metric("🔴 Total Expense", f"₹ {expense:,.0f}")
    c4.metric("🎯 Budget", f"₹ {budget:,.0f}")

    st.divider()

    # --------- BUDGET LOGIC ----------
    if budget > 0:
        budget_pct = (expense / budget) * 100 if budget > 0 else 0
        remaining = budget - expense

        col1, col2 = st.columns(2)
        col1.metric("📊 Budget Used", f"{budget_pct:.0f}%")
        col2.metric("💰 Remaining", f"₹ {remaining:,.0f}")

        if budget_pct >= 100:
            st.error(f"🚨 **BUDGET EXCEEDED!** Overspent by ₹ {abs(remaining):,.0f}")
        elif budget_pct >= 80:
            st.warning(
                f"⚠️ **{budget_pct:.0f}% budget used!** Only ₹ {remaining:,.0f} left"
            )
        elif budget_pct >= 50:
            st.info(f"ℹ️ **Half budget used.** ₹ {remaining:,.0f} remaining")
        else:
            st.success("✅ **Well within budget!** Keep it up!")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🧾 Recent Transactions")
        st.dataframe(df.tail(10), use_container_width=True)

    with col2:
        st.subheader("📊 Spending by Category")
        exp_df = df[df["Category"] != "Income"]

        if not exp_df.empty:
            fig = px.pie(exp_df, names="Category", values="Amount", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expense data yet.")

# ---------------- SET BUDGET ----------------
elif menu == "🎯 Set Budget":
    st.subheader("🎯 Set Monthly Budget")

    default_month = str(pd.Timestamp.today().to_period("M"))
    month_input = st.text_input("Enter Month (YYYY-MM)", value=default_month)
    budget_amount = st.number_input("Monthly Budget Amount", min_value=0.0)

    if st.button("Save Budget"):
        try:
            period = pd.Period(month_input, freq="M")
            month = str(period)
        except Exception:
            st.error("Please enter month in valid format like 2026-02.")
        else:
            save_budget_row(month, budget_amount)
            st.success(f"✅ Budget for {month} saved successfully!")

# ---------------- ADD INCOME ----------------
elif menu == "💵 Add Income":
    st.subheader("💵 Add Income")

    income_date = st.date_input("Date", date.today())
    income_amount = st.number_input("Income Amount", min_value=0.0)
    source = st.text_input("Income Source")

    if st.button("Save Income"):
        if income_amount <= 0:
            st.warning("Income amount should be greater than 0.")
        else:
            save_expense(income_date, "Income", income_amount, source)
            st.success("✅ Income added successfully!")

# ---------------- ADD EXPENSE ----------------
elif menu == "💸 Add Expense":
    st.subheader("💸 Add Expense")

    exp_date = st.date_input("Date", date.today())
    category = st.selectbox("Category", CATEGORY_DISPLAY)
    amount = st.number_input("Expense Amount", min_value=0.0)
    description = st.text_input("Description")

    if st.button("Save Expense"):
        if amount <= 0:
            st.warning("Expense amount should be greater than 0.")
        else:
            save_expense(exp_date, category, amount, description)
            st.success("✅ Expense added successfully!")

# ---------------- EXPENSE HISTORY ----------------
elif menu == "📜 Expense History":
    st.subheader("📜 Expense History (Expenses Only)")

    df = load_expenses()
    expense_df = df[df["Category"] != "Income"]

    if expense_df.empty:
        st.info("No expense records found.")
    else:
        st.dataframe(
            expense_df.sort_values("Date", ascending=False),
            use_container_width=True,
        )

# ---------------- DELETE EXPENSE ----------------
elif menu == "✂️ Delete Expense":
    st.subheader("✂️ Delete an Expense")

    df = load_expenses()
    expense_df = df[df["Category"] != "Income"].copy()

    if expense_df.empty:
        st.info("No expense records available to delete.")
    else:
        # Use DB ID as RowID
        expense_df = expense_df.rename(columns={"ID": "RowID"})

        st.write("Select a row to delete:")
        st.dataframe(expense_df, use_container_width=True)

        row_ids = expense_df["RowID"].tolist()
        selected_row_id = st.selectbox("RowID to delete", row_ids)

        if st.button("Delete Selected Expense"):
            delete_expense_by_id(int(selected_row_id))
            st.success(f"✅ Expense with RowID {selected_row_id} deleted successfully!")
            st.rerun()

# ---------------- STATISTICS ----------------
elif menu == "📊 Statistics":
    st.subheader("📊 Expense Statistics")

    df = load_expenses()
    if df.empty:
        st.info("No data available yet.")
    else:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
        df["Month"] = df["Date"].dt.to_period("M").astype(str)

        if df.empty:
            st.info("No valid dated records to show.")
        else:
            selected_month = st.selectbox(
                "Select Month", sorted(df["Month"].unique(), reverse=True)
            )
            month_df = df[df["Month"] == selected_month]

            if month_df.empty:
                st.info("No records for this month.")
            else:
                income = month_df[month_df["Category"] == "Income"]["Amount"].sum()
                expense = month_df[month_df["Category"] != "Income"]["Amount"].sum()

                st.metric("💵 Income", f"₹ {income:,.0f}")
                st.metric("💸 Expense", f"₹ {expense:,.0f}")

                exp_only = month_df[month_df["Category"] != "Income"]
                if not exp_only.empty:
                    fig = px.pie(
                        exp_only,
                        names="Category",
                        values="Amount",
                        hole=0.4,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No expenses in this month.")

# ---------------- SMART INSIGHTS & FEEDBACK ----------------
elif menu == "🧠 Smart Insights & Feedback":
    st.subheader("🧠 Smart Insights & Feedback")

    df = load_expenses()
    if df.empty:
        st.info(
            "No data available yet. Please add some income and expenses to see insights."
        )
    else:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
        df["Month"] = df["Date"].dt.to_period("M").astype(str)

        if df.empty:
            st.info("No valid dated records to show.")
        else:
            selected_month = st.selectbox(
                "Select Month for Feedback",
                sorted(df["Month"].unique(), reverse=True),
            )
            month_df = df[df["Month"] == selected_month]

            if month_df.empty:
                st.info("No records for this month.")
            else:
                income = month_df[month_df["Category"] == "Income"]["Amount"].sum()
                expense = month_df[month_df["Category"] != "Income"]["Amount"].sum()
                balance = income - expense

                c1, c2, c3 = st.columns(3)
                c1.metric("💵 Income", f"₹ {income:,.0f}")
                c2.metric("💸 Expense", f"₹ {expense:,.0f}")
                c3.metric("💰 Balance", f"₹ {balance:,.0f}")

                st.markdown("---")

                st.markdown("### 🧬 Lifestyle & Health Feedback")
                health_fb = generate_health_feedback(month_df)
                st.info(health_fb)

                st.markdown("### 🪙 Income & Savings Feedback")
                income_fb = generate_income_feedback(month_df)
                st.success(income_fb)

                exp_df = month_df[month_df["Category"] != "Income"]
                if not exp_df.empty:
                    st.markdown("### 📊 Where your money went")
                    fig = px.pie(exp_df, names="Category", values="Amount", hole=0.4)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(
                        "No expenses in this month, so no spending breakdown to show."
                    )
