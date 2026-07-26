from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app.extensions import db
from app.models.business import Business
from app.utils import get_active_business

usaha_bp = Blueprint('usaha', __name__, url_prefix='/usaha')


@usaha_bp.route('/set-active/<int:business_id>', methods=['GET', 'POST'])
@login_required
def set_active(business_id):
    """
    Set the active business in session for the current owner.
    """
    if current_user.role != 'owner':
        flash('Akses ditolak.', 'danger')
        return redirect(url_for('dashboard.index'))

    biz = Business.query.filter_by(id=business_id, owner_id=current_user.id).first_or_404()
    session['active_business_id'] = biz.id
    flash(f'Usaha aktif diubah ke "{biz.business_name}".', 'info')

    next_url = request.referrer or url_for('dashboard.index')
    return redirect(next_url)


@usaha_bp.route('/kelola', methods=['GET'])
@login_required
def kelola():
    """
    Kelola Usaha main page for managing the currently active business.
    """
    if current_user.role == 'admin':
        flash('Halaman ini khusus untuk Pemilik Usaha.', 'warning')
        return redirect(url_for('dashboard.index'))

    active_biz = get_active_business()
    return render_template('usaha/kelola.html', active_business=active_biz)


@usaha_bp.route('/tambah', methods=['GET', 'POST'])
@login_required
def tambah_usaha():
    """
    Route for owners to create a new Business profile.
    Automatically sets the newly created business as active in session.
    """
    if current_user.role == 'admin':
        flash('Admin tidak dapat memiliki usaha.', 'danger')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        business_name = request.form.get('business_name', '').strip()
        owner_name = request.form.get('owner_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        if not business_name or not owner_name:
            flash('Nama Usaha dan Nama Pemilik wajib diisi.', 'danger')
            return render_template('usaha/tambah.html')

        try:
            new_business = Business(
                owner_id=current_user.id,
                business_name=business_name,
                owner_name=owner_name,
                phone=phone or None,
                address=address or None
            )
            db.session.add(new_business)
            db.session.commit()

            # Set newly created business as active in session
            session['active_business_id'] = new_business.id

            flash(f'Usaha "{business_name}" berhasil ditambahkan!', 'success')
            return redirect(url_for('dashboard.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menambahkan usaha: {str(e)}', 'danger')

    return render_template('usaha/tambah.html')
