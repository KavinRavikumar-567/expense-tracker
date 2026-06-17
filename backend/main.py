import os
import hashlib
import uuid
import datetime
from fastapi import FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List

from backend.database import init_db, execute_query
from backend.calculations import (
    calculate_cagr, 
    calculate_projected_completion, 
    calculate_emergency_fund_status, 
    analyze_insurance_gaps
)

app = FastAPI(title="Antigravity Family Finance Manager API")

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Password Hashing Helper
def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = uuid.uuid4().hex
    hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return hashed, salt

# Pydantic Schemas
class SignupRequest(BaseModel):
    username: str
    password: str
    name: str
    age: int
    mode: str
    monthly_income: float

class LoginRequest(BaseModel):
    username: str
    password: str

class MemberCreate(BaseModel):
    name: str
    age: int
    relationship: str
    monthly_income: float
    is_dependent: bool

class TransactionCreate(BaseModel):
    member_id: int
    date: str
    type: str
    category: str
    amount: float
    note: Optional[str] = ""

class BudgetCreate(BaseModel):
    member_id: Optional[int] = None
    month: str
    category: str
    limit_amount: float

class GoalCreate(BaseModel):
    member_id: Optional[int] = None
    name: str
    target_amount: float
    saved_amount: float
    monthly_contribution: float
    deadline: str

class GoalUpdate(BaseModel):
    saved_amount: float

class InvestmentCreate(BaseModel):
    member_id: int
    type: str
    name: str
    invested_amount: float
    current_value: float
    start_date: str

class InvestmentUpdate(BaseModel):
    current_value: float

class InsuranceCreate(BaseModel):
    member_id: int
    type: str
    provider: str
    premium: float
    sum_assured: float
    renewal_date: str

class EmergencyFundUpdate(BaseModel):
    current_amount: float

# Helper to verify headers
def verify_user(x_user_id: Optional[str]) -> int:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user session")

# ==================== AUTH ENDPOINTS ====================

@app.post("/api/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest):
    username_clean = req.username.lower().strip()
    if not username_clean or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")
        
    # Check if username exists
    existing = execute_query("SELECT id FROM users WHERE username = ?", (username_clean,))
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash password
    p_hash, salt = hash_password(req.password)
    
    # Insert User
    user_id = execute_query(
        "INSERT INTO users (username, password_hash, salt, name, age, mode, monthly_income) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (username_clean, p_hash, salt, req.name.strip(), req.age, req.mode, req.monthly_income),
        is_select=False
    )
    
    # Insert Self member
    execute_query(
        "INSERT INTO members (user_id, name, age, relationship, monthly_income, is_dependent) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, req.name.strip(), req.age, 'Self', req.monthly_income, 0),
        is_select=False
    )
    
    # Initialize Emergency Fund
    execute_query(
        "INSERT INTO emergency_fund (user_id, current_amount) VALUES (?, 0.0)",
        (user_id,),
        is_select=False
    )
    
    return {"message": "User created successfully", "user_id": user_id}

@app.post("/api/login")
def login(req: LoginRequest):
    username_clean = req.username.lower().strip()
    rows = execute_query("SELECT * FROM users WHERE username = ?", (username_clean,))
    if not rows:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    user = rows[0]
    p_hash, _ = hash_password(req.password, user['salt'])
    if p_hash != user['password_hash']:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
        
    return {
        "id": user['id'],
        "username": user['username'],
        "name": user['name'],
        "age": user['age'],
        "mode": user['mode'],
        "monthly_income": user['monthly_income']
    }

@app.get("/api/user")
def get_user(x_user_id: Optional[str] = Header(None)):
    if not x_user_id:
        return None
    try:
        u_id = int(x_user_id)
    except ValueError:
        return None
        
    users = execute_query("SELECT id, username, name, age, mode, monthly_income FROM users WHERE id = ?", (u_id,))
    return users[0] if users else None

# ==================== PROTECTED CORE API ====================

@app.get("/api/members")
def get_members(x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    return execute_query("SELECT * FROM members WHERE user_id = ?", (user_id,))

@app.post("/api/members")
def add_member(member: MemberCreate, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    member_id = execute_query(
        "INSERT INTO members (user_id, name, age, relationship, monthly_income, is_dependent) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, member.name, member.age, member.relationship, member.monthly_income, 1 if member.is_dependent else 0),
        is_select=False
    )
    return {"message": "Member added successfully", "member_id": member_id}

@app.delete("/api/members/{member_id}")
def delete_member(member_id: int, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    # Validate ownership
    existing = execute_query("SELECT id FROM members WHERE id = ? AND user_id = ?", (member_id, user_id))
    if not existing:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    execute_query("DELETE FROM members WHERE id = ?", (member_id,), is_select=False)
    return {"message": "Member deleted successfully"}

@app.get("/api/transactions")
def get_transactions(x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    query = """
        SELECT t.*, m.name as member_name, m.relationship 
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        WHERE m.user_id = ?
        ORDER BY t.date DESC
    """
    return execute_query(query, (user_id,))

@app.post("/api/transactions")
def add_transaction(tx: TransactionCreate, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    # Verify member ownership
    member = execute_query("SELECT id FROM members WHERE id = ? AND user_id = ?", (tx.member_id, user_id))
    if not member:
        raise HTTPException(status_code=403, detail="Unauthorized member assignment")
        
    tx_id = execute_query(
        "INSERT INTO transactions (member_id, date, type, category, amount, note) VALUES (?, ?, ?, ?, ?, ?)",
        (tx.member_id, tx.date, tx.type, tx.category, tx.amount, tx.note),
        is_select=False
    )
    return {"message": "Transaction recorded", "transaction_id": tx_id}

@app.delete("/api/transactions/{tx_id}")
def delete_transaction(tx_id: int, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    # Verify transaction belongs to this user
    tx = execute_query("""
        SELECT t.id FROM transactions t 
        JOIN members m ON t.member_id = m.id 
        WHERE t.id = ? AND m.user_id = ?
    """, (tx_id, user_id))
    if not tx:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    execute_query("DELETE FROM transactions WHERE id = ?", (tx_id,), is_select=False)
    return {"message": "Transaction deleted"}

@app.get("/api/budgets")
def get_budgets_endpoint(month: str, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    query = """
        SELECT b.id, b.member_id, b.month, b.category, b.limit_amount,
               CASE WHEN b.member_id IS NULL THEN 'Family (Combined)' ELSE m.name END as member_name
        FROM budgets b
        LEFT JOIN members m ON b.member_id = m.id
        WHERE b.month = ? AND b.user_id = ?
    """
    return execute_query(query, (month, user_id))

@app.post("/api/budgets")
def set_budget_endpoint(budget: BudgetCreate, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    
    # If member_id is assigned, verify ownership
    if budget.member_id is not None:
        member = execute_query("SELECT id FROM members WHERE id = ? AND user_id = ?", (budget.member_id, user_id))
        if not member:
            raise HTTPException(status_code=403, detail="Unauthorized member assignment")
            
    # Check if budget already exists
    if budget.member_id is None:
        exists = execute_query(
            "SELECT id FROM budgets WHERE user_id = ? AND member_id IS NULL AND month = ? AND category = ?",
            (user_id, budget.month, budget.category)
        )
    else:
        exists = execute_query(
            "SELECT id FROM budgets WHERE user_id = ? AND member_id = ? AND month = ? AND category = ?",
            (user_id, budget.member_id, budget.month, budget.category)
        )
        
    if exists:
        execute_query(
            "UPDATE budgets SET limit_amount = ? WHERE id = ?",
            (budget.limit_amount, exists[0]['id']),
            is_select=False
        )
        b_id = exists[0]['id']
    else:
        b_id = execute_query(
            "INSERT INTO budgets (user_id, member_id, month, category, limit_amount) VALUES (?, ?, ?, ?, ?)",
            (user_id, budget.member_id, budget.month, budget.category, budget.limit_amount),
            is_select=False
        )
    return {"message": "Budget limit updated", "budget_id": b_id}

@app.delete("/api/budgets/{budget_id}")
def delete_budget_endpoint(budget_id: int, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    # Ownership check
    exists = execute_query("SELECT id FROM budgets WHERE id = ? AND user_id = ?", (budget_id, user_id))
    if not exists:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    execute_query("DELETE FROM budgets WHERE id = ?", (budget_id,), is_select=False)
    return {"message": "Budget deleted"}

@app.get("/api/goals")
def get_goals_endpoint(x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    query = """
        SELECT g.*, 
               CASE WHEN g.member_id IS NULL THEN 'Family (Combined)' ELSE m.name END as member_name
        FROM goals g
        LEFT JOIN members m ON g.member_id = m.id
        WHERE g.user_id = ?
    """
    return execute_query(query, (user_id,))

@app.post("/api/goals")
def create_goal(goal: GoalCreate, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    
    if goal.member_id is not None:
        member = execute_query("SELECT id FROM members WHERE id = ? AND user_id = ?", (goal.member_id, user_id))
        if not member:
            raise HTTPException(status_code=403, detail="Unauthorized member assignment")
            
    goal_id = execute_query(
        """
        INSERT INTO goals (user_id, member_id, name, target_amount, saved_amount, monthly_contribution, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, goal.member_id, goal.name, goal.target_amount, goal.saved_amount, goal.monthly_contribution, goal.deadline),
        is_select=False
    )
    return {"message": "Goal created", "goal_id": goal_id}

@app.put("/api/goals/{goal_id}")
def update_goal_progress(goal_id: int, payload: GoalUpdate, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    exists = execute_query("SELECT id FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
    if not exists:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    execute_query(
        "UPDATE goals SET saved_amount = ? WHERE id = ?",
        (payload.saved_amount, goal_id),
        is_select=False
    )
    return {"message": "Goal savings updated"}

@app.delete("/api/goals/{goal_id}")
def delete_goal_endpoint(goal_id: int, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    exists = execute_query("SELECT id FROM goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
    if not exists:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    execute_query("DELETE FROM goals WHERE id = ?", (goal_id,), is_select=False)
    return {"message": "Goal removed"}

@app.get("/api/investments")
def get_investments_endpoint(x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    query = """
        SELECT i.*, m.name as member_name
        FROM investments i
        JOIN members m ON i.member_id = m.id
        WHERE m.user_id = ?
    """
    investments = execute_query(query, (user_id,))
    
    for inv in investments:
        inv['cagr'] = calculate_cagr(inv['invested_amount'], inv['current_value'], inv['start_date'])
        inv['returns'] = inv['current_value'] - inv['invested_amount']
        inv['roi'] = round((inv['returns'] / inv['invested_amount'] * 100), 2) if inv['invested_amount'] > 0 else 0.0
        
    return investments

@app.post("/api/investments")
def add_investment_endpoint(inv: InvestmentCreate, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    member = execute_query("SELECT id FROM members WHERE id = ? AND user_id = ?", (inv.member_id, user_id))
    if not member:
        raise HTTPException(status_code=403, detail="Unauthorized member assignment")
        
    inv_id = execute_query(
        """
        INSERT INTO investments (member_id, type, name, invested_amount, current_value, start_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (inv.member_id, inv.type, inv.name, inv.invested_amount, inv.current_value, inv.start_date),
        is_select=False
    )
    return {"message": "Investment logged", "investment_id": inv_id}

@app.put("/api/investments/{inv_id}")
def update_investment_valuation(inv_id: int, payload: InvestmentUpdate, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    exists = execute_query("""
        SELECT i.id FROM investments i 
        JOIN members m ON i.member_id = m.id 
        WHERE i.id = ? AND m.user_id = ?
    """, (inv_id, user_id))
    if not exists:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    execute_query(
        "UPDATE investments SET current_value = ? WHERE id = ?",
        (payload.current_value, inv_id),
        is_select=False
    )
    return {"message": "Investment valuation updated"}

@app.delete("/api/investments/{inv_id}")
def delete_investment_endpoint(inv_id: int, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    exists = execute_query("""
        SELECT i.id FROM investments i 
        JOIN members m ON i.member_id = m.id 
        WHERE i.id = ? AND m.user_id = ?
    """, (inv_id, user_id))
    if not exists:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    execute_query("DELETE FROM investments WHERE id = ?", (inv_id,), is_select=False)
    return {"message": "Investment holding deleted"}

@app.get("/api/insurance")
def get_insurance_endpoint(x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    query = """
        SELECT i.*, m.name as member_name
        FROM insurance i
        JOIN members m ON i.member_id = m.id
        WHERE m.user_id = ?
    """
    return execute_query(query, (user_id,))

@app.post("/api/insurance")
def add_insurance_endpoint(ins: InsuranceCreate, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    member = execute_query("SELECT id FROM members WHERE id = ? AND user_id = ?", (ins.member_id, user_id))
    if not member:
        raise HTTPException(status_code=403, detail="Unauthorized member assignment")
        
    ins_id = execute_query(
        """
        INSERT INTO insurance (member_id, type, provider, premium, sum_assured, renewal_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (ins.member_id, ins.type, ins.provider, ins.premium, ins.sum_assured, ins.renewal_date),
        is_select=False
    )
    return {"message": "Insurance logged", "insurance_id": ins_id}

@app.delete("/api/insurance/{ins_id}")
def delete_insurance_endpoint(ins_id: int, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    exists = execute_query("""
        SELECT i.id FROM insurance i 
        JOIN members m ON i.member_id = m.id 
        WHERE i.id = ? AND m.user_id = ?
    """, (ins_id, user_id))
    if not exists:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    execute_query("DELETE FROM insurance WHERE id = ?", (ins_id,), is_select=False)
    return {"message": "Insurance policy deleted"}

@app.get("/api/emergency-fund")
def get_emergency_fund_endpoint(x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    user_rows = execute_query("SELECT mode, monthly_income FROM users WHERE id = ?", (user_id,))
    if not user_rows:
        raise HTTPException(status_code=404, detail="User not found")
    user = user_rows[0]
        
    ef_row = execute_query("SELECT current_amount FROM emergency_fund WHERE user_id = ? LIMIT 1", (user_id,))
    current_amount = ef_row[0]['current_amount'] if ef_row else 0.0
    
    exp_query = """
        SELECT SUM(amount) as total_expense
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        WHERE m.user_id = ? AND t.type = 'Expense'
        GROUP BY STRFTIME('%Y-%m', t.date)
    """
    exp_rows = execute_query(exp_query, (user_id,))
    actual_average = 0.0
    if exp_rows:
        actual_average = sum([r['total_expense'] for r in exp_rows]) / len(exp_rows)
        
    fallback_average = actual_average if actual_average > 0 else (user['monthly_income'] * 0.5 if user['monthly_income'] > 0 else 25000.0)
    status_dict = calculate_emergency_fund_status(current_amount, fallback_average, user['mode'])
    
    return {
        "current_amount": current_amount,
        "target_amount": status_dict['target_amount'],
        "gap": status_dict['gap'],
        "ratio": status_dict['ratio'],
        "status": status_dict['status'],
        "top_up_suggestion_12m": status_dict['top_up_suggestion_12m'],
        "actual_average_expenses": actual_average
    }

@app.post("/api/emergency-fund")
def update_emergency_fund_endpoint(payload: EmergencyFundUpdate, x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    execute_query(
        "UPDATE emergency_fund SET current_amount = ?, last_updated = CURRENT_TIMESTAMP WHERE user_id = ?",
        (payload.current_amount, user_id),
        is_select=False
    )
    return {"message": "Emergency fund balance updated"}

@app.get("/api/insights")
def get_insights_endpoint(x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    user_rows = execute_query("SELECT mode, monthly_income, name FROM users WHERE id = ?", (user_id,))
    if not user_rows:
        return []
    user = user_rows[0]
        
    today = datetime.date.today()
    current_month_str = today.strftime("%Y-%m")
    insights = []
    
    members = execute_query("SELECT * FROM members WHERE user_id = ?", (user_id,))
    has_kids = any(m['relationship'] == 'Child' for m in members)
    
    # 1. Emergency Fund
    ef_info = get_emergency_fund_endpoint(x_user_id=str(user_id))
    if ef_info:
        target_mult = 3 if user['mode'] == 'Bachelor' else 6
        if ef_info['ratio'] < target_mult:
            if ef_info['ratio'] < 2.0:
                insights.append({
                    "level": "Critical",
                    "category": "Emergency Fund",
                    "message": f"Emergency fund covers only {ef_info['ratio']:.1f} months of expenses — top up ₹{ef_info['top_up_suggestion_12m']:,.2f}/month."
                })
            else:
                insights.append({
                    "level": "Warning",
                    "category": "Emergency Fund",
                    "message": f"Emergency fund is at {ef_info['ratio']:.1f}x (Target: {target_mult}x) — top up ₹{ef_info['top_up_suggestion_12m']:,.2f}/month."
                })
        else:
            insights.append({
                "level": "Success",
                "category": "Emergency Fund",
                "message": f"Emergency fund is healthy at {ef_info['ratio']:.1f}x expenses."
            })
            
    # 2. Budget Overruns
    budgets = execute_query("SELECT * FROM budgets WHERE month = ? AND user_id = ?", (current_month_str, user_id))
    actual_query = """
        SELECT m.id as member_id, m.name as member_name, t.category, SUM(t.amount) as actual_amount
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        WHERE m.user_id = ? AND t.type = 'Expense' AND STRFTIME('%Y-%m', t.date) = ?
        GROUP BY m.id, t.category
    """
    actuals = execute_query(actual_query, (user_id, current_month_str))
    
    for b in budgets:
        if b['member_id'] is None:
            cat_actual = sum([a['actual_amount'] for a in actuals if a['category'] == b['category']])
            limit = b['limit_amount']
            label = "Family"
        else:
            cat_actual = sum([a['actual_amount'] for a in actuals if a['category'] == b['category'] and a['member_id'] == b['member_id']])
            limit = b['limit_amount']
            label = next((m['name'] for m in members if m['id'] == b['member_id']), "Member")
            
        if limit > 0 and cat_actual > limit:
            overrun = ((cat_actual - limit) / limit) * 100
            insights.append({
                "level": "Warning",
                "category": "Budget Overrun",
                "message": f"{label} spending on '{b['category']}' is {overrun:.1f}% over budget this month."
            })
            
    # 3. Insurance Gap Analyzer
    insurance_rows = get_insurance_endpoint(x_user_id=str(user_id))
    gap_alerts = analyze_insurance_gaps(insurance_rows, members, has_kids)
    for alert in gap_alerts:
        insights.append({
            "level": "Critical" if alert['level'] in ["Critical", "High Risk"] else "Warning",
            "category": "Insurance Gap",
            "message": alert['message']
        })
        
    has_dependents = any(m['is_dependent'] == 1 and m['relationship'] != 'Self' for m in members)
    if has_dependents:
        term_ins = [p for p in insurance_rows if p['type'] == 'Term']
        if not term_ins:
            insights.append({
                "level": "Warning",
                "category": "Insurance Gap",
                "message": f"{user['name']} has no term insurance — dependents at risk."
            })
            
    for p in insurance_rows:
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
            
    # 4. Investments Outperforming FDs
    investments = get_investments_endpoint(x_user_id=str(user_id))
    for inv in investments:
        if inv['cagr'] >= 12.0 and inv['type'] in ['SIP', 'MF', 'Stocks']:
            insights.append({
                "level": "Success",
                "category": "Investments",
                "message": f"SIP '{inv['name']}' is returning {inv['cagr']:.1f}% CAGR — outperforming FD returns (7.0%)."
            })
            
    # 5. Goals Tracker timeline
    goals = get_goals_endpoint(x_user_id=str(user_id))
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
                "category": "Goal Delayed",
                "message": f"Savings goal '{g['name']}' has zero monthly savings contribution."
            })
            continue
            
        try:
            deadline_dt = datetime.datetime.strptime(deadline_str, "%Y-%m-%d").date()
            months_to_deadline = (deadline_dt.year - today.year) * 12 + (deadline_dt.month - today.month)
            
            if months_rem <= months_to_deadline:
                insights.append({
                    "level": "Success",
                    "category": "Goals",
                    "message": f"'{g['name']}' goal is on track — projected completion in {proj_comp}."
                })
            else:
                deficit_monthly = (target - saved - (monthly * months_to_deadline)) / max(1, months_to_deadline)
                insights.append({
                    "level": "Warning",
                    "category": "Goal Delayed",
                    "message": f"Goal '{g['name']}' is delayed — projected completion {proj_comp} (Deadline: {deadline_dt.strftime('%b %Y')}). Top up by ₹{max(0.0, deficit_monthly):,.2f}/mo."
                })
        except Exception:
            pass
            
    return insights

@app.get("/api/dashboard")
def get_dashboard_summary(x_user_id: Optional[str] = Header(None)):
    user_id = verify_user(x_user_id)
    user_rows = execute_query("SELECT mode, monthly_income FROM users WHERE id = ?", (user_id,))
    if not user_rows:
        return None
    
    today = datetime.date.today()
    current_month_str = today.strftime("%Y-%m")
    
    txs = get_transactions(x_user_id=str(user_id))
    income_val = 0.0
    expense_val = 0.0
    
    for t in txs:
        if t['date'].startswith(current_month_str):
            if t['type'] == 'Income':
                income_val += t['amount']
            else:
                expense_val += t['amount']
                
    ef_info = get_emergency_fund_endpoint(x_user_id=str(user_id))
    
    # Budgets summary
    budgets = execute_query("SELECT * FROM budgets WHERE month = ? AND user_id = ?", (current_month_str, user_id))
    actual_query = """
        SELECT m.id as member_id, t.category, SUM(t.amount) as actual_amount
        FROM transactions t
        JOIN members m ON t.member_id = m.id
        WHERE m.user_id = ? AND t.type = 'Expense' AND STRFTIME('%Y-%m', t.date) = ?
        GROUP BY m.id, t.category
    """
    actuals = execute_query(actual_query, (user_id, current_month_str))
    
    safe_cnt = 0
    warning_cnt = 0
    overrun_cnt = 0
    
    for b in budgets:
        if b['member_id'] is None:
            cat_actual = sum([a['actual_amount'] for a in actuals if a['category'] == b['category']])
        else:
            cat_actual = sum([a['actual_amount'] for a in actuals if a['category'] == b['category'] and a['member_id'] == b['member_id']])
            
        limit = b['limit_amount']
        if limit > 0:
            pct = (cat_actual / limit) * 100
            if pct < 80:
                safe_cnt += 1
            elif pct <= 100:
                warning_cnt += 1
            else:
                overrun_cnt += 1
                
    investments = get_investments_endpoint(x_user_id=str(user_id))
    inv_invested = sum([i['invested_amount'] for i in investments])
    inv_current = sum([i['current_value'] for i in investments])
    
    recent_txs = txs[:5]
    insights_list = get_insights_endpoint(x_user_id=str(user_id))
    
    return {
        "monthly_income": income_val,
        "monthly_expenses": expense_val,
        "net_savings": income_val - expense_val,
        "emergency_fund": ef_info,
        "budget_summary": {
            "safe": safe_cnt,
            "warning": warning_cnt,
            "over": overrun_cnt,
            "total_budgets_defined": len(budgets)
        },
        "investments": {
            "total_invested": inv_invested,
            "total_current": inv_current,
            "absolute_returns": inv_current - inv_invested
        },
        "recent_transactions": recent_txs,
        "insights": insights_list[:4]
    }

# ==================== STATIC FILES SERVING ====================

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")
    
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    @app.get("/")
    def index_fallback():
        return {"message": "FastAPI is running. Compile frontend using 'npm run build' inside frontend/ to serve files."}
