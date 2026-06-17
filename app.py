import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# Page configuration
st.set_page_config(
    page_title="Antigravity Family Finance Manager",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injections for global look and feel
st.markdown(
    """
    <style>
    /* Global Styles */
    .stApp {
        background-color: #0F172A;
        color: #E2E8F0;
    }
    
    /* Sidebar styling override */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }
    section[data-testid="stSidebar"] * {
        color: #E2E8F0 !important;
    }
    
    /* Input and Selectbox borders styling */
    div[data-baseweb="select"] {
        border-color: #334155 !important;
    }
    
    /* Cards styling */
    .dashboard-card {
        background-color: #1E293B;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    /* Tabs custom styling */
    button[data-baseweb="tab"] {
        color: #94A3B8 !important;
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #10B981 !important;
        border-color: #10B981 !important;
    }
    
    /* Alert details customization */
    .alert-card {
        background-color: #1E293B;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 10px;
        border-left: 4px solid #10B981;
    }
    
    /* Hide Deploy buttons and default Streamlit header/footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

from utils.db import init_db, execute_query
from modules.members import get_current_user, show_member_setup_wizard, show_member_management_page, get_family_members
from modules.tracker import show_tracker_page, get_transactions_df
from modules.budget import show_budget_page, get_budgets, get_actual_expenses
from modules.goals import show_goals_page, get_goals
from modules.investments import show_investments_page, get_investments
from modules.insurance import show_insurance_page, get_insurance
from modules.emergency import show_emergency_page, get_emergency_fund, get_actual_average_expenses
from modules.insights import generate_smart_insights
from utils.calculations import calculate_emergency_fund_status, calculate_cagr

def show_dashboard(user):
    st.markdown(f"## Welcome back, {user['name']}!")
    st.markdown(f"<p style='color:#94A3B8;'>Here is your {user['mode']}-level financial overview for this month.</p>", unsafe_allow_html=True)
    
    today = datetime.date.today()
    current_month_str = today.strftime("%Y-%m")
    
    # 1. Fetch data
    members = get_family_members(user['id'])
    tx_df = get_transactions_df(user['id'])
    budgets_df = get_budgets(user['id'], current_month_str)
    goals_df = get_goals(user['id'])
    inv_df = get_investments(user['id'])
    ins_df = get_insurance(user['id'])
    
    # Emergency Fund metrics
    current_ef = get_emergency_fund(user['id'])
    avg_exp = get_actual_average_expenses(user['id'])
    if avg_exp <= 0:
        # fallback
        avg_exp = user['monthly_income'] * 0.5 if user['monthly_income'] > 0 else 25000.0
    ef_stats = calculate_emergency_fund_status(current_ef, avg_exp, user['mode'])
    
    # Income/Expenses current month
    tx_this_month = pd.DataFrame()
    if not tx_df.empty:
        tx_df['month'] = pd.to_datetime(tx_df['date']).dt.strftime('%Y-%m')
        tx_this_month = tx_df[tx_df['month'] == current_month_str]
        
    inc_val = tx_this_month[tx_this_month['type'] == 'Income']['amount'].sum() if not tx_this_month.empty else 0.0
    exp_val = tx_this_month[tx_this_month['type'] == 'Expense']['amount'].sum() if not tx_this_month.empty else 0.0
    net_savings = inc_val - exp_val
    
    # Budget status count
    budget_status_summary = "No budgets defined"
    if not budgets_df.empty:
        actual_exp_df = get_actual_expenses(user['id'], current_month_str)
        safe_count = 0
        warning_count = 0
        over_count = 0
        categories_list = ["Food", "Rent", "EMI", "Education", "Medical", "Travel", "Entertainment", "Utilities", "Other"]
        for cat in categories_list:
            cat_budgets = budgets_df[budgets_df['category'] == cat]
            family_wide = cat_budgets[cat_budgets['member_id'].isnull()]
            limit = family_wide['limit_amount'].sum() if not family_wide.empty else cat_budgets['limit_amount'].sum()
            actual = actual_exp_df[actual_exp_df['category'] == cat]['actual_amount'].sum()
            
            if limit > 0:
                pct = (actual / limit) * 100
                if pct < 80:
                    safe_count += 1
                elif pct <= 100:
                    warning_count += 1
                else:
                    over_count += 1
        budget_status_summary = f"{safe_count} Safe | {warning_count} Near Limit | {over_count} Over Budget"
        
    # Investment metrics
    inv_total_invested = inv_df['invested_amount'].sum() if not inv_df.empty else 0.0
    inv_total_current = inv_df['current_value'].sum() if not inv_df.empty else 0.0
    inv_abs_returns = inv_total_current - inv_total_invested
    
    # 2. Main KPI Grid
    st.markdown("### Monthly Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class="dashboard-card" style="border-left: 5px solid #10B981;">
                <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Family Income vs Expense</span>
                <h3 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{inc_val:,.2f} <span style="font-size:0.9rem; color:#94A3B8;">/ ₹{exp_val:,.2f}</span></h3>
                <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #94A3B8;">This Month ({today.strftime('%b %Y')})</p>
            </div>
            """, unsafe_allow_html=True
        )
    with col2:
        net_color = "#10B981" if net_savings >= 0 else "#EF4444"
        st.markdown(
            f"""
            <div class="dashboard-card" style="border-left: 5px solid {net_color};">
                <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Net Savings</span>
                <h3 style="margin: 5px 0 0 0; color: {net_color};">₹{net_savings:,.2f}</h3>
                <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #94A3B8;">Cash surplus after expenses</p>
            </div>
            """, unsafe_allow_html=True
        )
    with col3:
        # Emergency status colors
        ef_color = "#10B981" if ef_stats['status'] == 'Healthy' else ("#F59E0B" if ef_stats['status'] == 'Building' else "#EF4444")
        st.markdown(
            f"""
            <div class="dashboard-card" style="border-left: 5px solid {ef_color};">
                <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Emergency Fund Balance</span>
                <h3 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{current_ef:,.2f} <span style="font-size:0.8rem; color:{ef_color};">({ef_stats['status']})</span></h3>
                <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #94A3B8;">Multiplier: {ef_stats['ratio']:.1f}x monthly expenses</p>
            </div>
            """, unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f"""
            <div class="dashboard-card" style="border-left: 5px solid #F59E0B;">
                <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Investment Summary</span>
                <h3 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{inv_total_current:,.2f}</h3>
                <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #10B981;">Gain/Loss: ₹{inv_abs_returns:+,.2f}</p>
            </div>
            """, unsafe_allow_html=True
        )
        
    # 3. Two Column Layout for Insights & Budget/Goals
    col_left, col_right = st.columns([5, 4])
    
    with col_left:
        # Insights Panel
        st.markdown("### 🧠 Smart Insights & Alerts")
        insights = generate_smart_insights(user['id'])
        
        if not insights:
            st.info("No insights generated yet. Record transactions, set budgets, or add insurance policies to see smart insights.")
        else:
            for item in insights:
                # Color code left borders
                level_border = "#10B981" # default green
                if item['level'] == "Critical":
                    level_border = "#EF4444" # red
                elif item['level'] == "Warning":
                    level_border = "#F59E0B" # yellow/gold
                elif item['level'] == "Info":
                    level_border = "#3B82F6" # blue
                    
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 12px 18px; margin-bottom: 10px; border-left: 4px solid {level_border}; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155;">
                        <span style="font-size: 0.75rem; color: {level_border}; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px;">{item['category']}</span>
                        <div style="margin-top: 4px; font-size: 0.92rem; color: #E2E8F0;">{item['message']}</div>
                    </div>
                    """, unsafe_allow_html=True
                )
                
    with col_right:
        # Budget & Savings Overview
        st.markdown("### 📊 Budget Status")
        st.markdown(
            f"""
            <div class="dashboard-card" style="border-left: 4px solid #3B82F6;">
                <h5 style="margin: 0; color: #E2E8F0;">Monthly Budget Progress</h5>
                <p style="margin: 5px 0 10px 0; color: #94A3B8; font-size: 0.85rem;">{budget_status_summary}</p>
            </div>
            """, unsafe_allow_html=True
        )
        
        # Savings Goals summary
        st.markdown("### 🎯 Goals Progress Summary")
        if goals_df.empty:
            st.info("No savings goals defined.")
        else:
            for index, row in goals_df.iterrows():
                target = row['target_amount']
                saved = row['saved_amount']
                pct = min(100.0, (saved / target * 100) if target > 0 else 0.0)
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; padding: 12px; border-radius: 6px; margin-bottom: 8px; border: 1px solid #334155;">
                        <div style="display:flex; justify-content:space-between; font-size: 0.85rem; font-weight: bold;">
                            <span style="color:#E2E8F0;">{row['name']}</span>
                            <span style="color:#10B981;">{pct:,.1f}%</span>
                        </div>
                        <div style="width: 100%; background: #334155; height: 6px; border-radius: 3px; margin-top: 6px; overflow:hidden;">
                            <div style="width: {pct}%; background: #10B981; height: 100%; border-radius: 3px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )
                
    # 4. Income vs Expense Trend Chart (Family total)
    st.markdown("---")
    st.markdown("### 📊 Financial Year Trends")
    if not tx_df.empty:
        # Group by month and type
        trend_data = tx_df.groupby(['month', 'type'])['amount'].sum().reset_index()
        fig = px.line(
            trend_data, 
            x='month', 
            y='amount', 
            color='type',
            markers=True,
            color_discrete_map={'Income': '#10B981', 'Expense': '#EF4444'},
            template="plotly_dark",
            labels={'amount': 'Amount (₹)', 'month': 'Month'}
        )
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transaction data available to render the financial trend lines.")

def main():
    # Initialize DB tables
    init_db()
    
    # Onboard check
    user = get_current_user()
    if not user:
        show_member_setup_wizard()
        return
        
    # Navigation Sidebar
    st.sidebar.markdown(
        f"""
        <div style='text-align: center; margin-bottom: 20px;'>
            <h2 style='margin:0; color:#10B981;'>Antigravity</h2>
            <span style='font-size:0.8rem; color:#94A3B8;'>{user['name']} ({user['mode']} Mode)</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Navigation",
        options=[
            "🏠 Dashboard",
            "👥 Members & Profiles",
            "💸 Transaction Tracker",
            "📊 Budget Planner",
            "🎯 Savings Goals",
            "💼 Investments Portfolio",
            "🛡️ Insurance Policies",
            "🚨 Emergency Fund"
        ]
    )
    
    st.sidebar.markdown("---")
    
    # System Date Display
    st.sidebar.markdown(
        f"""
        <div style='font-size:0.75rem; color:#94A3B8; text-align:center;'>
            📅 Today's Date: {datetime.date.today().strftime('%b %d, %Y')}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Page Router
    if page == "🏠 Dashboard":
        show_dashboard(user)
    elif page == "👥 Members & Profiles":
        show_member_management_page()
    elif page == "💸 Transaction Tracker":
        show_tracker_page()
    elif page == "📊 Budget Planner":
        show_budget_page()
    elif page == "🎯 Savings Goals":
        show_goals_page()
    elif page == "💼 Investments Portfolio":
        show_investments_page()
    elif page == "🛡️ Insurance Policies":
        show_insurance_page()
    elif page == "🚨 Emergency Fund":
        show_emergency_page()

if __name__ == "__main__":
    main()
