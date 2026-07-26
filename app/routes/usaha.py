from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.business import Business

usaha_bp = Blueprint('usaha', __name__, url_prefix='/usaha')


@usaha_bp.route('/tambah', methods=['GET', 'POST'])
@login_required
def tambah_usaha():
    """
    Route for owners to create a new Business profile.
    Admin accounts are not permitted to create businesses.
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

            flash(f'Usaha "{business_name}" berhasil ditambahkan!', 'success')
            return redirect(url_for('dashboard.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menambahkan usaha: {str(e)}', 'danger')

    return render_template('usaha/tambah.html')
