from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.business import Business
from app.utils import generate_unique_username, generate_secure_password

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """
    Decorator to restrict route access strictly to users with admin role.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Akses ditolak. Halaman ini hanya dapat diakses oleh Administrator.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
def users_list():
    """
    Display list of all registered system users, new account modals, or reset password results.
    """
    users = User.query.order_by(User.created_at.desc()).all()
    new_account = session.pop('new_account_created', None)
    reset_info = session.pop('reset_password_success', None)
    return render_template('admin/users.html', users=users, new_account=new_account, reset_info=reset_info)


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    """
    Create a new user account & business profile atomically (Admin only).
    """
    business_name = request.form.get('business_name', '').strip()
    owner_name = request.form.get('owner_name', '').strip()
    phone = request.form.get('phone', '').strip()
    role = request.form.get('role', 'owner').strip()

    if not business_name or not owner_name or not phone:
        flash('Nama Usaha, Nama Pemilik, dan Nomor WhatsApp wajib diisi.', 'danger')
        return redirect(url_for('admin.users_list'))

    # Generate unique username and secure temporary password using secrets
    username = generate_unique_username(business_name)
    temp_password = generate_secure_password(12)

    try:
        # Single atomic database transaction
        new_user = User(
            username=username,
            full_name=owner_name,
            role=role if role in ['admin', 'owner'] else 'owner',
            must_change_password=True
        )
        new_user.set_password(temp_password)

        db.session.add(new_user)
        db.session.flush()  # Populates new_user.id for Business foreign key

        new_business = Business(
            user_id=new_user.id,
            business_name=business_name,
            owner_name=owner_name,
            phone=phone
        )
        db.session.add(new_business)
        db.session.commit()

        # Save credentials temporarily in session for post-creation modal popup (shown only once)
        session['new_account_created'] = {
            'username': username,
            'temp_password': temp_password,
            'business_name': business_name,
            'owner_name': owner_name,
            'phone': phone
        }
        flash(f'Akun untuk "{business_name}" berhasil dibuat!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan saat membuat akun: {str(e)}', 'danger')

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    """
    Reset password for a specified non-admin user using a secrets-generated temporary password.
    """
    user = User.query.get_or_404(user_id)

    # Reject resetting password for admin users
    if user.role == 'admin':
        flash('Password akun Admin tidak dapat direset dari halaman ini.', 'danger')
        return redirect(url_for('admin.users_list'))

    # Generate temporary password using secrets module (min 10 chars, uppercase, lowercase, numbers)
    temp_password = generate_secure_password(12)

    try:
        user.set_password(temp_password)
        user.must_change_password = True
        db.session.commit()

        # Store reset result in session for one-time modal display
        session['reset_password_success'] = {
            'username': user.username,
            'temp_password': temp_password,
            'full_name': user.full_name
        }
        flash(f'Password untuk akun "{user.full_name}" ({user.username}) berhasil di-reset.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Gagal mereset password: {str(e)}', 'danger')

    return redirect(url_for('admin.users_list'))
