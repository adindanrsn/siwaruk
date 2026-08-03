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
    Redirect legacy users list route to the new admin dashboard.
    """
    return redirect(url_for('dashboard.index'))


@admin_bp.route('/users/create', methods=['POST'])
@login_required
@admin_required
def create_user():
    """
    Create a new Owner account (Admin only).
    No Business record is created here — owners create their own businesses after login.
    Username is generated automatically from the owner's full name.
    """
    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    role = request.form.get('role', 'owner').strip()

    if not full_name or not phone:
        flash('Nama Lengkap dan Nomor WhatsApp wajib diisi.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Admin accounts must remain purely administrative
    if role not in ['owner']:
        role = 'owner'

    # Generate unique username from full name and a secure temporary password
    username = generate_unique_username(full_name)
    temp_password = generate_secure_password(12)

    try:
        new_user = User(
            username=username,
            full_name=full_name,
            role=role,
            must_change_password=True
        )
        new_user.set_password(temp_password)

        db.session.add(new_user)
        db.session.commit()

        # Save credentials temporarily in session for post-creation modal popup (shown only once)
        session['new_account_created'] = {
            'username': username,
            'temp_password': temp_password,
            'full_name': full_name,
        }
        flash(f'Akun Owner untuk "{full_name}" berhasil dibuat!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan saat membuat akun: {str(e)}', 'danger')

    return redirect(url_for('dashboard.index'))


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
        return redirect(url_for('dashboard.index'))

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

    return redirect(url_for('dashboard.index'))


@admin_bp.route('/users/<int:user_id>/detail', methods=['GET'])
@login_required
@admin_required
def user_detail(user_id):
    """
    Display details of a specific user including their businesses.
    """
    user = User.query.get_or_404(user_id)
    return render_template('admin/detail_akun.html', user=user)


@admin_bp.route('/business/<int:business_id>/detail', methods=['GET'])
@login_required
@admin_required
def business_detail(business_id):
    """
    Display full monitoring details of a specific business (admin view only).
    Includes aggregated stats: products, transactions, income, expense, net profit.
    """
    from sqlalchemy import func
    from app.models.product import Product
    from app.models.sales_transaction import SalesTransaction
    from app.models.expense_transaction import ExpenseTransaction

    biz = Business.query.get_or_404(business_id)

    total_products = Product.query.filter_by(business_id=biz.id).count()

    total_sales_count = SalesTransaction.query.filter_by(business_id=biz.id).count()
    total_expense_count = ExpenseTransaction.query.filter_by(business_id=biz.id).count()
    total_transactions = total_sales_count + total_expense_count

    total_income = db.session.query(
        func.coalesce(func.sum(SalesTransaction.total_amount), 0)
    ).filter_by(business_id=biz.id).scalar()

    total_expense = db.session.query(
        func.coalesce(func.sum(ExpenseTransaction.total_amount), 0)
    ).filter_by(business_id=biz.id).scalar()

    net_profit = total_income - total_expense

    return render_template(
        'admin/detail_usaha.html',
        biz=biz,
        total_products=total_products,
        total_transactions=total_transactions,
        total_income=total_income,
        total_expense=total_expense,
        net_profit=net_profit,
    )


# ─────────────────────────────────────────────────────────────
#  LAPORAN MASUK — Daftar laporan yang dikirim pemilik usaha
# ─────────────────────────────────────────────────────────────
@admin_bp.route('/laporan-masuk', methods=['GET'])
@login_required
@admin_required
def laporan_masuk():
    """
    Tampilkan semua laporan keuangan yang telah dikirim oleh pemilik usaha.
    Admin dapat melihat detail, membuka PDF, dan mengubah status tinjauan.
    """
    from app.models.laporan_terkirim import LaporanTerkirim

    # Filter opsional berdasarkan status
    status_filter = request.args.get('status', '')

    query = LaporanTerkirim.query.order_by(LaporanTerkirim.submitted_at.desc())
    if status_filter and status_filter != 'semua':
        query = query.filter(LaporanTerkirim.status == status_filter)

    laporan_list = query.all()

    # Statistik ringkasan
    total_all      = LaporanTerkirim.query.count()
    total_belum    = LaporanTerkirim.query.filter_by(status=LaporanTerkirim.STATUS_BELUM).count()
    total_ditinjau = LaporanTerkirim.query.filter_by(status=LaporanTerkirim.STATUS_DITINJAU).count()
    total_revisi   = LaporanTerkirim.query.filter_by(status='Perlu Revisi').count()

    return render_template(
        'admin/laporan_masuk.html',
        laporan_list=laporan_list,
        status_filter=status_filter,
        total_all=total_all,
        total_belum=total_belum,
        total_ditinjau=total_ditinjau,
        total_revisi=total_revisi,
    )


@admin_bp.route('/laporan-masuk/<int:laporan_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_status_laporan(laporan_id):
    """
    Ubah status tinjauan laporan yang masuk.
    Menerima POST form dengan field 'status'.
    """
    from app.models.laporan_terkirim import LaporanTerkirim

    record = LaporanTerkirim.query.get_or_404(laporan_id)
    new_status = request.form.get('status', '').strip()

    allowed = [
        LaporanTerkirim.STATUS_BELUM,
        LaporanTerkirim.STATUS_DITINJAU,
        'Perlu Revisi',
    ]
    if new_status not in allowed:
        flash('Status tidak valid.', 'danger')
        return redirect(url_for('admin.laporan_masuk'))

    record.status = new_status
    db.session.commit()
    flash(f'Status laporan berhasil diubah menjadi "{new_status}".', 'success')
    return redirect(url_for('admin.laporan_masuk'))


@admin_bp.route('/laporan-masuk/<int:laporan_id>/pdf', methods=['GET'])
@login_required
@admin_required
def buka_pdf_laporan(laporan_id):
    """
    Buka atau unduh file PDF laporan yang tersimpan di instance folder.
    """
    import os
    from flask import send_from_directory, current_app
    from app.models.laporan_terkirim import LaporanTerkirim

    record = LaporanTerkirim.query.get_or_404(laporan_id)
    if not record.file_path:
        flash('File PDF tidak tersedia untuk laporan ini.', 'warning')
        return redirect(url_for('admin.laporan_masuk'))

    # file_path is relative: "laporan_terkirim/<filename>.pdf"
    directory = os.path.join(current_app.instance_path, 'laporan_terkirim')
    filename  = os.path.basename(record.file_path)

    if not os.path.exists(os.path.join(directory, filename)):
        flash('File PDF tidak ditemukan di server.', 'danger')
        return redirect(url_for('admin.laporan_masuk'))

    return send_from_directory(
        directory,
        filename,
        as_attachment=False,
        mimetype='application/pdf',
    )
