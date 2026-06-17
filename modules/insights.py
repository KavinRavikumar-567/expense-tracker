import datetime
import pandas as pd
from utils.db import execute_query
from utils.calculations import calculate_cagr, calculate_projected_completion, calculate_emergency_fund_status, analyze_insurance_gaps

def generate_smart_insights(user_id):
    """
    Scans the database and returns a list of dynamic alert dictionaries.
    Each alert: { "level": "Critical" | "Warning" | "Info" | "Success", "message": str, "category": str }
    """
    insights = []
    today = datetime.date.today()
    current_month_str = today.strftime("%Y-%m")
    
    # 1. Fetch User details
    users = execute_query("SELECT * FROM users WHERE id = ?", (user_id,))
    if not users:
        return []
    user = users[0]
    
    # 2. Fetch Members
    members = execute_query("SELECT * FROM members WHERE user_id = ?", (user_id,))
    has_kids = any(m['relationship'] == 'Child' for m in members)
    
    # 3. EMERGENCY FUND INSIGHTS
    # Get current emergency fund balance
    ef_row = execute_query("SELECT current_amount FROM emergency_fund WHERE user_id = ? LIMIT 1", (user_id,))
    current_ef = ef_row[0]['current_amount'] if ef_row else 0.0
    
    # Calculate average monthly expenses
    exp_query = """
        SELECT SUM(amount) as total_expense
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        WHERE m.user_id = ? AND t.type = 'Expense'
        GROUP BY STRFTIME('%Y-%m', t.date)
    """
    exp_rows = execute_query(exp_query, (user_id,))
    if exp_rows:
        monthly_exp = sum([r['total_expense'] for r in exp_rows]) / len(exp_rows)
    else:
        # Fallback to estimated expenses: 50% of income or 25,000
        monthly_exp = user['monthly_income'] * 0.5 if user['monthly_income'] > 0 else 25000.0
        
    ef_stats = calculate_emergency_fund_status(current_ef, monthly_exp, user['mode'])
    target_mult = 3 if user['mode'] == 'Bachelor' else 6
    
    if ef_stats['ratio'] < target_mult:
        if ef_stats['ratio'] < 2.0:
            insights.append({
                "level": "Critical",
                "category": "Emergency Fund",
                "message": f"Emergency fund covers only {ef_stats['ratio']:.1f} months of expenses — top up ₹{ef_stats['top_up_suggestion_12m']:,.2f}/month."
            })
        else:
            insights.append({
                "level": "Warning",
                "category": "Emergency Fund",
                "message": f"Emergency fund is at {ef_stats['ratio']:.1f}x (Target: {target_mult}x) — top up ₹{ef_stats['top_up_suggestion_12m']:,.2f}/month to bridge the ₹{ef_stats['gap']:,.2f} gap."
            })
    else:
        insights.append({
            "level": "Success",
            "category": "Emergency Fund",
            "message": f"Your emergency fund is healthy at {ef_stats['ratio']:.1f} months of expenses (Target: {target_mult}x)."
        })
        
    # 4. BUDGET INSIGHTS
    # Fetch budgets for this month
    budgets_query = """
        SELECT b.*, m.name as member_name
        FROM budgets b
        LEFT JOIN members m ON b.member_id = m.id
        WHERE b.month = ? AND (b.member_id IS NULL OR m.user_id = ?)
    """
    budgets = execute_query(budgets_query, (current_month_str, user_id))
    
    # Fetch actual expenses for this month
    actual_query = """
        SELECT m.id as member_id, t.category, SUM(t.amount) as actual_amount
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        WHERE m.user_id = ? AND t.type = 'Expense' AND STRFTIME('%Y-%m', t.date) = ?
        GROUP BY m.id, t.category
    """
    actuals = execute_query(actual_query, (user_id, current_month_str))
    
    # Check overruns
    for b in budgets:
        # If it's family level:
        if b['member_id'] is None:
            # sum actuals for this category across family
            cat_actual = sum([a['actual_amount'] for a in actuals if a['category'] == b['category']])
            limit = b['limit_amount']
            member_label = "Family"
        else:
            # sum actuals for this category and member
            cat_actual = sum([a['actual_amount'] for a in actuals if a['category'] == b['category'] and a['member_id'] == b['member_id']])
            limit = b['limit_amount']
            member_label = b['member_name']
            
        if limit > 0 and cat_actual > limit:
            overrun_pct = ((cat_actual - limit) / limit) * 100
            insights.append({
                "level": "Warning",
                "category": "Budget",
                "message": f"{member_label} spending on '{b['category']}' is {overrun_pct:.1f}% over budget this month."
            })
            
    # 5. INSURANCE INSIGHTS
    policies_query = """
        SELECT i.*, m.name as member_name
        FROM insurance i
        JOIN members m ON i.member_id = m.id
        WHERE m.user_id = ?
    """
    policies = execute_query(policies_query, (user_id,))
    
    # Gap analysis alerts
    insurance_alerts = analyze_insurance_gaps(policies, members, has_kids)
    for alert in insurance_alerts:
        insights.append({
            "level": "Critical" if alert['level'] in ["Critical", "High Risk"] else "Warning",
            "category": "Insurance Gap",
            "message": alert['message']
        })
        
    # Check if primary user has term life if they have dependents
    has_dependents = any(m['is_dependent'] == 1 and m['relationship'] != 'Self' for m in members)
    if has_dependents:
        # Check if user has term insurance
        term_ins = [p for p in policies if p['type'] == 'Term']
        if not term_ins:
            # Find primary user name
            primary_name = next((m['name'] for m in members if m['relationship'] == 'Self'), "Primary user")
            insights.append({
                "level": "Warning",
                "category": "Insurance Gap",
                "message": f"{primary_name} has no term insurance — dependents at risk."
            })
            
    # Check renewals
    for p in policies:
        try:
            renewal_dt = datetime.datetime.strptime(p['renewal_date'], "%Y-%m-%d").date()
            days_diff = (renewal_dt - today).days
            if 0 <= days_diff <= 30:
                insights.append({
                    "level": "Warning",
                    "category": "Insurance Renewal",
                    "message": f"Health/Life insurance renewal for {p['member_name']} ({p['provider']}) due in {days_diff} days."
                })
        except Exception:
            pass
            
    # 6. INVESTMENT INSIGHTS
    investments_query = """
        SELECT i.*, m.name as member_name
        FROM investments i
        JOIN members m ON i.member_id = m.id
        WHERE m.user_id = ?
    """
    investments = execute_query(investments_query, (user_id,))
    for inv in investments:
        cagr = calculate_cagr(inv['invested_amount'], inv['current_value'], inv['start_date'])
        # If CAGR is high, nudge user that it's outperforming FDs
        if cagr >= 12.0 and inv['type'] in ['SIP', 'MF', 'Stocks']:
            insights.append({
                "level": "Success",
                "category": "Investments",
                "message": f"SIP '{inv['name']}' is returning {cagr:.1f}% CAGR — outperforming standard FD returns (7.0%)."
            })
            
    # 7. SAVINGS GOAL INSIGHTS
    goals_query = """
        SELECT g.*, m.name as member_name
        FROM goals g
        LEFT JOIN members m ON g.member_id = m.id
        WHERE g.member_id IS NULL OR m.user_id = ?
    """
    goals = execute_query(goals_query, (user_id,))
    for g in goals:
        target = g['target_amount']
        saved = g['saved_amount']
        monthly = g['monthly_contribution']
        deadline_str = g['deadline']
        
        if saved >= target:
            continue
            
        months_rem, proj_comp = calculate_projected_completion(target, saved, monthly)
        
        if months_rem is None:
            insights.append({
                "level": "Warning",
                "category": "Goals",
                "message": f"Goal '{g['name']}' is unfunded (₹0 monthly contribution) and cannot reach target."
            })
            continue
            
        try:
            deadline_dt = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()
            months_to_deadline = (deadline_dt.year - today.year) * 12 + (deadline_dt.month - today.month)
            
            if months_rem <= months_to_deadline:
                # Get the formatted target category/name
                g_name_clean = g['name'].split(": ")[-1] if ": " in g['name'] else g['name']
                insights.append({
                    "level": "Success",
                    "category": "Goals",
                    "message": f"'{g_name_clean}' savings goal is on track — projected completion in {proj_comp}."
                })
            else:
                deficit_monthly = (target - saved - (monthly * months_to_deadline)) / max(1, months_to_deadline)
                insights.append({
                    "level": "Warning",
                    "category": "Goals",
                    "message": f"Goal '{g['name']}' is delayed — projected completion {proj_comp} (Deadline: {deadline_dt.strftime('%b %Y')}). Consider topping up ₹{max(0.0, deficit_monthly):,.2f}/mo."
                })
        except Exception:
            pass
            
    return insights
