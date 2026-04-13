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
    anonymous       = db.Column(db.Boolean, default=False)
    payment_method  = db.Column(db.String(50), default='GCash')
    created_at      = db.Column(db.DateTime)

class Milestone(db.Model):
    __tablename__ = 'milestones'
    milestone_id  = db.Column(db.String(36), primary_key=True)
    initiative_id = db.Column(db.String(36))
    title         = db.Column(db.String(255), nullable=False)
    description   = db.Column(db.Text)
    is_completed  = db.Column(db.Boolean, default=False)

class Update(db.Model):
    __tablename__ = 'updates'
    update_id     = db.Column(db.String(36), primary_key=True)
    initiative_id = db.Column(db.String(36))
    content       = db.Column(db.Text, nullable=False)
    image_url     = db.Column(db.String(255))
    created_at    = db.Column(db.DateTime, default=datetime.now)

class CampaignSuggestion(db.Model):
    __tablename__ = 'campaign_suggestions'
    suggestion_id       = db.Column(db.String(36), primary_key=True)
    user_id             = db.Column(db.String(36))
    full_name           = db.Column(db.String(255), nullable=False)
    email               = db.Column(db.String(255), nullable=False)
    title               = db.Column(db.String(255), nullable=False)
    description         = db.Column(db.Text, nullable=False)
    category            = db.Column(db.Enum('research', 'outreach', 'conservation', 'scholarship'), nullable=False)
    target_amount       = db.Column(db.Numeric(15,2), nullable=False)
    required_signatures = db.Column(db.Integer, default=100)
    signature_count     = db.Column(db.Integer, default=0)
    status              = db.Column(db.Enum('pending', 'threshold_met', 'approved', 'rejected'), default='pending')
    admin_notes         = db.Column(db.Text)
    created_at          = db.Column(db.DateTime, default=datetime.now)
    reviewed_at         = db.Column(db.DateTime)

class PetitionSignature(db.Model):
    __tablename__ = 'petition_signatures'
    signature_id  = db.Column(db.String(36), primary_key=True)
    suggestion_id = db.Column(db.String(36), nullable=False)
    full_name     = db.Column(db.String(255), nullable=False)
    email         = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.Enum('student', 'faculty', 'alumni', 'community'), default='student')
    message       = db.Column(db.Text)
    created_at    = db.Column(db.DateTime, default=datetime.now)

# -----------------------------------------------
# PAGE ROUTES
# -----------------------------------------------

@app.route('/')
def login():
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
    updates = Update.query.order_by(Update.created_at.desc()).limit(5).all()
    milestones = Milestone.query.all()
    user_email = session.get('email', '')
    return render_template('dashboard.html',
                           initiatives=initiatives,
                           updates=updates,
                           milestones=milestones,
                           user_email=user_email,
                           role=session.get('role'))   # <-- add role

@app.route('/campaigns')
def campaigns():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    initiatives = Initiative.query.filter_by(status='active').all()
    return render_template('campaigns.html',
                           initiatives=initiatives,
                           donor_id=session.get('user_id'),
                           role=session.get('role'))   # <-- add role


@app.route('/campaign/<initiative_id>')
def campaign_detail(initiative_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    initiative = Initiative.query.get_or_404(initiative_id)
    return render_template('campaign_pledge_form.html', initiative=initiative)

@app.route('/donors')
def donor_registry():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    recent_donations = db.session.query(Donation, User, Initiative).\
        join(User, Donation.donor_id == User.user_id).\
        join(Initiative, Donation.initiative_id == Initiative.initiative_id).\
        order_by(Donation.created_at.desc()).all()
    return render_template('donor_registry.html',
                           donations=recent_donations,
                           role=session.get('role'))   # <-- add role


@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    initiatives = Initiative.query.all()
    donors      = User.query.filter_by(role='donor').all()
    donations   = Donation.query.all()
    suggestions = CampaignSuggestion.query.order_by(CampaignSuggestion.created_at.desc()).all()
    updates     = Update.query.order_by(Update.created_at.desc()).all()
    milestones  = Milestone.query.all()
    return render_template('admin.html',
                           initiatives=initiatives,
                           donors=donors,
                           donations=donations,
                           suggestions=suggestions,
                           updates=updates,
                           milestones=milestones)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -----------------------------------------------
# AUTH ROUTES
# -----------------------------------------------

@app.route('/login', methods=['POST'])
def do_login():
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    user = User.query.filter_by(email=email).first()
    if user and user.password_hash == password:
        session['user_id']  = user.user_id
        session['role']     = user.role
        session['name']     = user.full_name
        session['email']    = user.email
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
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    data = request.json
    initiative_id  = data.get('initiative_id')
    amount         = data.get('amount')
    is_anonymous   = data.get('anonymous', False)
    payment_method = data.get('payment_method', 'GCash')
    donor_id       = session.get('user_id')
    
    if not initiative_id or not amount:
        return jsonify({"status": "error", "message": "Missing initiative or amount"}), 400
    
    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"status": "error", "message": "Amount must be greater than 0"}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid amount"}), 400
    
    initiative = Initiative.query.get(initiative_id)
    if not initiative:
        return jsonify({"status": "error", "message": "Initiative not found"}), 404
    
    try:
        donation_id = str(uuid.uuid4())
        transaction_ref = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        
        donation = Donation(
            donation_id=donation_id,
            initiative_id=initiative_id,
            donor_id=donor_id,
            amount=amount,
            transaction_ref=transaction_ref,
            status='pending',
            anonymous=is_anonymous,
            payment_method=payment_method,
            created_at=datetime.now()
        )
        
        db.session.add(donation)
        initiative.current_amount = float(initiative.current_amount or 0) + amount
        
        if initiative.current_amount >= initiative.target_amount:
            initiative.status = 'completed'
        
        db.session.commit()
        
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

# ================== CAMPAIGN SUGGESTION API ==================

@app.route('/api/suggest-campaign', methods=['POST'])
def suggest_campaign():
    data = request.json
    
    required = ['title', 'description', 'category', 'target_amount', 'full_name', 'email']
    for field in required:
        if not data.get(field):
            return jsonify({"status": "error", "message": f"Missing field: {field}"}), 400
    
    try:
        target = float(data['target_amount'])
        if target <= 0:
            raise ValueError
    except:
        return jsonify({"status": "error", "message": "Target amount must be a positive number"}), 400
    
    required_sigs = int(data.get('required_signatures', 100))
    if required_sigs < 1:
        required_sigs = 100

    suggestion = CampaignSuggestion(
        suggestion_id       = str(uuid.uuid4()),
        user_id             = session.get('user_id'),
        full_name           = data['full_name'].strip(),
        email               = data['email'].strip(),
        title               = data['title'].strip(),
        description         = data['description'].strip(),
        category            = data['category'],
        target_amount       = target,
        required_signatures = required_sigs,
        signature_count     = 0,
        status              = 'pending',
        created_at          = datetime.now()
    )
    
    try:
        db.session.add(suggestion)
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": f"Your suggestion has been submitted! It needs {required_sigs} signatures before admin review.",
            "suggestion_id": suggestion.suggestion_id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/suggestions/<suggestion_id>', methods=['GET'])
def get_suggestion(suggestion_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    sug = CampaignSuggestion.query.get(suggestion_id)
    if not sug:
        return jsonify({"status": "error", "message": "Not found"}), 404
    return jsonify({
        "suggestion_id":       sug.suggestion_id,
        "title":               sug.title,
        "description":         sug.description,
        "category":            sug.category,
        "target_amount":       float(sug.target_amount),
        "full_name":           sug.full_name,
        "email":               sug.email,
        "status":              sug.status,
        "signature_count":     sug.signature_count,
        "required_signatures": sug.required_signatures,
        "admin_notes":         sug.admin_notes or ""
    })

@app.route('/api/admin/suggestions/<suggestion_id>', methods=['PUT'])
def review_suggestion(suggestion_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data        = request.json
    action      = data.get('action')
    admin_notes = data.get('admin_notes', '')
    
    suggestion = CampaignSuggestion.query.get(suggestion_id)
    if not suggestion:
        return jsonify({"status": "error", "message": "Suggestion not found"}), 404

    # --- NEW: Handle undo_reject ---
    if action == 'undo_reject':
        if suggestion.status != 'rejected':
            return jsonify({"status": "error", "message": "Can only undo rejected suggestions"}), 400
        
        # Restore to the appropriate pending state based on current signature count
        if suggestion.signature_count >= suggestion.required_signatures:
            suggestion.status = 'threshold_met'
        else:
            suggestion.status = 'pending'
        
        # Append undo info to admin notes (optional)
        suggestion.admin_notes = (suggestion.admin_notes or '') + f"\n[Undone on {datetime.now()}]"
        suggestion.reviewed_at = None   # Clear review timestamp so it can be reviewed again
        try:
            db.session.commit()
            return jsonify({"status": "success", "message": "Rejection undone. Suggestion is now pending again."}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)}), 500

    # For approve/reject, ensure suggestion is still pending or threshold_met
    if suggestion.status in ('approved', 'rejected'):
        return jsonify({"status": "error", "message": "Suggestion has already been reviewed."}), 400
    
    if action == 'approve':
        # Enforce signature threshold
        if suggestion.signature_count < suggestion.required_signatures:
            return jsonify({
                "status": "error",
                "message": f"Cannot approve: only {suggestion.signature_count}/{suggestion.required_signatures} signatures collected."
            }), 400

        new_initiative = Initiative(
            initiative_id  = str(uuid.uuid4()),
            creator_id     = suggestion.user_id,
            title          = suggestion.title,
            description    = suggestion.description,
            category       = suggestion.category,
            target_amount  = suggestion.target_amount,
            current_amount = 0.00,
            status         = 'active',
            start_date     = datetime.now().date(),
            end_date       = None,
            created_at     = datetime.now()
        )
        db.session.add(new_initiative)
        suggestion.status      = 'approved'
        suggestion.admin_notes = admin_notes
        suggestion.reviewed_at = datetime.now()

    elif action == 'reject':
        suggestion.status      = 'rejected'
        suggestion.admin_notes = admin_notes
        suggestion.reviewed_at = datetime.now()
    else:
        return jsonify({"status": "error", "message": "Invalid action"}), 400
    
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": f"Suggestion {action}d."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

# ================== PETITION / SIGNATURE API ==================

@app.route('/api/petition/count', methods=['GET'])
def petition_count():
    """Legacy global count — kept for backward compatibility."""
    count = PetitionSignature.query.count()
    return jsonify({"count": count})

@app.route('/api/suggestions', methods=['GET'])
def get_suggestions_public():
    """Return all pending/threshold_met suggestions so users can sign them."""
    suggestions = CampaignSuggestion.query.filter(
        CampaignSuggestion.status.in_(['pending', 'threshold_met'])
    ).order_by(CampaignSuggestion.created_at.desc()).all()
    return jsonify([{
        "suggestion_id":       s.suggestion_id,
        "title":               s.title,
        "description":         s.description,
        "category":            s.category,
        "target_amount":       float(s.target_amount),
        "full_name":           s.full_name,
        "signature_count":     s.signature_count,
        "required_signatures": s.required_signatures,
        "status":              s.status,
        "created_at":          s.created_at.strftime('%b %d, %Y') if s.created_at else ''
    } for s in suggestions])

@app.route('/api/suggestions/<suggestion_id>/sign', methods=['POST'])
def sign_suggestion(suggestion_id):
    """Sign the petition for a specific campaign suggestion."""
    suggestion = CampaignSuggestion.query.get(suggestion_id)
    if not suggestion:
        return jsonify({"status": "error", "message": "Suggestion not found."}), 404
    if suggestion.status in ('approved', 'rejected'):
        return jsonify({"status": "error", "message": "This suggestion is no longer open for signatures."}), 400

    data    = request.json
    name    = data.get('full_name', '').strip()
    email   = data.get('email', '').strip()
    role    = data.get('role', 'student')
    message = data.get('message', '').strip()

    if not name or not email:
        return jsonify({"status": "error", "message": "Name and email are required."}), 400

    existing = PetitionSignature.query.filter_by(suggestion_id=suggestion_id, email=email).first()
    if existing:
        return jsonify({"status": "error", "message": "You have already signed this petition."}), 400

    new_sig = PetitionSignature(
        signature_id  = str(uuid.uuid4()),
        suggestion_id = suggestion_id,
        full_name     = name,
        email         = email,
        role          = role,
        message       = message,
        created_at    = datetime.now()
    )
    try:
        db.session.add(new_sig)
        # Increment signature count manually (mirrors the DB trigger logic)
        if suggestion.status in ('pending', 'threshold_met'):
            suggestion.signature_count = (suggestion.signature_count or 0) + 1
        # Auto-promote to threshold_met
        if suggestion.signature_count >= suggestion.required_signatures and suggestion.status == 'pending':
            suggestion.status = 'threshold_met'
        db.session.commit()
        new_count = suggestion.signature_count
        threshold = suggestion.required_signatures
        return jsonify({
            "status":      "success",
            "message":     f"Thank you, {name}! Your signature has been recorded.",
            "count":       new_count,
            "threshold":   threshold,
            "threshold_met": new_count >= threshold
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/petition/sign', methods=['POST'])
def sign_petition():
    """Legacy endpoint — kept for backward compatibility; routes to the first open suggestion."""
    data          = request.json
    name          = data.get('full_name', '').strip()
    email         = data.get('email', '').strip()
    role          = data.get('role', 'student')
    message       = data.get('message', '').strip()
    suggestion_id = data.get('suggestion_id')

    if not name or not email:
        return jsonify({"status": "error", "message": "Name and email are required."}), 400

    # If a suggestion_id is provided delegate to the per-suggestion endpoint logic
    if suggestion_id:
        data['full_name'] = name
        from flask import request as _req
        # re-use sign_suggestion logic inline
        suggestion = CampaignSuggestion.query.get(suggestion_id)
        if not suggestion or suggestion.status in ('approved', 'rejected'):
            return jsonify({"status": "error", "message": "Suggestion not available."}), 400
        existing = PetitionSignature.query.filter_by(suggestion_id=suggestion_id, email=email).first()
        if existing:
            return jsonify({"status": "error", "message": "You have already signed this petition."}), 400
        new_sig = PetitionSignature(
            signature_id=str(uuid.uuid4()), suggestion_id=suggestion_id,
            full_name=name, email=email, role=role, message=message, created_at=datetime.now()
        )
        db.session.add(new_sig)
        suggestion.signature_count = (suggestion.signature_count or 0) + 1
        if suggestion.signature_count >= suggestion.required_signatures and suggestion.status == 'pending':
            suggestion.status = 'threshold_met'
        db.session.commit()
        return jsonify({"status": "success", "message": f"Thank you, {name}!"}), 201

    # Fallback: no suggestion_id provided — find the first open suggestion
    suggestion = CampaignSuggestion.query.filter(
        CampaignSuggestion.status.in_(['pending', 'threshold_met'])
    ).first()
    if not suggestion:
        return jsonify({"status": "error", "message": "No open suggestions to sign at the moment."}), 400
    existing = PetitionSignature.query.filter_by(suggestion_id=suggestion.suggestion_id, email=email).first()
    if existing:
        return jsonify({"status": "error", "message": "You have already signed this petition."}), 400
    new_sig = PetitionSignature(
        signature_id=str(uuid.uuid4()), suggestion_id=suggestion.suggestion_id,
        full_name=name, email=email, role=role, message=message, created_at=datetime.now()
    )
    db.session.add(new_sig)
    suggestion.signature_count = (suggestion.signature_count or 0) + 1
    if suggestion.signature_count >= suggestion.required_signatures and suggestion.status == 'pending':
        suggestion.status = 'threshold_met'
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": f"Thank you, {name}!"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

# ================== UPDATES API ==================

@app.route('/api/updates', methods=['GET'])
def get_updates():
    limit = request.args.get('limit', 10, type=int)
    updates = Update.query.order_by(Update.created_at.desc()).limit(limit).all()
    return jsonify([{
        "id": u.update_id,
        "initiative_id": u.initiative_id,
        "content": u.content,
        "image_url": u.image_url,
        "created_at": u.created_at.strftime('%b %d, %Y') if u.created_at else ''
    } for u in updates])

@app.route('/api/admin/updates', methods=['POST'])
def create_update():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    new_update = Update(
        update_id = str(uuid.uuid4()),
        initiative_id = data.get('initiative_id'),
        content = data.get('content'),
        image_url = data.get('image_url', ''),
        created_at = datetime.now()
    )
    try:
        db.session.add(new_update)
        db.session.commit()
        return jsonify({"status": "success", "message": "Update created"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/admin/updates/<update_id>', methods=['DELETE'])
def delete_update(update_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    upd = Update.query.get(update_id)
    if not upd:
        return jsonify({"status": "error", "message": "Not found"}), 404
    db.session.delete(upd)
    db.session.commit()
    return jsonify({"status": "success", "message": "Deleted"})

# ================== MILESTONES API ==================

@app.route('/api/milestones', methods=['GET'])
def get_milestones():
    milestones = Milestone.query.all()
    return jsonify([{
        "id": m.milestone_id,
        "initiative_id": m.initiative_id,
        "title": m.title,
        "description": m.description,
        "is_completed": m.is_completed
    } for m in milestones])

@app.route('/api/admin/milestones', methods=['POST'])
def create_milestone():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.json
    new_milestone = Milestone(
        milestone_id = str(uuid.uuid4()),
        initiative_id = data.get('initiative_id'),
        title = data.get('title'),
        description = data.get('description'),
        is_completed = data.get('is_completed', False)
    )
    db.session.add(new_milestone)
    db.session.commit()
    return jsonify({"status": "success", "message": "Milestone created"}), 201

@app.route('/api/admin/milestones/<milestone_id>', methods=['PUT'])
def update_milestone(milestone_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    m = Milestone.query.get(milestone_id)
    if not m:
        return jsonify({"status": "error", "message": "Not found"}), 404
    data = request.json
    if 'title' in data:
        m.title = data['title']
    if 'description' in data:
        m.description = data['description']
    if 'is_completed' in data:
        m.is_completed = data['is_completed']
    db.session.commit()
    return jsonify({"status": "success", "message": "Milestone updated"})

@app.route('/api/admin/milestones/<milestone_id>', methods=['DELETE'])
def delete_milestone(milestone_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    m = Milestone.query.get(milestone_id)
    if not m:
        return jsonify({"status": "error", "message": "Not found"}), 404
    db.session.delete(m)
    db.session.commit()
    return jsonify({"status": "success", "message": "Deleted"})

# -----------------------------------------------
# RUN
# -----------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)