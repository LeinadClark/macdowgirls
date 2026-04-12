from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'helpersofgod_secret_key'

# --- DATABASE CONNECTION ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/HelpersOfGod_DB'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- TEST CONNECTION ON STARTUP ---
with app.app_context():
    try:
        db.session.execute(text("SELECT 1"))
        print("✅ Database connected successfully!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

# -----------------------------------------------
# DATABASE MODELS
# -----------------------------------------------

class User(db.Model):
    __tablename__ = 'Users'
    user_id       = db.Column(db.String(36), primary_key=True)
    rfid_tag      = db.Column(db.String(50), unique=True)
    full_name     = db.Column(db.String(255), nullable=False)
    email         = db.Column(db.String(255), unique=True)
    password_hash = db.Column(db.String(255))
    role          = db.Column(db.Enum('student', 'faculty', 'admin', 'donor'), nullable=False)
    created_at    = db.Column(db.DateTime)

class Initiative(db.Model):
    __tablename__  = 'Initiatives'
    initiative_id  = db.Column(db.String(36), primary_key=True)
    creator_id     = db.Column(db.String(36))
    title          = db.Column(db.String(255), nullable=False)
    description    = db.Column(db.Text)
    category       = db.Column(db.Enum('research', 'outreach', 'conservation', 'scholarship'))
    target_amount  = db.Column(db.Numeric(15, 2))
    current_amount = db.Column(db.Numeric(15, 2), default=0.00)
    status         = db.Column(db.Enum('draft', 'active', 'completed', 'cancelled'))
    start_date     = db.Column(db.Date)
    end_date       = db.Column(db.Date)
    created_at     = db.Column(db.DateTime)

class Donation(db.Model):
    __tablename__   = 'Donations'
    donation_id     = db.Column(db.String(36), primary_key=True)
    initiative_id   = db.Column(db.String(36))
    donor_id        = db.Column(db.String(36))
    amount          = db.Column(db.Numeric(15, 2))
    transaction_ref = db.Column(db.String(100), unique=True)
    status          = db.Column(db.Enum('pending', 'success', 'failed'))
    created_at      = db.Column(db.DateTime)

class Milestone(db.Model):
    __tablename__ = 'Milestones'
    milestone_id  = db.Column(db.String(36), primary_key=True)
    initiative_id = db.Column(db.String(36))
    title         = db.Column(db.String(255))
    description   = db.Column(db.Text)
    is_completed  = db.Column(db.Boolean, default=False)

# -----------------------------------------------
# PAGE ROUTES
# -----------------------------------------------

@app.route('/')
def login():
    """Login / Register Page"""
    error      = request.args.get('error')
    success    = request.args.get('success')
    active_tab = request.args.get('tab', 'login')
    return render_template('login_page.html',
                           error=error,
                           success=success,
                           active_tab=active_tab)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    initiatives = Initiative.query.filter_by(status='active').all()
    return render_template('dashboard.html', initiatives=initiatives)

@app.route('/campaigns')
def campaigns():
    """Campaigns / Donation Page — lists all active initiatives"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    initiatives = Initiative.query.filter_by(status='active').all()
    return render_template('campaigns.html',
                           initiatives=initiatives,
                           donor_id=session.get('user_id'))

@app.route('/campaign/<initiative_id>')
def campaign_detail(initiative_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    initiative = Initiative.query.get_or_404(initiative_id)
    return render_template('campaign_pledge_form.html', initiative=initiative)

@app.route('/community-impact')
def community_impact():
    return render_template('community_impact_relief_hub.html')

@app.route('/outreach')
def outreach():
    return render_template('community_outreach_sectors.html')

@app.route('/donors')
def donor_registry():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    donors = User.query.filter_by(role='donor').all()
    return render_template('donor_registry.html', donors=donors)

@app.route('/heritage')
def heritage():
    return render_template('heritage_impact.html')

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    initiatives = Initiative.query.all()
    donors      = User.query.filter_by(role='donor').all()
    donations   = Donation.query.all()
    return render_template('admin.html',
                           initiatives=initiatives,
                           donors=donors,
                           donations=donations)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -----------------------------------------------
# AUTH ROUTES
# -----------------------------------------------

@app.route('/login', methods=['POST'])
def do_login():
    """Handle login form submission"""
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    user = User.query.filter_by(email=email).first()

    if user and user.password_hash == password:
        session['user_id']  = user.user_id
        session['role']     = user.role
        session['name']     = user.full_name

        if user.role == 'admin':
            return redirect(url_for('admin'))
        elif user.role == 'donor':
            return redirect(url_for('donor_registry'))
        else:
            return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login',
                                error='Invalid email or password. Please try again.',
                                tab='login'))

@app.route('/register', methods=['POST'])
def do_register():
    """Handle registration form submission"""
    full_name        = request.form.get('full_name', '').strip()
    email            = request.form.get('email', '').strip()
    role             = request.form.get('role', '').strip()
    password         = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not full_name or not email or not role or not password:
        return redirect(url_for('login',
                                error='Please fill in all fields.',
                                tab='register'))

    if password != confirm_password:
        return redirect(url_for('login',
                                error='Passwords do not match. Please try again.',
                                tab='register'))

    if len(password) < 6:
        return redirect(url_for('login',
                                error='Password must be at least 6 characters.',
                                tab='register'))

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return redirect(url_for('login',
                                error='An account with this email already exists. Please sign in.',
                                tab='register'))

    new_user = User(
        user_id       = str(uuid.uuid4()),
        rfid_tag      = None,
        full_name     = full_name,
        email         = email,
        password_hash = password,
        role          = role
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login',
                                success=f'Account created! Welcome, {full_name}. Please sign in.',
                                tab='login'))
    except Exception as e:
        db.session.rollback()
        return redirect(url_for('login',
                                error='Registration failed. Please try again.',
                                tab='register'))

# -----------------------------------------------
# API ROUTES
# -----------------------------------------------

@app.route('/api/initiatives')
def api_initiatives():
    """
    JSON endpoint for fetching real initiative IDs from database
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    initiatives = Initiative.query.filter_by(status='active').all()
    return jsonify([{
        "id":          i.initiative_id,
        "title":       i.title,
        "description": i.description or '',
        "category":    i.category,
        "raised":      float(i.current_amount or 0),
        "goal":        float(i.target_amount or 0),
        "end_date":    str(i.end_date) if i.end_date else None
    } for i in initiatives])

@app.route('/user/rfid/<tag>', methods=['GET'])
def get_user_by_rfid(tag):
    """RFID Simulation Endpoint"""
    user = User.query.filter_by(rfid_tag=tag).first()
    if user:
        return jsonify({
            "user_id":   user.user_id,
            "full_name": user.full_name,
            "role":      user.role
        }), 200
    return jsonify({"message": "User not found"}), 404

@app.route('/donate', methods=['POST'])
def donate():
    """
    ✅ FIXED: Save donation directly to database
    No setup needed - saves immediately when user confirms donation
    """
    # Check if user is authenticated
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    data = request.json
    
    # Get parameters from request
    initiative_id = data.get('initiative_id')
    amount = data.get('amount')
    donor_id = session.get('user_id')  # ✅ Get from session, NOT request
    
    # Validation: Check required fields
    if not initiative_id or not amount:
        return jsonify({"status": "error", "message": "Missing initiative or amount"}), 400
    
    # Validation: Check amount is valid
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"status": "error", "message": "Amount must be greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid amount"}), 400
    
    # Check if initiative exists
    initiative = Initiative.query.get(initiative_id)
    if not initiative:
        return jsonify({"status": "error", "message": "Initiative not found"}), 404
    
    try:
        # Generate IDs and reference
        donation_id = str(uuid.uuid4())
        transaction_ref = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        
        # ✅ Create donation record
        donation = Donation(
            donation_id=donation_id,
            initiative_id=initiative_id,
            donor_id=donor_id,
            amount=amount,
            transaction_ref=transaction_ref,
            status='success',
            created_at=datetime.now()
        )
        
        # Add to database session
        db.session.add(donation)
        
        # ✅ Update initiative current amount
        initiative.current_amount = float(initiative.current_amount or 0) + amount
        
        # ✅ Check if goal is met and update status to 'completed'
        if initiative.current_amount >= initiative.target_amount:
            initiative.status = 'completed'
        
        # ✅ Commit all changes to database
        db.session.commit()
        
        # Check if goal was met
        goal_met = initiative.current_amount >= initiative.target_amount
        
        print(f"✅ Donation saved: {donation_id} | Amount: ₱{amount} | Ref: {transaction_ref}")
        
        return jsonify({
            "status": "success",
            "message": "Thank you for your blessing",
            "ref": transaction_ref,
            "goal_met": goal_met,
            "new_total": float(initiative.current_amount),
            "donation_id": donation_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Donation error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error saving donation to database",
            "detail": str(e)
        }), 400

@app.route('/create-initiative', methods=['POST'])
def create_initiative():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    data = request.form
    new_init = Initiative(
        initiative_id  = str(uuid.uuid4()),
        creator_id     = session.get('user_id'),
        title          = data.get('title'),
        description    = data.get('description'),
        category       = data.get('category'),
        target_amount  = data.get('target_amount'),
        status         = 'active'
    )
    db.session.add(new_init)
    db.session.commit()
    return redirect(url_for('dashboard'))

# -----------------------------------------------
# RUN
# -----------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)