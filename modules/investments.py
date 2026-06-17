import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
from utils.db import execute_query
from modules.members import get_current_user, get_family_members
from utils.calculations import calculate_cagr

INVESTMENT_TYPES = ["MF", "SIP", "FD", "PPF", "Stocks", "Gold", "RD"]

def get_investments(user_id):
    """Fetches all investments for the user, joined with member details."""
    query = """
        SELECT i.*, m.name as member_name
        FROM investments i
        JOIN members m ON i.member_id = m.id
        WHERE m.user_id = ?
    """
    rows = execute_query(query, (user_id,))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        'id', 'member_id', 'type', 'name', 'invested_amount', 'current_value', 'start_date', 'member_name'
    ])

def add_investment(member_id, inv_type, name, invested_amount, current_value, start_date):
    """Adds a new investment record to the database."""
    execute_query(
        """
        INSERT INTO investments (member_id, type, name, invested_amount, current_value, start_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (member_id, inv_type, name, invested_amount, current_value, start_date),
        is_select=False
    )

def update_current_value(inv_id, current_value):
    """Updates the current valuation of an asset."""
    execute_query(
        "UPDATE investments SET current_value = ? WHERE id = ?",
        (current_value, inv_id),
        is_select=False
    )

def delete_investment(inv_id):
    """Removes an investment record."""
    execute_query("DELETE FROM investments WHERE id = ?", (inv_id,), is_select=False)

def show_investments_page():
    user = get_current_user()
    if not user:
        st.warning("Please setup your profile first.")
        return
        
    st.markdown("## Investment Portfolio Tracker")
    
    members = get_family_members(user['id'])
    member_options = {m['name']: m['id'] for m in members}
    
    tab1, tab2 = st.tabs(["💼 Portfolio Summary & Logs", "➕ Add Investment"])
    
    with tab1:
        df = get_investments(user['id'])
        if df.empty:
            st.info("No investments recorded yet. Go to the 'Add Investment' tab to get started.")
        else:
            # Calculate CAGR for each row
            df['CAGR (%)'] = df.apply(lambda r: calculate_cagr(r['invested_amount'], r['current_value'], r['start_date']), axis=1)
            df['Returns (₹)'] = df['current_value'] - df['invested_amount']
            df['ROI (%)'] = df.apply(lambda r: round((r['Returns (₹)'] / r['invested_amount'] * 100), 2) if r['invested_amount'] > 0 else 0.0, axis=1)
            
            # KPI Tiles
            total_invested = df['invested_amount'].sum()
            total_current = df['current_value'].sum()
            total_returns = total_current - total_invested
            total_roi = (total_returns / total_invested * 100) if total_invested > 0 else 0.0
            
            # Weighted CAGR calculation
            valid_cagr_df = df[df['CAGR (%)'] > 0]
            if not valid_cagr_df.empty:
                weighted_cagr = (valid_cagr_df['CAGR (%)'] * valid_cagr_df['invested_amount']).sum() / valid_cagr_df['invested_amount'].sum()
            else:
                weighted_cagr = 0.0
                
            c_k1, c_k2, c_k3, c_k4 = st.columns(4)
            with c_k1:
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid #94A3B8;">
                        <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Total Invested</span>
                        <h3 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{total_invested:,.2f}</h3>
                    </div>
                    """, unsafe_allow_html=True
                )
            with c_k2:
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid #10B981;">
                        <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Current Value</span>
                        <h3 style="margin: 5px 0 0 0; color: #E2E8F0;">₹{total_current:,.2f}</h3>
                    </div>
                    """, unsafe_allow_html=True
                )
            with c_k3:
                ret_color = "#10B981" if total_returns >= 0 else "#EF4444"
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid {ret_color};">
                        <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Total Returns</span>
                        <h3 style="margin: 5px 0 0 0; color: {ret_color};">₹{total_returns:,.2f} ({total_roi:,.2f}%)</h3>
                    </div>
                    """, unsafe_allow_html=True
                )
            with c_k4:
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border-radius: 8px; padding: 15px; text-align: center; border-bottom: 4px solid #F59E0B;">
                        <span style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase;">Weighted CAGR</span>
                        <h3 style="margin: 5px 0 0 0; color: #F59E0B;">{weighted_cagr:,.2f}%</h3>
                    </div>
                    """, unsafe_allow_html=True
                )
                
            # Layout: Pie Charts side by side
            st.markdown("### Allocation Breakdown")
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                st.markdown("#### Allocation by Asset Type")
                type_df = df.groupby('type')['current_value'].sum().reset_index()
                fig_type = px.pie(
                    type_df, 
                    values='current_value', 
                    names='type', 
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_type.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_type, use_container_width=True)
                
            with col_chart2:
                st.markdown("#### Allocation by Family Member")
                member_df = df.groupby('member_name')['current_value'].sum().reset_index()
                fig_member = px.pie(
                    member_df, 
                    values='current_value', 
                    names='member_name', 
                    template="plotly_dark",
                    color_discrete_sequence=px.colors.qualitative.Safe
                )
                fig_member.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_member, use_container_width=True)
                
            # Returns Summary Table
            st.markdown("### Asset Holdings & Performance")
            
            disp_df = df[['member_name', 'type', 'name', 'invested_amount', 'current_value', 'Returns (₹)', 'ROI (%)', 'CAGR (%)', 'start_date']].copy()
            disp_df.columns = ["Member", "Asset Type", "Name", "Invested (₹)", "Current Value (₹)", "Returns (₹)", "ROI (%)", "CAGR (%)", "Start Date"]
            
            def highlight_roi(val):
                return 'color: #10B981;' if val > 0 else ('color: #EF4444;' if val < 0 else '')
                
            st.dataframe(
                disp_df.style.format({
                    "Invested (₹)": "₹{:,.2f}",
                    "Current Value (₹)": "₹{:,.2f}",
                    "Returns (₹)": "₹{:,.2f}",
                    "ROI (%)": "{:,.2f}%",
                    "CAGR (%)": "{:,.2f}%"
                }).map(highlight_roi, subset=["Returns (₹)", "ROI (%)", "CAGR (%)"]),
                use_container_width=True
            )
            
            # Management Section
            st.markdown("#### Update / Remove Investments")
            col_m1, col_m2 = st.columns(2)
            
            with col_m1:
                inv_to_update = st.selectbox(
                    "Select Asset to Update Value",
                    options=df.apply(lambda r: f"ID {r['id']} | {r['name']} ({r['type']}) | Current: ₹{r['current_value']}", axis=1),
                    index=None,
                    placeholder="Choose an asset..."
                )
                if inv_to_update:
                    inv_id = int(inv_to_update.split(" | ")[0].replace("ID ", ""))
                    current_inv = df[df['id'] == inv_id].iloc[0]
                    new_val = st.number_input("New Current Value (₹)", min_value=0.0, value=float(current_inv['current_value']))
                    if st.button("Update Valuation", key="btn_upd_val"):
                        update_current_value(inv_id, new_val)
                        st.success("Valuation updated successfully!")
                        st.rerun()
                        
            with col_m2:
                inv_to_del = st.selectbox(
                    "Select Asset to Remove",
                    options=df.apply(lambda r: f"ID {r['id']} | {r['name']} ({r['type']})", axis=1),
                    index=None,
                    placeholder="Choose an asset to delete..."
                )
                if inv_to_del:
                    inv_id = int(inv_to_del.split(" | ")[0].replace("ID ", ""))
                    if st.button("Delete Asset Record", type="secondary"):
                        delete_investment(inv_id)
                        st.success("Asset record removed.")
                        st.rerun()

    with tab2:
        st.markdown("### Record New Asset Holding")
        with st.form("add_investment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                target_member = st.selectbox("Owner / Assigned Member", options=list(member_options.keys()))
                inv_type = st.selectbox("Asset Type", options=INVESTMENT_TYPES)
                name = st.text_input("Asset Name", placeholder="E.g., SBI Bluechip Mutual Fund, Gold SIP, Apple Stocks")
            with col2:
                invested = st.number_input("Invested Amount (₹)", min_value=0.01, step=1000.0, format="%.2f")
                current = st.number_input("Current Value (₹)", min_value=0.0, step=1000.0, format="%.2f")
                start_date = st.date_input("Start Date / Purchase Date", value=datetime.date.today() - datetime.timedelta(days=365))
                
            submitted = st.form_submit_form_button("Add Asset Holding", type="primary")
            if submitted:
                if not name.strip():
                    st.error("Please provide an asset name.")
                elif current <= 0:
                    st.error("Please enter a current valuation.")
                else:
                    add_investment(
                        member_options[target_member],
                        inv_type,
                        name.strip(),
                        invested,
                        current,
                        start_date.strftime("%Y-%m-%d")
                    )
                    st.success(f"Added holding '{name}' successfully.")
                    st.rerun()
