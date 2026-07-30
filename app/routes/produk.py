from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.product import Product
from app.models.category import Category
from app.utils import get_active_business
from sqlalchemy import nulls_last

produk_bp = Blueprint('produk', __name__, url_prefix='/produk')


def _check_owner_and_active_biz():
    """Helper guard for owner role and active business presence."""
    if current_user.role == 'admin':
        flash('Halaman ini khusus untuk Pemilik Usaha.', 'warning')
        return None, redirect(url_for('dashboard.index'))

    active_biz = get_active_business()
    if not active_biz:
        flash('Silakan pilih atau buat usaha terlebih dahulu.', 'warning')
        return None, redirect(url_for('usaha.kelola'))

    return active_biz, None


@produk_bp.route('/', methods=['GET'])
@produk_bp.route('/daftar', methods=['GET'])
@login_required
def index():
    """
    Display product list for active business with Search, Filter by Category, and Sorting.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    # Get query parameters
    search = request.args.get('search', '').strip()
    kategori_id = request.args.get('kategori_id', 'all').strip()
    sort_by = request.args.get('sort', 'created_desc').strip()

    # Base query restricted to active business
    query = Product.query.filter_by(business_id=active_biz.id)

    # 1. Search Filter (by Product Name)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

    # 2. Category Filter
    if kategori_id and kategori_id != 'all':
        try:
            cat_id = int(kategori_id)
            query = query.filter(Product.category_id == cat_id)
        except ValueError:
            kategori_id = 'all'

    # 3. Sorting
    if sort_by == 'name_asc':
        query = query.order_by(Product.name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Product.name.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Product.selling_price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Product.selling_price.desc())
    elif sort_by == 'stock_desc':
        query = query.order_by(nulls_last(Product.stock.desc()))
    elif sort_by == 'stock_asc':
        query = query.order_by(nulls_last(Product.stock.asc()))
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.all()

    # Fetch categories for filter dropdown
    categories = Category.query.filter_by(business_id=active_biz.id).order_by(Category.name.asc()).all()

    return render_template(
        'produk/index.html',
        products=products,
        categories=categories,
        search=search,
        selected_kategori=kategori_id,
        selected_sort=sort_by,
        active_business=active_biz
    )


@produk_bp.route('/tambah', methods=['GET', 'POST'])
@login_required
def tambah():
    """
    Add a new product form & submission handler for active business.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    categories = Category.query.filter_by(business_id=active_biz.id).order_by(Category.name.asc()).all()

    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        price_raw = request.form.get('price', '').strip()
        category_id_raw = request.form.get('category_id', '').strip()
        stock_raw = request.form.get('stock', '').strip()

        errors = []

        # Validate product_name
        if not product_name:
            errors.append('Nama produk wajib diisi.')
        elif len(product_name) > 100:
            errors.append('Nama produk maksimal 100 karakter.')

        # Validate price
        price = None
        if not price_raw:
            errors.append('Harga produk wajib diisi.')
        else:
            try:
                # Clean currency string if any
                clean_price = price_raw.replace('.', '').replace(',', '.').replace('Rp', '').strip()
                price = float(clean_price)
                if price <= 0:
                    errors.append('Harga produk harus lebih dari 0.')
            except ValueError:
                errors.append('Harga produk harus berupa angka yang valid.')

        # Validate category_id
        category_id = None
        if category_id_raw and category_id_raw != '':
            try:
                cat_id_int = int(category_id_raw)
                cat = Category.query.filter_by(id=cat_id_int, business_id=active_biz.id).first()
                if cat:
                    category_id = cat.id
                else:
                    errors.append('Kategori yang dipilih tidak valid.')
            except ValueError:
                pass

        # Validate stock (optional)
        stock = None
        if stock_raw != '':
            try:
                stock_int = int(stock_raw)
                if stock_int < 0:
                    errors.append('Stok tidak boleh bernilai negatif (harus >= 0).')
                else:
                    stock = stock_int
            except ValueError:
                errors.append('Stok harus berupa angka bulat yang valid.')

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return render_template(
                'produk/tambah.html',
                categories=categories,
                form_values=request.form,
                active_business=active_biz
            )

        try:
            new_product = Product(
                business_id=active_biz.id,
                category_id=category_id,
                name=product_name,
                selling_price=price,
                stock=stock
            )
            db.session.add(new_product)
            db.session.commit()

            flash(f'Produk "{product_name}" berhasil ditambahkan!', 'success')
            return redirect(url_for('produk.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat menyimpan produk: {str(e)}', 'danger')

    return render_template(
        'produk/tambah.html',
        categories=categories,
        form_values={},
        active_business=active_biz
    )


@produk_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """
    Edit an existing product form & submission handler.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    product = Product.query.filter_by(id=id, business_id=active_biz.id).first_or_404()
    categories = Category.query.filter_by(business_id=active_biz.id).order_by(Category.name.asc()).all()

    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        price_raw = request.form.get('price', '').strip()
        category_id_raw = request.form.get('category_id', '').strip()
        stock_raw = request.form.get('stock', '').strip()

        errors = []

        # Validate product_name
        if not product_name:
            errors.append('Nama produk wajib diisi.')
        elif len(product_name) > 100:
            errors.append('Nama produk maksimal 100 karakter.')

        # Validate price
        price = None
        if not price_raw:
            errors.append('Harga produk wajib diisi.')
        else:
            try:
                clean_price = price_raw.replace('.', '').replace(',', '.').replace('Rp', '').strip()
                price = float(clean_price)
                if price <= 0:
                    errors.append('Harga produk harus lebih dari 0.')
            except ValueError:
                errors.append('Harga produk harus berupa angka yang valid.')

        # Validate category_id
        category_id = None
        if category_id_raw and category_id_raw != '':
            try:
                cat_id_int = int(category_id_raw)
                cat = Category.query.filter_by(id=cat_id_int, business_id=active_biz.id).first()
                if cat:
                    category_id = cat.id
                else:
                    errors.append('Kategori yang dipilih tidak valid.')
            except ValueError:
                pass

        # Validate stock (optional)
        stock = None
        if stock_raw != '':
            try:
                stock_int = int(stock_raw)
                if stock_int < 0:
                    errors.append('Stok tidak boleh bernilai negatif (harus >= 0).')
                else:
                    stock = stock_int
            except ValueError:
                errors.append('Stok harus berupa angka bulat yang valid.')

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return render_template(
                'produk/edit.html',
                product=product,
                categories=categories,
                form_values=request.form,
                active_business=active_biz
            )

        try:
            product.name = product_name
            product.selling_price = price
            product.category_id = category_id
            product.stock = stock

            db.session.commit()

            flash(f'Produk "{product_name}" berhasil diperbarui!', 'success')
            return redirect(url_for('produk.index'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat memperbarui produk: {str(e)}', 'danger')

    return render_template(
        'produk/edit.html',
        product=product,
        categories=categories,
        form_values={},
        active_business=active_biz
    )


@produk_bp.route('/hapus/<int:id>', methods=['POST'])
@login_required
def hapus(id):
    """
    Delete a product belonging to active business.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    product = Product.query.filter_by(id=id, business_id=active_biz.id).first_or_404()

    try:
        name = product.name
        db.session.delete(product)
        db.session.commit()
        flash(f'Produk "{name}" berhasil dihapus.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus produk: {str(e)}', 'danger')

    return redirect(url_for('produk.index'))


@produk_bp.route('/kategori/tambah', methods=['POST'])
@login_required
def tambah_kategori():
    """
    AJAX / Modal route for creating a new Category for the active business.
    Returns JSON { success: True, category: { id: ..., name: ... } }
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return jsonify({'success': False, 'message': 'Akses ditolak.'}), 403

    # Support JSON payload or Form data
    data = request.get_json(silent=True) or request.form
    category_name = data.get('category_name', '').strip()

    if not category_name:
        return jsonify({'success': False, 'message': 'Nama kategori wajib diisi.'}), 400

    if len(category_name) > 100:
        return jsonify({'success': False, 'message': 'Nama kategori maksimal 100 karakter.'}), 400

    # Check for duplicate category name in active business
    existing = Category.query.filter(
        Category.business_id == active_biz.id,
        Category.name.ilike(category_name)
    ).first()

    if existing:
        return jsonify({
            'success': True,
            'message': 'Kategori sudah ada.',
            'category': {'id': existing.id, 'name': existing.name}
        })

    try:
        new_cat = Category(business_id=active_biz.id, name=category_name)
        db.session.add(new_cat)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Kategori "{category_name}" berhasil dibuat!',
            'category': {'id': new_cat.id, 'name': new_cat.name}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal membuat kategori: {str(e)}'}), 500


@produk_bp.route('/kategori/hapus/<int:id>', methods=['POST'])
@login_required
def hapus_kategori(id):
    """
    Delete a Category for active business. Products belonging to it will have category_id set to NULL.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    cat = Category.query.filter_by(id=id, business_id=active_biz.id).first_or_404()

    try:
        cat_name = cat.name
        db.session.delete(cat)
        db.session.commit()
        flash(f'Kategori "{cat_name}" berhasil dihapus.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus kategori: {str(e)}', 'danger')

    return redirect(url_for('produk.index'))
