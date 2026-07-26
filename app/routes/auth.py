from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route for users. Redirects authenticated users to the dashboard.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = True if request.form.get('remember') else False

        if not username or not password:
            flash('Username dan password harus diisi.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Selamat datang kembali, {user.full_name}!', 'success')

            # If user must change password, redirect directly to change-password
            if user.must_change_password:
                flash('Anda diwajibkan untuk mengganti password terlebih dahulu.', 'warning')
                return redirect(url_for('auth.change_password'))

            next_page = request.args.get('next')
            # Validate next parameter to prevent open redirect vulnerabilities
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Username atau password salah. Silakan coba lagi.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Logout route to clear user session.
    """
    logout_user()
    flash('Anda telah berhasil keluar dari sistem.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    Change password route for authenticated users.
    """
    if request.method == 'POST':
        old_password = request.form.get('old_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not old_password or not new_password or not confirm_password:
            flash('Semua kolom password harus diisi.', 'danger')
            return render_template('auth/change_password.html')

        # 1. Validate old password
        if not current_user.check_password(old_password):
            flash('Password lama tidak sesuai. Silakan coba lagi.', 'danger')
            return render_template('auth/change_password.html')

        # 2. Validate new password length (min 8 characters)
        if len(new_password) < 8:
            flash('Password baru minimal harus 8 karakter.', 'danger')
            return render_template('auth/change_password.html')

        # 3. Validate password confirmation match
        if new_password != confirm_password:
            flash('Konfirmasi password baru tidak cocok.', 'danger')
            return render_template('auth/change_password.html')

        # Update user password and set must_change_password to False
        current_user.set_password(new_password)
        current_user.must_change_password = False
        db.session.commit()

        flash('Password Anda berhasil diperbarui!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/change_password.html')
