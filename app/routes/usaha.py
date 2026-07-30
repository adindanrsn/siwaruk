from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_required, current_user
from app.extensions import db
from app.models.business import Business, BIDANG_USAHA_CHOICES, SERTIFIKASI_LIST
from app.utils import get_active_business

usaha_bp = Blueprint('usaha', __name__, url_prefix='/usaha')


def _extract_sertifikasi(form):
    """
    Extract certification data from a submitted form.
    Returns (cert_data dict, errors list).
    cert_data keys: has_halal, halal_number, has_bpom, bpom_number, etc.
    """
    cert_data = {}
    errors = []
    for sert in SERTIFIKASI_LIST:
        key = sert['key']
        label = sert['label']
        has_field = f'has_{key}'
        num_field = f'{key}_number'

        is_selected = form.get(has_field) == '1'
        number_val = form.get(num_field, '').strip()

        cert_data[has_field] = is_selected
        if is_selected:
            if not number_val:
                errors.append(f'Nomor Sertifikat {label} wajib diisi jika sertifikasi {label} dipilih.')
                cert_data[num_field] = ''
            else:
                cert_data[num_field] = number_val
        else:
            cert_data[num_field] = None

    return cert_data, errors


def _apply_sertifikasi(biz, cert_data):
    """Apply certification data dict to a Business instance."""
    for sert in SERTIFIKASI_LIST:
        key = sert['key']
        setattr(biz, f'has_{key}', cert_data[f'has_{key}'])
        setattr(biz, f'{key}_number', cert_data[f'{key}_number'])


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
    Kelola Usaha main menu page for managing the currently active business.
    """
    if current_user.role == 'admin':
        flash('Halaman ini khusus untuk Pemilik Usaha.', 'warning')
        return redirect(url_for('dashboard.index'))

    active_biz = get_active_business()
    return render_template('usaha/kelola.html', active_business=active_biz)


@usaha_bp.route('/pengaturan', methods=['GET'])
@login_required
def pengaturan():
    """
    Pengaturan Usaha dedicated page displaying all businesses owned by the current user.
    """
    if current_user.role == 'admin':
        flash('Halaman ini khusus untuk Pemilik Usaha.', 'warning')
        return redirect(url_for('dashboard.index'))

    businesses = current_user.businesses.all()
    active_biz = get_active_business()
    return render_template(
        'usaha/pengaturan.html',
        businesses=businesses,
        active_business=active_biz,
        bidang_usaha_choices=BIDANG_USAHA_CHOICES,
        sertifikasi_list=SERTIFIKASI_LIST,
    )


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
        bidang_usaha = request.form.get('bidang_usaha', '').strip()

        errors = []
        if not business_name:
            errors.append('Nama Usaha wajib diisi.')
        if not owner_name:
            errors.append('Nama Pemilik wajib diisi.')
        if not bidang_usaha or bidang_usaha not in BIDANG_USAHA_CHOICES:
            errors.append('Bidang Usaha wajib dipilih.')

        # Extract and validate certifications
        cert_data, cert_errors = _extract_sertifikasi(request.form)
        errors.extend(cert_errors)

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return render_template(
                'usaha/tambah.html',
                bidang_usaha_choices=BIDANG_USAHA_CHOICES,
                sertifikasi_list=SERTIFIKASI_LIST,
                form_values=request.form,
            )

        try:
            new_business = Business(
                owner_id=current_user.id,
                business_name=business_name,
                owner_name=owner_name,
                phone=phone or None,
                address=address or None,
                bidang_usaha=bidang_usaha,
            )
            _apply_sertifikasi(new_business, cert_data)

            db.session.add(new_business)
            db.session.commit()

            # Set newly created business as active in session
            session['active_business_id'] = new_business.id

            flash(f'Usaha "{business_name}" berhasil ditambahkan!', 'success')
            return redirect(url_for('usaha.pengaturan'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menambahkan usaha: {str(e)}', 'danger')

    return render_template(
        'usaha/tambah.html',
        bidang_usaha_choices=BIDANG_USAHA_CHOICES,
        sertifikasi_list=SERTIFIKASI_LIST,
        form_values={},
    )


@usaha_bp.route('/edit/<int:business_id>', methods=['POST'])
@login_required
def edit_usaha(business_id):
    """
    Handle POST form submission to edit an existing Business owned by the current user.
    """
    if current_user.role == 'admin':
        flash('Admin tidak dapat mengelola usaha.', 'danger')
        return redirect(url_for('dashboard.index'))

    biz = Business.query.filter_by(id=business_id, owner_id=current_user.id).first_or_404()

    business_name = request.form.get('business_name', '').strip()
    owner_name = request.form.get('owner_name', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    bidang_usaha = request.form.get('bidang_usaha', '').strip()

    errors = []
    if not business_name:
        errors.append('Nama Usaha wajib diisi.')
    if not owner_name:
        errors.append('Nama Pemilik wajib diisi.')
    if not bidang_usaha or bidang_usaha not in BIDANG_USAHA_CHOICES:
        errors.append('Bidang Usaha wajib dipilih.')

    # Extract and validate certifications
    cert_data, cert_errors = _extract_sertifikasi(request.form)
    errors.extend(cert_errors)

    if errors:
        for msg in errors:
            flash(msg, 'danger')
        return redirect(url_for('usaha.pengaturan'))

    try:
        biz.business_name = business_name
        biz.owner_name = owner_name
        biz.phone = phone or None
        biz.address = address or None
        biz.bidang_usaha = bidang_usaha
        _apply_sertifikasi(biz, cert_data)

        db.session.commit()
        flash(f'Data usaha "{business_name}" berhasil diperbarui!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan saat memperbarui usaha: {str(e)}', 'danger')

    return redirect(url_for('usaha.pengaturan'))
