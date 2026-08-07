from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.utils import is_valid_whatsapp_number

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route for users. Redirects authenticated users to Beranda.
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

            # If user must change password, redirect directly to Profil Saya
            if user.must_change_password:
                flash('Anda diwajibkan untuk mengganti password terlebih dahulu.', 'warning')
                return redirect(url_for('auth.profil'))

            next_page = request.args.get('next')
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


@auth_bp.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    """
    Profil Saya route combining Account Information and Account Security (Password Change).
    """
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            new_username = request.form.get('username', '').strip()

            if not full_name:
                flash('Nama Lengkap tidak boleh kosong.', 'danger')
                return render_template('auth/profil.html')

            if not new_username:
                flash('Username tidak boleh kosong.', 'danger')
                return render_template('auth/profil.html')
            
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', new_username):
                flash('Username hanya boleh terdiri dari huruf, angka, dan underscore (_), tanpa spasi.', 'danger')
                return render_template('auth/profil.html')
            
            if len(new_username) < 4 or len(new_username) > 30:
                flash('Username harus terdiri dari 4 hingga 30 karakter.', 'danger')
                return render_template('auth/profil.html')
                
            if new_username != current_user.username:
                existing_user = User.query.filter_by(username=new_username).first()
                if existing_user:
                    flash('Username sudah digunakan. Silakan gunakan username lain.', 'danger')
                    return render_template('auth/profil.html')

            if current_user.role == 'admin':
                if not phone:
                    flash('Nomor WhatsApp wajib diisi oleh Admin.', 'danger')
                    return render_template('auth/profil.html')
                if not is_valid_whatsapp_number(phone):
                    flash('Format Nomor WhatsApp tidak valid. Gunakan angka saja (boleh diawali +) dengan panjang 9-15 karakter.', 'danger')
                    return render_template('auth/profil.html')

            username_changed = (new_username != current_user.username)
            current_user.full_name = full_name
            current_user.username = new_username
            current_user.phone = phone or None
            db.session.commit()
            
            if username_changed:
                flash('Informasi akun berhasil diperbarui! Username berhasil diperbarui. Gunakan username baru tersebut pada saat login berikutnya.', 'success')
            else:
                flash('Informasi akun berhasil diperbarui!', 'success')
                
            return redirect(url_for('auth.profil'))

        elif action == 'change_password':
            old_password = request.form.get('old_password', '').strip()
            new_password = request.form.get('new_password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()

            if not old_password or not new_password or not confirm_password:
                flash('Semua kolom password harus diisi.', 'danger')
                return render_template('auth/profil.html')

            if not current_user.check_password(old_password):
                flash('Password lama tidak sesuai. Silakan coba lagi.', 'danger')
                return render_template('auth/profil.html')

            import re
            if len(new_password) < 8 or not re.search(r'[a-zA-Z]', new_password) or not re.search(r'\d', new_password):
                flash('Password minimal terdiri dari 8 karakter serta mengandung minimal 1 huruf dan 1 angka.', 'danger')
                return render_template('auth/profil.html')

            if new_password != confirm_password:
                flash('Konfirmasi password baru tidak cocok.', 'danger')
                return render_template('auth/profil.html')

            current_user.set_password(new_password)
            current_user.must_change_password = False
            db.session.commit()

            flash('Password Anda berhasil diperbarui!', 'success')
            return redirect(url_for('auth.profil'))

        elif action == 'delete_account':
            if current_user.role != 'owner':
                flash('Hanya Pemilik Usaha yang dapat menghapus akunnya sendiri.', 'danger')
                return redirect(url_for('auth.profil'))

            target_user = current_user
            user_fullname = target_user.full_name

            try:
                # Hapus user secara atomik (cascade delete menghapus businesses, products, sales, dll.)
                db.session.delete(target_user)
                db.session.commit()

                # Logout dan redirect ke login
                logout_user()
                flash(f'Akun "{user_fullname}" beserta seluruh data terkait telah berhasil dihapus.', 'success')
                return redirect(url_for('auth.login'))

            except Exception as e:
                db.session.rollback()
                flash(f'Terjadi kesalahan saat menghapus akun: {str(e)}', 'danger')
                return redirect(url_for('auth.profil'))

    return render_template('auth/profil.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """
    Legacy route redirecting to Profil Saya.
    """
    return redirect(url_for('auth.profil'))
