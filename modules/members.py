import streamlit as st
from utils.db import execute_query

def get_current_user():
    """Fetches the main user from the database."""
    users = execute_query("SELECT * FROM users LIMIT 1")
    return users[0] if users else None

def get_family_members(user_id):
    """Fetches all family members for the user, including the user themselves ('Self')."""
    return execute_query("SELECT * FROM members WHERE user_id = ?", (user_id,))

def register_user(name, age, mode, income):
    """Registers the main user and automatically adds them as a 'Self' member."""
    user_id = execute_query(
        "INSERT INTO users (name, age, mode, monthly_income) VALUES (?, ?, ?, ?)",
        (name, age, mode, income),
        is_select=False
    )
    # Add Self to members
    execute_query(
        "INSERT INTO members (user_id, name, age, relationship, monthly_income, is_dependent) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, age, 'Self', income, 0),
        is_select=False
    )
    # Initialize emergency fund record for the user
    execute_query(
        "INSERT INTO emergency_fund (user_id, current_amount) VALUES (?, 0.0)",
        (user_id,),
        is_select=False
    )
    return user_id

def add_family_member(user_id, name, age, relationship, income, is_dependent):
    """Adds a family member profile."""
    execute_query(
        "INSERT INTO members (user_id, name, age, relationship, monthly_income, is_dependent) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, age, relationship, income, 1 if is_dependent else 0),
        is_select=False
    )

def delete_family_member(member_id):
    """Deletes a family member profile. Cascade deletes transactions/goals etc."""
    execute_query("DELETE FROM members WHERE id = ?", (member_id,), is_select=False)

def show_member_setup_wizard():
    """Displays the first-time onboarding registration wizard."""
    st.markdown("<h1 style='text-align: center; color: #10B981;'>Welcome to Antigravity Finance</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.1rem; color: #94A3B8;'>Setup your personal or family profile to start tracking your finances.</p>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 1. Mode Selection
    mode = st.radio(
        "Select Application Mode",
        options=["Bachelor Mode", "Family Mode"],
        help="Bachelor Mode is simplified for individuals. Family Mode supports multiple members and relationships."
    )
    mode_str = "Bachelor" if mode == "Bachelor Mode" else "Family"
    
    st.markdown("### Primary User Profile")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full Name", value="", placeholder="Enter your name")
        income = st.number_input("Monthly Income (₹)", min_value=0.0, step=1000.0, format="%.2f")
    with col2:
        age = st.number_input("Age", min_value=1, max_value=120, value=25)
        
    # Validation
    if st.button("Complete Setup", type="primary", use_container_width=True):
        if not name.strip():
            st.error("Please enter a valid name.")
        else:
            register_user(name.strip(), age, mode_str, income)
            st.success("Registration successful! Refreshing...")
            st.rerun()

def show_member_management_page():
    """Displays the page to manage profiles and family members from the dashboard."""
    user = get_current_user()
    if not user:
        st.warning("User profile not found. Please complete setup.")
        return
        
    st.markdown(f"## Profile & Family Management ({user['mode']} Mode)")
    
    members = get_family_members(user['id'])
    
    # 1. Primary User Card
    st.markdown("### Primary Profile")
    with st.container():
        st.markdown(
            f"""
            <div style="background-color: #1E293B; border-radius: 10px; padding: 20px; border-left: 5px solid #10B981; margin-bottom: 20px;">
                <h4 style="margin: 0; color: #E2E8F0;">{user['name']} <span style="font-size: 0.8rem; color: #10B981; background: #064E3B; padding: 2px 8px; border-radius: 4px; margin-left: 8px;">Primary (Self)</span></h4>
                <p style="margin: 5px 0 0 0; color: #94A3B8;">Age: {user['age']} &nbsp;|&nbsp; Monthly Income: <b>₹{user['monthly_income']:,.2f}</b></p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    # 2. Family Members
    st.markdown("### Family Members & Dependents")
    other_members = [m for m in members if m['relationship'] != 'Self']
    
    if not other_members:
        st.info("No other family members added yet.")
    else:
        for m in other_members:
            dep_badge = "Dependent" if m['is_dependent'] == 1 else "Contributor"
            badge_color = "#F59E0B" if m['is_dependent'] == 1 else "#10B981"
            badge_bg = "#78350F" if m['is_dependent'] == 1 else "#064E3B"
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; border-radius: 10px; padding: 15px; border-left: 5px solid {badge_color}; margin-bottom: 10px;">
                        <h5 style="margin: 0; color: #E2E8F0;">{m['name']} 
                            <span style="font-size: 0.75rem; color: {badge_color}; background: {badge_bg}; padding: 2px 6px; border-radius: 4px; margin-left: 8px;">{m['relationship']}</span>
                            <span style="font-size: 0.75rem; color: #CBD5E1; background: #334155; padding: 2px 6px; border-radius: 4px; margin-left: 4px;">{dep_badge}</span>
                        </h5>
                        <p style="margin: 5px 0 0 0; color: #94A3B8;">Age: {m['age']} &nbsp;|&nbsp; Monthly Income: <b>₹{m['monthly_income']:,.2f}</b></p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            with col2:
                st.write("")
                # Add spacing to align vertically
                st.write("")
                if st.button("Delete", key=f"del_{m['id']}", type="secondary", use_container_width=True):
                    delete_family_member(m['id'])
                    st.success(f"Removed {m['name']}.")
                    st.rerun()

    # 3. Form to Add Member
    st.markdown("---")
    st.markdown("### Add New Profile")
    
    with st.form("add_member_form", clear_on_submit=True):
        name = st.text_input("Name", placeholder="Enter member name")
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=1, max_value=120, value=25)
            # Restrict relationships based on mode
            if user['mode'] == 'Bachelor':
                relationship_options = ["Dependent", "Other"]
            else:
                relationship_options = ["Spouse", "Child", "Parent", "Other"]
            relationship = st.selectbox("Relationship", options=relationship_options)
        with col2:
            income = st.number_input("Monthly Income (₹)", min_value=0.0, step=1000.0, format="%.2f")
            
            # For Bachelor mode, dependents are marked as optional / customizable.
            # Children are automatic dependents, spouse can be contributor/dependent, parent is usually dependent.
            is_dep = st.checkbox("Mark as Dependent", value=True, help="Check if this person relies on your income for their expenses.")
            
        submitted = st.form_submit_form_button("Add Member", type="primary")
        if submitted:
            if not name.strip():
                st.error("Please provide a name.")
            else:
                # Map relationship correctly for db
                rel_val = relationship
                if user['mode'] == 'Bachelor' and relationship == 'Dependent':
                    rel_val = 'Dependent'
                add_family_member(user['id'], name.strip(), age, rel_val, income, is_dep)
                st.success(f"Successfully added {name}!")
                st.rerun()
