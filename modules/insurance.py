import streamlit as st
import pandas as pd
import datetime
from utils.db import execute_query
from modules.members import get_current_user, get_family_members
from utils.calculations import analyze_insurance_gaps

INSURANCE_TYPES = ["Life", "Health", "Term", "Vehicle", "Home"]

def get_insurance(user_id):
    """Fetches all active insurance policies for the user, joined with member details."""
    query = """
        SELECT i.*, m.name as member_name
        FROM insurance i
        JOIN members m ON i.member_id = m.id
        WHERE m.user_id = ?
    """
    rows = execute_query(query, (user_id,))
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        'id', 'member_id', 'type', 'provider', 'premium', 'sum_assured', 'renewal_date', 'member_name'
    ])

def add_insurance(member_id, ins_type, provider, premium, sum_assured, renewal_date):
    """Adds a new insurance policy to the database."""
    execute_query(
        """
        INSERT INTO insurance (member_id, type, provider, premium, sum_assured, renewal_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (member_id, ins_type, provider, premium, sum_assured, renewal_date),
        is_select=False
    )

def delete_insurance(ins_id):
    """Removes an insurance policy."""
    execute_query("DELETE FROM insurance WHERE id = ?", (ins_id,), is_select=False)

def show_insurance_page():
    user = get_current_user()
    if not user:
        st.warning("Please setup your profile first.")
        return
        
    st.markdown("## Insurance Manager")
    
    members = get_family_members(user['id'])
    member_options = {m['name']: m['id'] for m in members}
    
    # Check if user has kids
    has_kids = any(m['relationship'] == 'Child' for m in members)
    
    tab1, tab2 = st.tabs(["🛡️ Coverage & Alerts", "➕ Add Policy"])
    
    with tab1:
        st.markdown("### Active Policies & Risk Analysis")
        df = get_insurance(user['id'])
        
        # 1. Coverage Gap & Risk Engine Analysis
        st.markdown("#### Gap Analysis & Nudges")
        policies_list = df.to_dict('records') if not df.empty else []
        alerts = analyze_insurance_gaps(policies_list, members, has_kids)
        
        if not alerts:
            st.success("All critical insurance profiles look good! Make sure coverage amounts are adequate.")
        else:
            for alert in alerts:
                if alert['level'] == "Critical" or alert['level'] == "High Risk":
                    st.error(f"🔴 **{alert['level']}**: {alert['message']}")
                elif alert['level'] == "Warning":
                    st.warning(f"⚠️ **{alert['level']}**: {alert['message']}")
                else:
                    st.info(f"ℹ️ **Info**: {alert['message']}")
                    
        # 2. Renewal Alerts
        st.markdown("#### Renewal Alerts (Next 30 Days)")
        renewals_found = False
        today = datetime.date.today()
        
        if not df.empty:
            for index, row in df.iterrows():
                try:
                    renewal_dt = datetime.datetime.strptime(row['renewal_date'], "%Y-%m-%d").date()
                    days_diff = (renewal_dt - today).days
                    
                    if 0 <= days_diff <= 30:
                        renewals_found = True
                        st.markdown(
                            f"""
                            <div style="background-color: #78350F; border: 1px solid #F59E0B; border-radius: 6px; padding: 12px; margin-bottom: 10px; color: #FEE2E2;">
                                ⚠️ Policy <b>{row['name']}</b> ({row['type']} - {row['provider']}) is due for renewal in <b>{days_diff} days</b> ({row['renewal_date']}).
                                <br>Premium: ₹{row['premium']:,.2f}
                            </div>
                            """, unsafe_allow_html=True
                        )
                    elif days_diff < 0:
                        renewals_found = True
                        st.markdown(
                            f"""
                            <div style="background-color: #991B1B; border: 1px solid #EF4444; border-radius: 6px; padding: 12px; margin-bottom: 10px; color: #FEE2E2;">
                                🚨 Policy <b>{row['name']}</b> ({row['type']} - {row['provider']}) has <b>EXPIRED</b> by {-days_diff} days ({row['renewal_date']}).
                                <br>Premium: ₹{row['premium']:,.2f}
                            </div>
                            """, unsafe_allow_html=True
                        )
                except Exception:
                    pass
                    
        if not renewals_found:
            st.info("No policy renewals due within the next 30 days.")
            
        # 3. Family Coverage Table
        st.markdown("#### Active Coverage Summary")
        if df.empty:
            st.info("No active insurance policies found.")
        else:
            disp_df = df[['member_name', 'type', 'provider', 'premium', 'sum_assured', 'renewal_date', 'id']].copy()
            disp_df.columns = ["Member", "Policy Type", "Provider", "Premium (₹)", "Sum Assured (₹)", "Renewal Date", "id"]
            
            st.dataframe(
                disp_df[["Member", "Policy Type", "Provider", "Premium (₹)", "Sum Assured (₹)", "Renewal Date"]].style.format({
                    "Premium (₹)": "₹{:,.2f}",
                    "Sum Assured (₹)": "₹{:,.2f}"
                }),
                use_container_width=True
            )
            
            # Deletion Manager
            st.markdown("#### Delete Policies")
            to_delete = st.selectbox(
                "Select Policy to Remove",
                options=df.apply(lambda r: f"ID {r['id']} | {r['member_name']} | {r['type']} ({r['provider']}) | Sum Assured: ₹{r['sum_assured']}", axis=1),
                index=None,
                placeholder="Choose a policy to delete..."
            )
            if to_delete:
                ins_id = int(to_delete.split(" | ")[0].replace("ID ", ""))
                if st.button("Delete Policy Record", type="secondary"):
                    delete_insurance(ins_id)
                    st.success("Policy record deleted successfully.")
                    st.rerun()
                    
    with tab2:
        st.markdown("### Add New Insurance Policy")
        with st.form("add_policy_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                target_member = st.selectbox("Policy Holder (Member)", options=list(member_options.keys()))
                ins_type = st.selectbox("Policy Type", options=INSURANCE_TYPES)
                provider = st.text_input("Insurance Provider", placeholder="E.g., LIC, HDFC Ergo, Max Life, ICICI Lombard")
            with col2:
                premium = st.number_input("Annual Premium (₹)", min_value=0.0, step=500.0, format="%.2f")
                sum_assured = st.number_input("Sum Assured / Coverage (₹)", min_value=0.0, step=5000.0, format="%.2f")
                renewal_date = st.date_input("Renewal Due Date", value=datetime.date.today() + datetime.timedelta(days=365))
                
            submitted = st.form_submit_form_button("Add Insurance Policy", type="primary")
            if submitted:
                if not provider.strip():
                    st.error("Please enter a provider name.")
                elif premium <= 0 or sum_assured <= 0:
                    st.error("Please enter premium and sum assured values.")
                else:
                    add_insurance(
                        member_options[target_member],
                        ins_type,
                        provider.strip(),
                        premium,
                        sum_assured,
                        renewal_date.strftime("%Y-%m-%d")
                    )
                    st.success(f"Added policy with {provider} for {target_member}!")
                    st.rerun()
