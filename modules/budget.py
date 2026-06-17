import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from utils.db import execute_query
from modules.members import get_current_user, get_family_members

def get_budgets(user_id, month):
    """Fetches all budgets for a given user and month (YYYY-MM)."""
    # SQLite does not treat multiple NULL values as equal in UNIQUE constraints,
    # so we will query and handle updates manually to be fully reliable.
    query = """
        SELECT b.id, b.member_id, b.month, b.category, b.limit_amount,
               m.name as member_name
        FROM budgets b
        LEFT JOIN members m ON b.member_id = m.id
        WHERE b.month = ? AND (m.user_id = ? OR b.member_id IS NULL)
    """
    # Wait, if member_id is NULL, it's a family-wide budget.
    # To check if it belongs to this user, we must ensure that either it's family-wide (and we only have one primary user anyway) 
    # or the member belongs to the user.
    # Let's adjust the query to only get family-wide budgets AND user's member budgets.
    query = """
        SELECT b.id, b.member_id, b.month, b.category, b.limit_amount,
               CASE WHEN b.member_id IS NULL THEN 'Family (Combined)' ELSE m.name END as member_name
        FROM budgets b
        LEFT JOIN members m ON b.member_id = m.id
        WHERE b.month = ? AND (b.member_id IS NULL OR m.user_id = ?)
    """
    rows = execute_query(query, (month, user_id))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['id', 'member_id', 'month', 'category', 'limit_amount', 'member_name'])

def set_budget(member_id, month, category, limit_amount):
    """Inserts or updates a budget record."""
    # Check if exists
    if member_id is None:
        exists = execute_query(
            "SELECT id FROM budgets WHERE member_id IS NULL AND month = ? AND category = ?",
            (month, category)
        )
    else:
        exists = execute_query(
            "SELECT id FROM budgets WHERE member_id = ? AND month = ? AND category = ?",
            (member_id, month, category)
        )
        
    if exists:
        execute_query(
            "UPDATE budgets SET limit_amount = ? WHERE id = ?",
            (limit_amount, exists[0]['id']),
            is_select=False
        )
    else:
        execute_query(
            "INSERT INTO budgets (member_id, month, category, limit_amount) VALUES (?, ?, ?, ?)",
            (member_id, month, category, limit_amount),
            is_select=False
        )

def get_actual_expenses(user_id, month):
    """Fetches actual expense transactions grouped by member, month (YYYY-MM), and category."""
    query = """
        SELECT m.id as member_id, m.name as member_name, t.category, SUM(t.amount) as actual_amount
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        WHERE m.user_id = ? 
          AND t.type = 'Expense' 
          AND STRFTIME('%Y-%m', t.date) = ?
        GROUP BY m.id, m.name, t.category
    """
    rows = execute_query(query, (user_id, month))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['member_id', 'member_name', 'category', 'actual_amount'])

def delete_budget(budget_id):
    """Deletes a budget record."""
    execute_query("DELETE FROM budgets WHERE id = ?", (budget_id,), is_select=False)

def show_budget_page():
    user = get_current_user()
    if not user:
        st.warning("Please setup your profile first.")
        return
        
    st.markdown("## Monthly Budget Planner")
    
    # Selection of Month
    current_month_str = datetime.date.today().strftime("%Y-%m")
    selected_month = st.sidebar.text_input("Active Budget Month (YYYY-MM)", value=current_month_str)
    
    try:
        datetime.datetime.strptime(selected_month, "%Y-%m")
    except ValueError:
        st.error("Invalid month format! Please use YYYY-MM (e.g. 2026-06)")
        return
        
    # Get members
    members = get_family_members(user['id'])
    
    # Setup choices for member dropdown
    member_choices = {"Family (Combined)": None}
    for m in members:
        member_choices[m['name']] = m['id']
        
    # Tabs: Set Budget, Budget vs Actual
    tab1, tab2 = st.tabs(["⚙️ Set/Update Budgets", "📊 Budget vs Actual"])
    
    with tab1:
        st.markdown(f"### Configure Budgets for {selected_month}")
        with st.form("set_budget_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                target_member = st.selectbox("Assign Budget To", options=list(member_choices.keys()))
                category = st.selectbox("Category", options=["Food", "Rent", "EMI", "Education", "Medical", "Travel", "Entertainment", "Utilities", "Other"])
            with col2:
                limit_amount = st.number_input("Budget Limit (₹)", min_value=0.0, step=500.0, format="%.2f")
                st.write("") # placeholder
                st.write("") # placeholder
                
            submitted = st.form_submit_form_button("Save Budget", type="primary")
            if submitted:
                set_budget(member_choices[target_member], selected_month, category, limit_amount)
                st.success(f"Saved budget of ₹{limit_amount:,.2f} for {category} ({target_member}).")
                st.rerun()
                
        # List of existing budgets
        st.markdown("#### Configured Budgets")
        budgets_df = get_budgets(user['id'], selected_month)
        if budgets_df.empty:
            st.info("No budgets defined for this month yet.")
        else:
            display_budgets = budgets_df[['member_name', 'category', 'limit_amount', 'id']].copy()
            display_budgets.columns = ["Assigned To", "Category", "Limit (₹)", "id"]
            
            st.dataframe(
                display_budgets[["Assigned To", "Category", "Limit (₹)"]].style.format({"Limit (₹)": "₹{:,.2f}"}),
                use_container_width=True
            )
            
            # Delete budget option
            to_delete = st.selectbox(
                "Select Budget to Remove",
                options=budgets_df.apply(lambda r: f"ID {r['id']} | {r['member_name']} | {r['category']} | ₹{r['limit_amount']}", axis=1),
                index=None,
                placeholder="Choose a budget to delete..."
            )
            if to_delete:
                b_id = int(to_delete.split(" | ")[0].replace("ID ", ""))
                if st.button("Delete Budget", type="secondary"):
                    delete_budget(b_id)
                    st.success("Budget record deleted.")
                    st.rerun()

    with tab2:
        st.markdown(f"### Spending analysis for {selected_month}")
        
        # Toggle Level: Family-level vs Individual-level
        level = st.radio(
            "Analysis View Level",
            options=["Family Level (Combined)", "Individual Member Level"],
            horizontal=True
        )
        
        budgets_df = get_budgets(user['id'], selected_month)
        actual_df = get_actual_expenses(user['id'], selected_month)
        
        # We will build a category list
        categories_list = ["Food", "Rent", "EMI", "Education", "Medical", "Travel", "Entertainment", "Utilities", "Other"]
        
        comparison_rows = []
        
        if level == "Family Level (Combined)":
            # Combine all budgets (family-wide + individual member budgets) per category
            # Combine all actual expenses per category
            for cat in categories_list:
                # Limit sum
                cat_budgets = budgets_df[budgets_df['category'] == cat]
                # If there's a family-wide budget (member_id is NULL), we use it. 
                # Else, we sum individual budgets for this category to get a family total.
                family_wide = cat_budgets[cat_budgets['member_id'].isnull()]
                if not family_wide.empty:
                    limit = family_wide['limit_amount'].sum()
                else:
                    # Sum individual member limits
                    limit = cat_budgets['limit_amount'].sum()
                    
                # Actual sum across family
                cat_actual = actual_df[actual_df['category'] == cat]
                actual = cat_actual['actual_amount'].sum()
                
                comparison_rows.append({
                    "Category": cat,
                    "Budget Limit": limit,
                    "Actual Spend": actual
                })
        else:
            # Individual Member Level
            selected_member = st.selectbox("Select Member to Analyze", options=[m['name'] for m in members])
            m_id = member_choices[selected_member]
            
            for cat in categories_list:
                # Find budget for this specific member
                m_budget = budgets_df[(budgets_df['category'] == cat) & (budgets_df['member_id'] == m_id)]
                limit = m_budget['limit_amount'].sum() if not m_budget.empty else 0.0
                
                # Find actual expense for this specific member
                m_actual = actual_df[(actual_df['category'] == cat) & (actual_df['member_id'] == m_id)]
                actual = m_actual['actual_amount'].sum() if not m_actual.empty else 0.0
                
                comparison_rows.append({
                    "Category": cat,
                    "Budget Limit": limit,
                    "Actual Spend": actual
                })
                
        comp_df = pd.DataFrame(comparison_rows)
        
        # Calculate Remaining, % Used, and Status
        comp_df['Remaining'] = comp_df['Budget Limit'] - comp_df['Actual Spend']
        comp_df['% Used'] = comp_df.apply(lambda r: (r['Actual Spend'] / r['Budget Limit'] * 100) if r['Budget Limit'] > 0 else (0.0 if r['Actual Spend'] == 0 else float('inf')), axis=1)
        
        def get_status(row):
            limit = row['Budget Limit']
            actual = row['Actual Spend']
            if limit == 0:
                return "Unbudgeted" if actual > 0 else "N/A"
            pct = (actual / limit) * 100
            if pct < 80:
                return "Safe"
            elif pct <= 100:
                return "Near Limit"
            else:
                return "Over Budget"
                
        comp_df['Status'] = comp_df.apply(get_status, axis=1)
        
        # Render Comparison Chart
        if comp_df['Budget Limit'].sum() > 0 or comp_df['Actual Spend'].sum() > 0:
            chart_df = comp_df.melt(id_vars=['Category'], value_vars=['Budget Limit', 'Actual Spend'], var_name='Type', value_name='Amount')
            fig = px.bar(
                chart_df,
                x='Category',
                y='Amount',
                color='Type',
                barmode='group',
                color_discrete_map={'Budget Limit': '#F59E0B', 'Actual Spend': '#10B981'},
                template="plotly_dark",
                labels={'Amount': 'Amount (₹)', 'Category': 'Category'}
            )
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
            # Progress Bars and Cards
            st.markdown("### Budget Health Cards")
            col_idx = 0
            cols = st.columns(3)
            
            for index, row in comp_df.iterrows():
                # Skip category with 0 budget and 0 actual expense
                if row['Budget Limit'] == 0 and row['Actual Spend'] == 0:
                    continue
                    
                limit = row['Budget Limit']
                actual = row['Actual Spend']
                pct = row['% Used']
                status = row['Status']
                
                # Color code selection
                if status == "Safe":
                    progress_color = "#10B981" # Green
                    border_color = "5px solid #10B981"
                elif status == "Near Limit":
                    progress_color = "#F59E0B" # Yellow/Amber
                    border_color = "5px solid #F59E0B"
                else: # Over budget / Unbudgeted
                    progress_color = "#EF4444" # Red
                    border_color = "5px solid #EF4444"
                    
                pct_val = min(1.0, actual / limit) if limit > 0 else 1.0
                
                with cols[col_idx % 3]:
                    st.markdown(
                        f"""
                        <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; border-left: {border_color}; margin-bottom: 15px;">
                            <span style="font-size: 0.95rem; font-weight: bold; color: #E2E8F0;">{row['Category']}</span>
                            <span style="font-size: 0.75rem; color: #E2E8F0; background: {progress_color}44; border: 1px solid {progress_color}; padding: 1px 5px; border-radius: 4px; float: right;">{status}</span>
                            <div style="margin-top: 10px; font-size: 0.8rem; color: #94A3B8;">
                                Spent: <b>₹{actual:,.2f}</b> / ₹{limit:,.2f}
                            </div>
                            <div style="width: 100%; bg-color: #334155; height: 8px; border-radius: 4px; background: #334155; margin-top: 8px; overflow: hidden;">
                                <div style="width: {pct_val*100}%; background: {progress_color}; height: 100%; border-radius: 4px;"></div>
                            </div>
                            <div style="font-size: 0.75rem; color: #94A3B8; margin-top: 4px; text-align: right;">
                                {pct:,.1f}% Used
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                col_idx += 1
                
            st.markdown("### Budget vs Actual Details Table")
            # Style Table
            def color_rows(val):
                if val == 'Safe':
                    return 'color: #10B981; font-weight: bold;'
                elif val == 'Near Limit':
                    return 'color: #F59E0B; font-weight: bold;'
                elif val == 'Over Budget':
                    return 'color: #EF4444; font-weight: bold;'
                return ''
                
            st.dataframe(
                comp_df.style.format({
                    "Budget Limit": "₹{:,.2f}",
                    "Actual Spend": "₹{:,.2f}",
                    "Remaining": "₹{:,.2f}",
                    "% Used": "{:,.1f}%"
                }).map(color_rows, subset=['Status']),
                use_container_width=True
            )
        else:
            st.info("No budgets or expenses entered for this month. Set budgets in the 'Set/Update Budgets' tab.")
