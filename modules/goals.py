import streamlit as st
import pandas as pd
import datetime
from utils.db import execute_query
from modules.members import get_current_user, get_family_members
from utils.calculations import calculate_projected_completion

def get_goals(user_id):
    """Fetches all savings goals for the user, joined with member details."""
    query = """
        SELECT g.*, 
               CASE WHEN g.member_id IS NULL THEN 'Family (Combined)' ELSE m.name END as member_name
        FROM goals g
        LEFT JOIN members m ON g.member_id = m.id
        WHERE g.member_id IS NULL OR m.user_id = ?
    """
    rows = execute_query(query, (user_id,))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        'id', 'member_id', 'name', 'target_amount', 'saved_amount', 'monthly_contribution', 'deadline', 'member_name'
    ])

def add_goal(member_id, name, target, saved, monthly, deadline):
    """Inserts a new goal into the database."""
    execute_query(
        """
        INSERT INTO goals (member_id, name, target_amount, saved_amount, monthly_contribution, deadline)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (member_id, name, target, saved, monthly, deadline),
        is_select=False
    )

def update_goal_savings(goal_id, saved_amount):
    """Updates the saved amount of a goal."""
    execute_query(
        "UPDATE goals SET saved_amount = ? WHERE id = ?",
        (saved_amount, goal_id),
        is_select=False
    )

def delete_goal(goal_id):
    """Removes a goal from the database."""
    execute_query("DELETE FROM goals WHERE id = ?", (goal_id,), is_select=False)

def show_goals_page():
    user = get_current_user()
    if not user:
        st.warning("Please setup your profile first.")
        return
        
    st.markdown("## Savings Goal Tracker")
    
    members = get_family_members(user['id'])
    member_choices = {"Family (Combined)": None}
    for m in members:
        member_choices[m['name']] = m['id']
        
    tab1, tab2 = st.tabs(["🎯 Current Goals", "➕ Add New Goal"])
    
    with tab1:
        st.markdown("### Active Savings Goals")
        df = get_goals(user['id'])
        
        if df.empty:
            st.info("No savings goals defined yet. Go to 'Add New Goal' to create one.")
        else:
            # We display cards/progress bars for each goal
            for index, row in df.iterrows():
                target = row['target_amount']
                saved = row['saved_amount']
                monthly = row['monthly_contribution']
                deadline_str = row['deadline']
                
                # Math and projections
                pct = (saved / target * 100) if target > 0 else 0.0
                pct = min(100.0, pct)
                
                months_rem, projected_completion = calculate_projected_completion(target, saved, monthly)
                
                # Check target timeline vs projected
                try:
                    deadline_dt = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()
                    today = datetime.date.today()
                    
                    if saved >= target:
                        goal_status = "Completed"
                        status_color = "#10B981" # Green
                    elif monthly <= 0:
                        goal_status = "Unfunded"
                        status_color = "#EF4444" # Red
                    else:
                        # calculate how many months between today and deadline
                        months_to_deadline = (deadline_dt.year - today.year) * 12 + (deadline_dt.month - today.month)
                        if months_rem is not None and months_rem <= months_to_deadline:
                            goal_status = "On Track"
                            status_color = "#10B981"
                        else:
                            goal_status = "Delayed"
                            status_color = "#F59E0B" # Gold
                except Exception:
                    goal_status = "N/A"
                    status_color = "#94A3B8"
                
                col_c1, col_c2 = st.columns([4, 1])
                with col_c1:
                    st.markdown(
                        f"""
                        <div style="background-color: #1E293B; border-radius: 8px; padding: 20px; border-left: 5px solid {status_color}; margin-bottom: 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h4 style="margin: 0; color: #E2E8F0;">{row['name']} 
                                    <span style="font-size: 0.75rem; color: #94A3B8; background: #334155; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">{row['member_name']}</span>
                                </h4>
                                <span style="font-size: 0.75rem; color: {status_color}; background: {status_color}33; border: 1px solid {status_color}; padding: 2px 8px; border-radius: 4px; font-weight: bold;">{goal_status}</span>
                            </div>
                            <div style="margin-top: 10px; font-size: 0.85rem; color: #94A3B8;">
                                Target: <b>₹{target:,.2f}</b> &nbsp;|&nbsp; Saved: <b>₹{saved:,.2f}</b> &nbsp;|&nbsp; Monthly Contribution: <b>₹{monthly:,.2f}</b>
                            </div>
                            <div style="width: 100%; background: #334155; height: 10px; border-radius: 5px; margin-top: 12px; overflow: hidden;">
                                <div style="width: {pct}%; background: {status_color}; height: 100%; border-radius: 5px;"></div>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: #94A3B8; margin-top: 6px;">
                                <span>{pct:,.1f}% Saved</span>
                                <span>Deadline: {datetime.datetime.strptime(deadline_str, "%Y-%m-%d").strftime("%b %d, %Y")}</span>
                            </div>
                            <div style="font-size: 0.8rem; color: #CBD5E1; margin-top: 10px;">
                                📅 Projected Completion: <b>{projected_completion}</b> 
                                {f"({round(months_rem, 1) if months_rem else 0} months remaining)" if goal_status != 'Completed' and months_rem is not None else ""}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with col_c2:
                    st.write("")
                    st.write("")
                    # Update savings input
                    new_saved = st.number_input("Update Saved Amount (₹)", min_value=0.0, max_value=float(target), value=float(saved), key=f"save_amt_{row['id']}")
                    if new_saved != saved:
                        if st.button("Save", key=f"btn_save_{row['id']}", use_container_width=True):
                            update_goal_savings(row['id'], new_saved)
                            st.success("Updated savings!")
                            st.rerun()
                            
                    st.write("")
                    if st.button("Remove", key=f"btn_rem_{row['id']}", type="secondary", use_container_width=True):
                        delete_goal(row['id'])
                        st.success("Goal removed.")
                        st.rerun()
                        
    with tab2:
        st.markdown("### Define a New Goal")
        with st.form("new_goal_form", clear_on_submit=True):
            goal_cat = st.selectbox("Goal Category", options=["Education", "Home", "Vehicle", "Vacation", "Emergency", "Custom"])
            
            col1, col2 = st.columns(2)
            with col1:
                name_detail = st.text_input("Goal Details/Name", placeholder="E.g., Ravi's Master Degree, New SUV")
                target_amount = st.number_input("Target Amount (₹)", min_value=1.0, step=5000.0, format="%.2f")
                saved_amount = st.number_input("Initial Saved Amount (₹)", min_value=0.0, step=1000.0, format="%.2f")
            with col2:
                monthly_contribution = st.number_input("Monthly Savings Contribution (₹)", min_value=0.0, step=500.0, format="%.2f")
                deadline = st.date_input("Target Deadline Date", value=datetime.date.today() + datetime.timedelta(days=365))
                target_member = st.selectbox("Assign Goal To", options=list(member_choices.keys()))
                
            submitted = st.form_submit_form_button("Create Goal", type="primary")
            if submitted:
                if not name_detail.strip():
                    name_detail = goal_cat
                else:
                    name_detail = f"{goal_cat}: {name_detail.strip()}"
                    
                add_goal(
                    member_choices[target_member],
                    name_detail,
                    target_amount,
                    saved_amount,
                    monthly_contribution,
                    deadline.strftime("%Y-%m-%d")
                )
                st.success(f"Goal '{name_detail}' created successfully!")
                st.rerun()
