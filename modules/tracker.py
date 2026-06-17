import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from utils.db import execute_query
from modules.members import get_current_user, get_family_members

CATEGORIES = ["Food", "Rent", "EMI", "Education", "Medical", "Travel", "Entertainment", "Utilities", "Other"]

def add_transaction(member_id, date_str, tx_type, category, amount, note):
    """Inserts a transaction into the database."""
    execute_query(
        "INSERT INTO transactions (member_id, date, type, category, amount, note) VALUES (?, ?, ?, ?, ?, ?)",
        (member_id, date_str, tx_type, category, amount, note),
        is_select=False
    )

def delete_transaction(tx_id):
    """Deletes a transaction from the database."""
    execute_query("DELETE FROM transactions WHERE id = ?", (tx_id,), is_select=False)

def get_transactions_df(user_id):
    """Fetches transactions joined with member details as a Pandas DataFrame."""
    query = """
        SELECT t.id as transaction_id, t.date, t.type, t.category, t.amount, t.note,
               m.id as member_id, m.name as member_name, m.relationship
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        WHERE m.user_id = ?
        ORDER BY t.date DESC
    """
    rows = execute_query(query, (user_id,))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        'transaction_id', 'date', 'type', 'category', 'amount', 'note', 'member_id', 'member_name', 'relationship'
    ])

def show_tracker_page():
    user = get_current_user()
    if not user:
        st.warning("Please setup your profile first.")
        return
        
    st.markdown("## Income & Expense Tracker")
    
    # Fetch members for dropdown
    members = get_family_members(user['id'])
    member_options = {m['name']: m['id'] for m in members}
    
    # Tabs: Add Transaction, Log & Charts, Member Summary
    tab1, tab2, tab3 = st.tabs(["➕ Add Transaction", "📊 Log & Trends", "👥 Monthly Summary"])
    
    with tab1:
        st.markdown("### Record New Transaction")
        with st.form("add_transaction_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                member_name = st.selectbox("Family Member", options=list(member_options.keys()))
                tx_type = st.selectbox("Transaction Type", options=["Expense", "Income"])
                category = st.selectbox("Category", options=CATEGORIES)
            with col2:
                amount = st.number_input("Amount (₹)", min_value=0.01, step=100.0, format="%.2f")
                date = st.date_input("Date", value=datetime.date.today())
                note = st.text_input("Note/Description", placeholder="E.g., Weekly groceries, Salary")
                
            submitted = st.form_submit_form_button("Add Transaction", type="primary")
            if submitted:
                add_transaction(member_options[member_name], date.strftime("%Y-%m-%d"), tx_type, category, amount, note)
                st.success(f"Added {tx_type} of ₹{amount:,.2f} for {member_name}!")
                st.rerun()
                
    # Get all transactions
    df = get_transactions_df(user['id'])
    
    with tab2:
        if df.empty:
            st.info("No transactions recorded yet. Go to the 'Add Transaction' tab to add some.")
        else:
            # Filters Sidebar/Expander
            with st.expander("🔍 Filter Transactions", expanded=True):
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                with col_f1:
                    filter_member = st.selectbox("Member", options=["All"] + list(member_options.keys()))
                with col_f2:
                    filter_type = st.selectbox("Type", options=["All", "Expense", "Income"])
                with col_f3:
                    filter_cat = st.multiselect("Category", options=CATEGORIES, default=[])
                with col_f4:
                    # Date range filter
                    min_date = pd.to_datetime(df['date']).min().date()
                    max_date = pd.to_datetime(df['date']).max().date()
                    date_range = st.date_input("Date Range", value=(min_date, max_date))
            
            # Apply filters to copy of df
            filtered_df = df.copy()
            filtered_df['date_dt'] = pd.to_datetime(filtered_df['date']).dt.date
            
            if filter_member != "All":
                filtered_df = filtered_df[filtered_df['member_name'] == filter_member]
            if filter_type != "All":
                filtered_df = filtered_df[filtered_df['type'] == filter_type]
            if filter_cat:
                filtered_df = filtered_df[filtered_df['category'].isin(filter_cat)]
            if isinstance(date_range, tuple) and len(date_range) == 2:
                filtered_df = filtered_df[(filtered_df['date_dt'] >= date_range[0]) & (filtered_df['date_dt'] <= date_range[1])]
            
            # KPI Tiles
            kpi_income = filtered_df[filtered_df['type'] == 'Income']['amount'].sum()
            kpi_expense = filtered_df[filtered_df['type'] == 'Expense']['amount'].sum()
            kpi_net = kpi_income - kpi_expense
            
            c_k1, c_k2, c_k3 = st.columns(3)
            with c_k1:
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid #10B981;">
                        <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Total Income</span>
                        <h3 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{kpi_income:,.2f}</h3>
                    </div>
                    """, unsafe_allow_html=True
                )
            with c_k2:
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid #EF4444;">
                        <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Total Expenses</span>
                        <h3 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{kpi_expense:,.2f}</h3>
                    </div>
                    """, unsafe_allow_html=True
                )
            with c_k3:
                net_color = "#10B981" if kpi_net >= 0 else "#EF4444"
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid {net_color};">
                        <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Net Savings</span>
                        <h3 style="margin: 5px 0 0 0; color: {net_color};">₹{kpi_net:,.2f}</h3>
                    </div>
                    """, unsafe_allow_html=True
                )
            
            st.markdown("### Transaction Trends")
            
            # Format Date for Charting Groupby (YYYY-MM)
            filtered_df['month'] = pd.to_datetime(filtered_df['date']).dt.strftime('%Y-%m')
            
            monthly_trend = filtered_df.groupby(['month', 'type'])['amount'].sum().reset_index()
            
            if not monthly_trend.empty:
                fig = px.bar(
                    monthly_trend, 
                    x='month', 
                    y='amount', 
                    color='type', 
                    barmode='group',
                    labels={'amount': 'Amount (₹)', 'month': 'Month', 'type': 'Type'},
                    color_discrete_map={'Income': '#10B981', 'Expense': '#EF4444'},
                    template="plotly_dark"
                )
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available for the trend chart after filtering.")
                
            # Log Table
            st.markdown("### Transaction Log")
            
            # Display and delete buttons
            log_cols = ["date", "member_name", "type", "category", "amount", "note"]
            display_df = filtered_df[log_cols].copy()
            display_df.columns = ["Date", "Member", "Type", "Category", "Amount (₹)", "Note"]
            
            # Streamlit Dataframe display with color coding
            st.dataframe(
                display_df.style.format({"Amount (₹)": "₹{:,.2f}"})
                .map(lambda val: 'color: #10B981' if val == 'Income' else ('color: #EF4444' if val == 'Expense' else ''), subset=['Type']),
                use_container_width=True
            )
            
            # Option to delete transactions
            st.markdown("#### Manage Transactions")
            tx_to_delete = st.selectbox(
                "Select Transaction to Delete",
                options=filtered_df.apply(lambda r: f"ID {r['transaction_id']} | {r['date']} | {r['member_name']} | {r['type']} | {r['category']} | ₹{r['amount']}", axis=1),
                index=None,
                placeholder="Choose a transaction..."
            )
            if tx_to_delete:
                tx_id = int(tx_to_delete.split(" | ")[0].replace("ID ", ""))
                if st.button("Delete Transaction", type="secondary"):
                    delete_transaction(tx_id)
                    st.success("Transaction deleted successfully.")
                    st.rerun()
                    
    with tab3:
        if df.empty:
            st.info("No transaction data to summarize.")
        else:
            df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
            
            st.markdown("### Family Total Income & Expenses by Category")
            cat_summary = df.groupby(['category', 'type'])['amount'].sum().reset_index()
            fig_cat = px.bar(
                cat_summary, 
                x='category', 
                y='amount', 
                color='type', 
                barmode='group',
                color_discrete_map={'Income': '#10B981', 'Expense': '#EF4444'},
                template="plotly_dark",
                labels={'amount': 'Total Amount (₹)', 'category': 'Category'}
            )
            fig_cat.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_cat, use_container_width=True)
            
            st.markdown("### Monthly Member-wise Summary")
            
            # Pivot table: Months as index, Member Name + Type as columns
            summary_pivot = df.pivot_table(
                values='amount', 
                index=['month', 'type'], 
                columns='member_name', 
                aggfunc='sum', 
                fill_value=0.0
            )
            
            # Add Family Total
            summary_pivot['Family Total'] = summary_pivot.sum(axis=1)
            summary_pivot = summary_pivot.reset_index()
            
            st.dataframe(
                summary_pivot.style.format(
                    {col: "₹{:,.2f}" for col in summary_pivot.columns if col not in ['month', 'type']}
                ).map(lambda val: 'color: #10B981; font-weight: bold;' if val == 'Income' else ('color: #EF4444; font-weight: bold;' if val == 'Expense' else ''), subset=['type']),
                use_container_width=True
            )
            
            # Category share of Expenses
            st.markdown("### Category-wise Expenses Breakdown")
            exp_df = df[df['type'] == 'Expense']
            if not exp_df.empty:
                fig_pie = px.pie(
                    exp_df, 
                    values='amount', 
                    names='category', 
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    template="plotly_dark"
                )
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No expense data recorded yet to show breakdown.")
