import datetime
import calendar

def calculate_cagr(invested_amount, current_value, start_date_str):
    """Calculates CAGR in percent."""
    if invested_amount <= 0 or current_value < 0:
        return 0.0
    
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except ValueError:
        return 0.0
        
    today = datetime.date.today()
    days_diff = (today - start_date).days
    
    if days_diff <= 0:
        return 0.0
        
    years = days_diff / 365.25
    
    try:
        cagr = ((current_value / invested_amount) ** (1.0 / years)) - 1.0
        return round(cagr * 100.0, 2)
    except Exception:
        return 0.0

def calculate_projected_completion(target_amount, saved_amount, monthly_contribution):
    """Calculates remaining months and target completion date text."""
    if target_amount <= saved_amount:
        return 0, "Completed"
    
    if monthly_contribution <= 0:
        return None, "Never (increase contribution)"
        
    remaining = target_amount - saved_amount
    months = remaining / monthly_contribution
    
    today = datetime.date.today()
    total_months = today.month - 1 + int(round(months))
    new_month = (total_months % 12) + 1
    new_year = today.year + (total_months // 12)
    
    max_days = calendar.monthrange(new_year, new_month)[1]
    new_day = min(today.day, max_days)
    
    projected_date = datetime.date(new_year, new_month, new_day)
    return round(months, 1), projected_date.strftime("%b %Y")

def calculate_emergency_fund_status(current_amount, monthly_expenses, mode):
    """Calculates emergency fund thresholds and top-ups."""
    target_multiplier = 3 if mode == 'Bachelor' else 6
    target_amount = monthly_expenses * target_multiplier
    gap = max(0.0, target_amount - current_amount)
    
    ratio = (current_amount / monthly_expenses) if monthly_expenses > 0 else 0.0
    
    if mode == 'Bachelor':
        if ratio < 1.0:
            status = "Critical"
        elif ratio < 3.0:
            status = "Building"
        else:
            status = "Healthy"
    else:  # Family Mode
        if ratio < 2.0:
            status = "Critical"
        elif ratio < 6.0:
            status = "Building"
        else:
            status = "Healthy"
            
    top_up_12m = round(gap / 12.0, 2) if gap > 0 else 0.0
    
    return {
        "target_amount": round(target_amount, 2),
        "gap": round(gap, 2),
        "ratio": round(ratio, 2),
        "status": status,
        "top_up_suggestion_12m": top_up_12m
    }

def analyze_insurance_gaps(policies, family_members, has_kids):
    """Finds alerts based on policy coverage."""
    alerts = []
    
    if not policies:
        alerts.append({
            "level": "High Risk",
            "message": "No insurance policies found! Your family is completely exposed to financial risks."
        })
        return alerts
        
    health_policies = [p for p in policies if p['type'] == 'Health']
    if not health_policies:
        alerts.append({
            "level": "Critical",
            "message": "No Health Insurance found! Medical emergencies can wipe out your savings."
        })
    else:
        insured_member_ids = {p['member_id'] for p in health_policies}
        missing_health_members = [m['name'] for m in family_members if m['id'] not in insured_member_ids]
        if missing_health_members:
            alerts.append({
                "level": "Warning",
                "message": f"Health insurance missing for: {', '.join(missing_health_members)}."
            })
            
    term_policies = [p for p in policies if p['type'] == 'Term']
    has_life = len(term_policies) > 0 or any(p['type'] == 'Life' for p in policies)
    
    if has_kids and not has_life:
        alerts.append({
            "level": "Warning",
            "message": "You have children but no Term Life Insurance! Dependents' future is at risk."
        })
        
    return alerts
