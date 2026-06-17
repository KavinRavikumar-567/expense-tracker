import streamlit as st
import pandas as pd
import datetime
from utils.db import execute_query
from modules.members import get_current_user
from utils.calculations import calculate_emergency_fund_status

def get_actual_average_expenses(user_id):
    """Calculates the average monthly expenses from the transactions database."""
    query = """
        SELECT STRFTIME('%Y-%m', t.date) as month_val, SUM(t.amount) as total_expense
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        WHERE m.user_id = ? AND t.type = 'Expense'
        GROUP BY month_val
    """
    rows = execute_query(query, (user_id,))
    if not rows:
        return 0.0
    
    # Calculate simple average of all active months
    sums = [r['total_expense'] for r in rows]
    return sum(sums) / len(sums)

def get_emergency_fund(user_id):
    """Fetches the emergency fund current amount for the user."""
    row = execute_query("SELECT current_amount FROM emergency_fund WHERE user_id = ? LIMIT 1", (user_id,))
    return row[0]['current_amount'] if row else 0.0

def update_emergency_fund(user_id, current_amount):
    """Updates the emergency fund current amount in the database."""
    execute_query(
        "UPDATE emergency_fund SET current_amount = ?, last_updated = CURRENT_TIMESTAMP WHERE user_id = ?",
        (current_amount, user_id),
        is_select=False
    )

def show_emergency_page():
    user = get_current_user()
    if not user:
        st.warning("Please setup your profile first.")
        return
        
    st.markdown("## Emergency Fund Tracker")
    
    # 1. Fetch current data
    current_fund = get_emergency_fund(user['id'])
    actual_avg = get_actual_average_expenses(user['id'])
    
    # Fallback to estimated monthly expenses if no transaction history
    st.markdown("### Expense Settings")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        if actual_avg > 0:
            st.info(f"📈 Verified monthly average expense (from transactions): **₹{actual_avg:,.2f}**")
            monthly_exp_val = actual_avg
        else:
            st.info("💡 No transaction history found yet. Using estimated monthly expenses.")
            # Default to 50% of monthly income, or 25,000 if income is 0
            default_est = user['monthly_income'] * 0.5 if user['monthly_income'] > 0 else 25000.0
            monthly_exp_val = default_est
            
        est_expenses = st.number_input(
            "Monthly Expense Estimate (₹)", 
            min_value=1.0, 
            value=float(monthly_exp_val), 
            step=1000.0,
            help="This value serves as the base for calculating your target emergency fund (3x for Bachelor / 6x for Family)."
        )
    with col_e2:
        # Update Emergency Fund Amount Input
        new_fund = st.number_input(
            "Current Emergency Fund Balance (₹)",
            min_value=0.0,
            value=float(current_fund),
            step=1000.0,
            help="Enter the amount you currently have parked in liquid savings/FDs dedicated to emergencies."
        )
        if st.button("Update Balance", type="primary", use_container_width=True):
            update_emergency_fund(user['id'], new_fund)
            st.success("Emergency fund balance updated successfully!")
            st.rerun()
            
    # 2. Status Calculation
    calc_results = calculate_emergency_fund_status(new_fund, est_expenses, user['mode'])
    
    target = calc_results['target_amount']
    gap = calc_results['gap']
    ratio = calc_results['ratio']
    status = calc_results['status']
    top_up_12m = calc_results['top_up_suggestion_12m']
    
    # Set status badge color
    if status == "Healthy":
        status_color = "#10B981"
        badge_bg = "#064E3B"
    elif status == "Building":
        status_color = "#F59E0B"
        badge_bg = "#78350F"
    else:
        status_color = "#EF4444"
        badge_bg = "#7A1515"
        
    st.markdown("---")
    st.markdown("### Fund Health Analysis")
    
    # KPI Grid
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid #94A3B8;">
                <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Target Amount ({'3x' if user['mode'] == 'Bachelor' else '6x'})</span>
                <h3 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{target:,.2f}</h3>
            </div>
            """, unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid #10B981;">
                <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Current Balance</span>
                <h3 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{new_fund:,.2f}</h3>
            </div>
            """, unsafe_allow_html=True
        )
    with col3:
        gap_color = "#10B981" if gap == 0 else "#EF4444"
        st.markdown(
            f"""
            <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid {gap_color};">
                <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Deficit / Gap</span>
                <h3 style="margin: 5px 0 0 0; color: {gap_color};">₹{gap:,.2f}</h3>
            </div>
            """, unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f"""
            <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid {status_color};">
                <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Status ({ratio:,.1f}x)</span>
                <h3 style="margin: 5px 0 0 0; color: {status_color};">{status}</h3>
            </div>
            """, unsafe_allow_html=True
        )
        
    # Visual Progress Bar
    pct = min(100.0, (new_fund / target * 100.0) if target > 0 else 0.0)
    st.markdown(
        f"""
        <div style="width: 100%; background: #334155; height: 20px; border-radius: 10px; margin-top: 20px; overflow: hidden; position: relative;">
            <div style="width: {pct}%; background: {status_color}; height: 100%; border-radius: 10px;"></div>
            <div style="position: absolute; width: 100%; text-align: center; top: 0; left: 0; line-height: 20px; font-size: 0.8rem; font-weight: bold; color: #FFFFFF;">
                {pct:,.1f}% of target reached
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 3. Monthly Suggestions Box
    st.markdown("### Top-up Recommendations")
    if gap <= 0:
        st.success("🎉 Your emergency fund is fully funded! No monthly top-ups are required. Excellent job securing your finances.")
    else:
        st.warning(f"⚠️ You are short by **₹{gap:,.2f}** to achieve a secure emergency buffer.")
        
        # Calculate for 6, 12, 24 months
        top_6m = gap / 6.0
        top_12m = gap / 12.0
        top_24m = gap / 24.0
        
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown(
                f"""
                <div style="background-color: #1E293B; border-radius: 6px; padding: 15px; border-top: 4px solid #EF4444; text-align: center;">
                    <span style="font-size: 0.8rem; color: #94A3B8;">Reach in 6 Months</span>
                    <h4 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{top_6m:,.2f} <span style="font-size: 0.7rem; color: #94A3B8;">/mo</span></h4>
                </div>
                """, unsafe_allow_html=True
            )
        with col_s2:
            st.markdown(
                f"""
                <div style="background-color: #1E293B; border-radius: 6px; padding: 15px; border-top: 4px solid #F59E0B; text-align: center;">
                    <span style="font-size: 0.8rem; color: #94A3B8;">Reach in 12 Months</span>
                    <h4 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{top_12m:,.2f} <span style="font-size: 0.7rem; color: #94A3B8;">/mo</span></h4>
                </div>
                """, unsafe_allow_html=True
            )
        with col_s3:
            st.markdown(
                f"""
                <div style="background-color: #1E293B; border-radius: 6px; padding: 15px; border-top: 4px solid #10B981; text-align: center;">
                    <span style="font-size: 0.8rem; color: #94A3B8;">Reach in 24 Months</span>
                    <h4 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{top_24m:,.2f} <span style="font-size: 0.7rem; color: #94A3B8;">/mo</span></h4>
                </div>
                """, unsafe_allow_html=True
            )
            
        st.markdown(
            f"""
            <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; border-left: 5px solid #F59E0B; margin-top: 15px;">
                💡 <b>Smart Recommendation</b>: Set aside a standing instruction of <b>₹{top_12m:,.2f}</b> each month. 
                This will comfortably cover your target in 1 year without stretching your monthly cash flows.
            </div>
            """,
            unsafe_allow_html=True
        )
