from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import uuid

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
    active_tab = request.args.get('tab', 'login')  # default to login tab
    return render_template('login_page.html',
                           error=error,
                           success=success,
                           active_tab=active_tab)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    initiatives = Initiative.query.filter_by(status='active').all()
    return render_template('university_campaign_dashboard.html', initiatives=initiatives)

@app.route('/campaign/<initiative_id>')
def campaign_detail(initiative_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    initiative = Initiative.query.get_or_404(initiative_id)
    return render_template('campaign_detail_pledge_form.html', initiative=initiative)

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
    return render_template('institutional_donor_registry.html', donors=donors)

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

    # Find the user by email
    user = User.query.filter_by(email=email).first()

    if user and user.password_hash == password:
        # ✅ Correct — save to session
        session['user_id']  = user.user_id
        session['role']     = user.role
        session['name']     = user.full_name

        # Redirect based on role
        if user.role == 'admin':
            return redirect(url_for('admin'))
        elif user.role == 'donor':
            return redirect(url_for('donor_registry'))
        else:
            return redirect(url_for('dashboard'))
    else:
        # ❌ Wrong credentials
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

    # --- Validation ---
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

    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return redirect(url_for('login',
                                error='An account with this email already exists. Please sign in.',
                                tab='register'))

    # --- Create new user ---
    new_user = User(
        user_id       = str(uuid.uuid4()),
        rfid_tag      = None,
        full_name     = full_name,
        email         = email,
        password_hash = password,   # plain text for now (good enough for school project)
        role          = role
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        # ✅ Registration success — go to login tab with success message
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
    Triggers MySQL Stored Procedure 'ProcessDonation'
    Transaction flow per ERD diagram:
      BEGIN TRANSACTION
        STEP 1: INSERT into Donations
        STEP 2: UPDATE Initiative total
      COMMIT
      POST-COMMIT: Check if goal met → update status to 'completed'
    """
    data = request.json

    p_donation_id   = str(uuid.uuid4())
    p_initiative_id = data.get('initiative_id')
    p_donor_id      = data.get('donor_id')
    p_amount        = data.get('amount')
    p_txn_ref       = f"TXN-{uuid.uuid4().hex[:8].upper()}"

    try:
        query = text("CALL ProcessDonation(:d_id, :i_id, :u_id, :amt, :ref)")
        db.session.execute(query, {
            "d_id": p_donation_id,
            "i_id": p_initiative_id,
            "u_id": p_donor_id,
            "amt":  p_amount,
            "ref":  p_txn_ref
        })
        db.session.commit()

        # POST-COMMIT: Goal met check (outside transaction per diagram)
        initiative = Initiative.query.get(p_initiative_id)
        goal_met   = initiative and initiative.current_amount >= initiative.target_amount

        return jsonify({
            "status":   "success",
            "message":  "Thank you for your blessing",
            "ref":      p_txn_ref,
            "goal_met": goal_met
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "status":  "error",
            "message": "Gift Failed",
            "detail":  str(e)
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