import io
import random
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user

from app.extensions import db
from app.models.sale import Sale
from app.models.sale_detail import SaleDetail
from app.models.expense import Expense
from app.models.sales_transaction import SalesTransaction
from app.models.sales_transaction_item import SalesTransactionItem
from app.models.expense_transaction import ExpenseTransaction
from app.models.product import Product
from app.models.category import Category
from app.utils import get_active_business

# ReportLab imports for Thermal Receipt PDF generation
from reportlab.lib.pagesizes import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepInFrame, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

transaksi_bp = Blueprint('transaksi', __name__, url_prefix='/transaksi')

EXPENSE_CATEGORIES = [
    'Bahan Baku',
    'Operasional',
    'Gaji',
    'Transportasi',
    'Peralatan',
    'Lain-lain',
]

EXPENSE_UNITS = [
    'kg',
    'gram',
    'liter',
    'ml',
    'pcs',
    'pack',
    'dus',
    'orang',
    'ikat',
    'karung',
    'botol',
    'kaleng',
    'lembar',
    'roll',
    'sak',
    'buah',
    'lusin'
]


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


def _generate_invoice_number(business_id):
    """Generate a unique transaction invoice number e.g. TRX-20260731-X89A."""
    date_str = datetime.now().strftime('%Y%m%d')
    while True:
        rand_str = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4))
        inv_no = f"TRX-{date_str}-{rand_str}"
        existing = Sale.query.filter_by(invoice_number=inv_no).first()
        if not existing:
            return inv_no


# ─── 1. DAFTAR / RIWAYAT TRANSAKSI ─────────────────────────────────────────

@transaksi_bp.route('/', methods=['GET'])
@transaksi_bp.route('/riwayat', methods=['GET'])
@login_required
def riwayat():
    """
    Combined history of sales (pemasukan) and expenses (pengeluaran) for active business.
    Supports combined filtering by jenis (type) and waktu (time range).
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    jenis_filter = request.args.get('jenis', 'semua').strip()   # semua | pemasukan | pengeluaran
    waktu_filter = request.args.get('waktu', 'semua').strip()   # semua | hari_ini | minggu_ini | bulan_ini | tahun_ini
    search       = request.args.get('search', '').strip()

    # ── Compute date range based on waktu filter ──────────────────────────────
    from zoneinfo import ZoneInfo
    from datetime import timezone as _tz
    _WIB = ZoneInfo('Asia/Jakarta')

    now   = datetime.now(_WIB)
    start = None   # None means no lower bound (semua)

    if waktu_filter == 'hari_ini':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(_tz.utc).replace(tzinfo=None)
    elif waktu_filter == 'minggu_ini':
        # Monday of current week
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(_tz.utc).replace(tzinfo=None)
    elif waktu_filter == 'bulan_ini':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(_tz.utc).replace(tzinfo=None)
    elif waktu_filter == 'tahun_ini':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(_tz.utc).replace(tzinfo=None)
    # else 'semua' → start stays None

    # ── Fetch Sales (Pemasukan) ───────────────────────────────────────────────
    sales_query = Sale.query.filter_by(business_id=active_biz.id)
    if search:
        sales_query = sales_query.filter(Sale.invoice_number.ilike(f'%{search}%'))
    if start:
        sales_query = sales_query.filter(Sale.transaction_date >= start)
    sales = sales_query.order_by(Sale.transaction_date.desc()).all() \
            if jenis_filter in ['semua', 'pemasukan'] else []

    # ── Fetch Expenses (Pengeluaran) ──────────────────────────────────────────
    exp_query = Expense.query.filter_by(business_id=active_biz.id)
    if search:
        exp_query = exp_query.filter(
            (Expense.description.ilike(f'%{search}%')) |
            (Expense.category_name.ilike(f'%{search}%'))
        )
    if start:
        exp_query = exp_query.filter(Expense.expense_date >= start)
    expenses = exp_query.order_by(Expense.expense_date.desc()).all() \
               if jenis_filter in ['semua', 'pengeluaran'] else []

    def _to_wib(dt):
        if dt is None:
            return dt
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_tz.utc)
        return dt.astimezone(_WIB)

    # ── Combine into unified history list ─────────────────────────────────────
    history_items = []

    for s in sales:
        history_items.append({
            'id': s.id,
            'type': 'pemasukan',
            'type_label': 'Pemasukan',
            'transaction_number': s.invoice_number,
            'date': _to_wib(s.transaction_date),
            'total': float(s.total),
            'payment_method': s.payment_method or '-',
            'method_or_category': s.payment_method,
            'details_count': len(s.sale_details),
            'obj': s
        })

    for e in expenses:
        cat_disp = e.category_name or (e.expense_category.name if e.expense_category else 'Pengeluaran')
        history_items.append({
            'id': e.id,
            'type': 'pengeluaran',
            'type_label': 'Pengeluaran',
            'transaction_number': f"EXP-{e.id:05d}",
            'date': _to_wib(e.expense_date),
            'total': float(e.amount),
            'payment_method': cat_disp,
            'method_or_category': cat_disp,
            'details_count': 1,
            'obj': e
        })

    # Sort descending by date
    history_items.sort(key=lambda x: x['date'], reverse=True)

    return render_template(
        'transaksi/riwayat.html',
        history_items=history_items,
        jenis_filter=jenis_filter,
        waktu_filter=waktu_filter,
        search=search,
        active_business=active_biz
    )


# ─── 2. TRANSAKSI PEMASUKAN (POS KASIR) ───────────────────────────────────

@transaksi_bp.route('/pemasukan', methods=['GET', 'POST'])
@login_required
def pemasukan():
    """
    POS Cashier page for creating sales transactions.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    if request.method == 'POST':
        # Handles JSON payload from cashier cart
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'success': False, 'message': 'Data transaksi tidak ditemukan.'}), 400

        cart_items = data.get('items', [])
        payment_method = data.get('payment_method', '').strip()
        notes = data.get('notes', '').strip()

        if not cart_items or len(cart_items) == 0:
            return jsonify({'success': False, 'message': 'Keranjang transaksi minimal harus berisi 1 produk.'}), 400

        if not payment_method or payment_method not in ['Tunai', 'Non Tunai']:
            return jsonify({'success': False, 'message': 'Metode pembayaran wajib dipilih (Tunai / Non Tunai).'}), 400

        try:
            total_sale = 0.0
            sale_details_to_add = []
            products_to_update = []

            for item in cart_items:
                product_id = item.get('product_id')
                qty = int(item.get('quantity', 1))

                if qty <= 0:
                    continue

                prod = Product.query.filter_by(id=product_id, business_id=active_biz.id).first()
                if not prod:
                    return jsonify({'success': False, 'message': f'Produk dengan ID {product_id} tidak ditemukan.'}), 400

                unit_price = float(prod.selling_price)
                subtotal = unit_price * qty
                total_sale += subtotal

                # Deduct stock if stock is recorded (NOT NULL)
                if prod.stock is not None:
                    if prod.stock <= 0:
                        return jsonify({'success': False, 'message': f'Stok produk "{prod.name}" sudah habis.'}), 400
                    if prod.stock < qty:
                        return jsonify({'success': False, 'message': f'Stok produk "{prod.name}" tidak mencukupi (sisa: {prod.stock}).'}), 400
                    
                    prod.stock -= qty
                    products_to_update.append(prod)

                detail = SaleDetail(
                    product_id=prod.id,
                    quantity=qty,
                    selling_price=unit_price,
                    subtotal=subtotal
                )
                sale_details_to_add.append(detail)

            # Create SalesTransaction & Sale headers
            inv_number = _generate_invoice_number(active_biz.id)
            
            sales_tx = SalesTransaction(
                business_id=active_biz.id,
                transaction_code=inv_number,
                payment_method=payment_method,
                total_amount=total_sale
            )
            db.session.add(sales_tx)
            db.session.flush()

            new_sale = Sale(
                business_id=active_biz.id,
                invoice_number=inv_number,
                transaction_date=sales_tx.created_at,
                total=total_sale,
                payment_method=payment_method,
                notes=notes or None
            )
            db.session.add(new_sale)
            db.session.flush()

            for d in sale_details_to_add:
                d.sale_id = new_sale.id
                db.session.add(d)

                tx_item = SalesTransactionItem(
                    sales_transaction_id=sales_tx.id,
                    product_id=d.product_id,
                    quantity=d.quantity,
                    price=d.selling_price,
                    subtotal=d.subtotal
                )
                db.session.add(tx_item)

            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Transaksi {inv_number} berhasil disimpan!',
                'sale_id': new_sale.id,
                'invoice_number': inv_number,
                'redirect_url': url_for('transaksi.riwayat')
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Terjadi kesalahan: {str(e)}'}), 500

    # GET Request: Render POS Kasir Interface
    products = Product.query.filter_by(business_id=active_biz.id, is_active=True).order_by(Product.name.asc()).all()
    categories = Category.query.filter_by(business_id=active_biz.id).order_by(Category.name.asc()).all()

    return render_template(
        'transaksi/pemasukan.html',
        products=products,
        categories=categories,
        active_business=active_biz
    )

# ─── QUICK RESTOCK ───────────────────────────────────────────────────────────

@transaksi_bp.route('/quick-restock/<int:id>', methods=['POST'])
@login_required
def quick_restock(id):
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect
        
    product = Product.query.filter_by(id=id, business_id=active_biz.id).first()
    if not product:
        return jsonify({'success': False, 'message': 'Produk tidak ditemukan.'}), 404
        
    if product.stock is None:
        return jsonify({'success': False, 'message': 'Produk ini tidak menggunakan fitur stok.'}), 400
        
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'message': 'Data tidak valid.'}), 400
        
    add_qty = data.get('add_stock')
    try:
        add_qty = int(add_qty)
        if add_qty <= 0:
            return jsonify({'success': False, 'message': 'Jumlah restock harus lebih dari 0.'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Jumlah restock harus berupa angka valid.'}), 400
        
    product.stock += add_qty
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Stok berhasil ditambahkan.',
        'new_stock': product.stock
    })
# ─── 3. TRANSAKSI PENGELUARAN ───────────────────────────────────────────────

@transaksi_bp.route('/pengeluaran/tambah', methods=['POST'])
@login_required
def tambah_pengeluaran():
    """
    Record an operational expense for active business (POST only).
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    description = request.form.get('description', '').strip()
    category_name = request.form.get('category_name', '').strip()
    quantity_raw = request.form.get('quantity', '1').strip()
    unit = request.form.get('unit', '').strip()
    amount_raw = request.form.get('amount', '').strip()
    notes = request.form.get('notes', '').strip()

    errors = []

    if not description:
        errors.append('Keperluan pengeluaran wajib diisi.')

    if not category_name:
        errors.append('Kategori pengeluaran wajib dipilih.')

    quantity = 1.0
    if quantity_raw:
        try:
            quantity = float(quantity_raw)
            if quantity <= 0:
                errors.append('Jumlah harus lebih dari 0.')
        except ValueError:
            errors.append('Jumlah harus berupa angka yang valid.')

    amount = 0.0
    if not amount_raw:
        errors.append('Total pengeluaran wajib diisi.')
    else:
        try:
            clean_amount = amount_raw.replace('.', '').replace(',', '.').replace('Rp', '').strip()
            amount = float(clean_amount)
            if amount <= 0:
                errors.append('Total pengeluaran harus lebih dari 0.')
        except ValueError:
            errors.append('Total pengeluaran harus berupa angka yang valid.')

    if errors:
        for msg in errors:
            flash(msg, 'danger')
        search_exp = request.args.get('search', '').strip()
        filter_cat = request.args.get('category', '').strip()
        expenses_list = Expense.query.filter_by(business_id=active_biz.id).order_by(Expense.expense_date.desc()).all()
        return render_template(
            'transaksi/pengeluaran.html',
            expense_categories=EXPENSE_CATEGORIES,
            expense_units=EXPENSE_UNITS,
            form_values=request.form,
            expenses=expenses_list,
            search_exp=search_exp,
            filter_cat=filter_cat,
            active_business=active_biz
        )

    try:
        exp_code = f"EXP-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        
        exp_tx = ExpenseTransaction(
            business_id=active_biz.id,
            transaction_code=exp_code,
            purpose=description,
            category=category_name,
            quantity=quantity,
            unit=unit or None,
            total_amount=amount,
            notes=notes or None
        )
        db.session.add(exp_tx)

        new_expense = Expense(
            business_id=active_biz.id,
            category_name=category_name,
            description=description,
            quantity=quantity,
            unit=unit or None,
            amount=amount,
            expense_date=datetime.utcnow(),
            notes=notes or None
        )
        db.session.add(new_expense)
        db.session.commit()

        flash('Transaksi pengeluaran berhasil disimpan!', 'success')
        return redirect(url_for('transaksi.pengeluaran'))

    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan saat menyimpan pengeluaran: {str(e)}', 'danger')
        return redirect(url_for('transaksi.pengeluaran'))


@transaksi_bp.route('/pengeluaran', methods=['GET'])
@login_required
def pengeluaran():
    """
    View operational expenses for active business.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    # GET: fetch existing expenses for riwayat table
    search_exp = request.args.get('search', '').strip()
    filter_cat = request.args.get('category', '').strip()
    
    exp_query = Expense.query.filter_by(business_id=active_biz.id)
    if search_exp:
        exp_query = exp_query.filter(
            (Expense.description.ilike(f'%{search_exp}%'))
        )
    if filter_cat:
        exp_query = exp_query.filter(Expense.category_name == filter_cat)
        
    expenses_list = exp_query.order_by(Expense.expense_date.desc()).all()

    return render_template(
        'transaksi/pengeluaran.html',
        expense_categories=EXPENSE_CATEGORIES,
        expense_units=EXPENSE_UNITS,
        form_values={},
        expenses=expenses_list,
        search_exp=search_exp,
        filter_cat=filter_cat,
        active_business=active_biz
    )


@transaksi_bp.route('/pengeluaran/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_pengeluaran(id):
    """
    Edit an existing operational expense transaction for active business.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    expense = Expense.query.filter_by(id=id, business_id=active_biz.id).first_or_404()

    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        category_name = request.form.get('category_name', '').strip()
        quantity_raw = request.form.get('quantity', '1').strip()
        unit = request.form.get('unit', '').strip()
        amount_raw = request.form.get('amount', '').strip()
        notes = request.form.get('notes', '').strip()

        errors = []

        if not description:
            errors.append('Keperluan pengeluaran wajib diisi.')

        if not category_name:
            errors.append('Kategori pengeluaran wajib dipilih.')

        quantity = 1.0
        if quantity_raw:
            try:
                quantity = float(quantity_raw)
                if quantity <= 0:
                    errors.append('Jumlah harus lebih dari 0.')
            except ValueError:
                errors.append('Jumlah harus berupa angka yang valid.')

        amount = 0.0
        if not amount_raw:
            errors.append('Total pengeluaran wajib diisi.')
        else:
            try:
                clean_amount = amount_raw.replace('.', '').replace(',', '.').replace('Rp', '').strip()
                amount = float(clean_amount)
                if amount <= 0:
                    errors.append('Total pengeluaran harus lebih dari 0.')
            except ValueError:
                errors.append('Total pengeluaran harus berupa angka yang valid.')

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return render_template(
                'transaksi/edit_pengeluaran.html',
                expense=expense,
                expense_categories=EXPENSE_CATEGORIES,
                expense_units=EXPENSE_UNITS,
                form_values=request.form,
                active_business=active_biz
            )

        try:
            expense.description = description
            expense.category_name = category_name
            expense.quantity = quantity
            expense.unit = unit or None
            expense.amount = amount
            expense.notes = notes or None

            exp_tx = ExpenseTransaction.query.filter_by(business_id=active_biz.id, id=id).first()
            if exp_tx:
                exp_tx.purpose = description
                exp_tx.category = category_name
                exp_tx.quantity = quantity
                exp_tx.unit = unit or None
                exp_tx.total_amount = amount
                exp_tx.notes = notes or None

            db.session.commit()
            flash('Transaksi pengeluaran berhasil diperbarui!', 'success')
            return redirect(url_for('transaksi.pengeluaran'))

        except Exception as e:
            db.session.rollback()
            flash(f'Terjadi kesalahan saat memperbarui pengeluaran: {str(e)}', 'danger')

    return render_template(
        'transaksi/edit_pengeluaran.html',
        expense=expense,
        expense_categories=EXPENSE_CATEGORIES,
        expense_units=EXPENSE_UNITS,
        form_values={},
        active_business=active_biz
    )


# ─── 4. DETAIL TRANSAKSI (AJAX & VIEW) ─────────────────────────────────────

@transaksi_bp.route('/detail/<int:id>', methods=['GET'])
@login_required
def detail(id):
    """
    Get detailed JSON data for a sales transaction.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return jsonify({'success': False, 'message': 'Akses ditolak.'}), 403

    sale = Sale.query.filter_by(id=id, business_id=active_biz.id).first()
    if not sale:
        return jsonify({'success': False, 'message': 'Transaksi tidak ditemukan.'}), 404

    from zoneinfo import ZoneInfo
    from datetime import timezone as _tz
    _wib_dt = sale.transaction_date.replace(tzinfo=_tz.utc).astimezone(ZoneInfo('Asia/Jakarta'))

    items = []
    for d in sale.sale_details:
        items.append({
            'product_name': d.product.name if d.product else 'Produk Dihapus',
            'quantity': d.quantity,
            'selling_price': float(d.selling_price),
            'subtotal': float(d.subtotal)
        })

    return jsonify({
        'success': True,
        'id': sale.id,
        'business_name': active_biz.business_name,
        'business_address': active_biz.address or '-',
        'business_phone': active_biz.phone or '-',
        'invoice_number': sale.invoice_number,
        'date': _wib_dt.strftime('%d/%m/%Y'),
        'time': _wib_dt.strftime('%H:%M'),
        'payment_method': sale.payment_method,
        'total': float(sale.total),
        'items': items,
        'items_count': len(items)
    })


@transaksi_bp.route('/preview-nota/<int:id>', methods=['GET'])
@login_required
def preview_nota(id):
    """
    Render Preview Nota page for a sale transaction.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    sale = Sale.query.filter_by(id=id, business_id=active_biz.id).first_or_404()

    return render_template(
        'transaksi/preview_nota.html',
        sale=sale,
        active_business=active_biz
    )


@transaksi_bp.route('/detail-pengeluaran/<int:id>', methods=['GET'])
@login_required
def detail_pengeluaran(id):
    """
    Get detailed JSON data for an expense transaction (for modal display).
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return jsonify({'success': False, 'message': 'Akses ditolak.'}), 403

    expense = Expense.query.filter_by(id=id, business_id=active_biz.id).first()
    if not expense:
        return jsonify({'success': False, 'message': 'Transaksi tidak ditemukan.'}), 404

    cat_display = expense.category_name or (
        expense.expense_category.name if expense.expense_category else '-'
    )
    qty_display = f"{float(expense.quantity):g}" if expense.quantity is not None else '1'

    return jsonify({
        'success': True,
        'id': expense.id,
        'transaction_number': f"EXP-{expense.id:05d}",
        'description': expense.description,
        'category': cat_display,
        'quantity': qty_display,
        'unit': expense.unit or '',
        'amount': float(expense.amount),
        'amount_formatted': f"{int(expense.amount):,}".replace(',', '.'),
        'date': expense.expense_date.strftime('%d/%m/%Y'),
        'time': expense.expense_date.strftime('%H:%M'),
        'notes': expense.notes or '-',
    })


# ─── 5. DOWNLOAD NOTA PDF (THERMAL RECEIPT FORMAT) ──────────────────────────

@transaksi_bp.route('/nota/<int:id>', methods=['GET'])
@login_required
def download_nota(id):
    """
    Generate and download thermal receipt PDF for a sale transaction.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    sale = Sale.query.filter_by(id=id, business_id=active_biz.id).first_or_404()

    # Create memory buffer for PDF
    buffer = io.BytesIO()

    # Define 80mm thermal receipt page size (width=80mm, height=220mm)
    page_width = 80 * mm
    page_height = 240 * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(page_width, page_height),
        leftMargin=4 * mm,
        rightMargin=4 * mm,
        topMargin=6 * mm,
        bottomMargin=6 * mm
    )

    styles = getSampleStyleSheet()

    # Custom thermal receipt typography styles
    style_center_bold = ParagraphStyle('CenterBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12, alignment=TA_CENTER)
    style_center = ParagraphStyle('Center', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, alignment=TA_CENTER)
    style_left = ParagraphStyle('Left', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, alignment=TA_LEFT)
    style_left_bold = ParagraphStyle('LeftBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_LEFT)
    style_right = ParagraphStyle('Right', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, alignment=TA_RIGHT)
    style_right_bold = ParagraphStyle('RightBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_RIGHT)

    from zoneinfo import ZoneInfo
    from datetime import timezone as _tz
    _wib_dt = sale.transaction_date.replace(tzinfo=_tz.utc).astimezone(ZoneInfo('Asia/Jakarta'))

    elements = []

    # 1. Header: Business Name & Info
    if hasattr(active_biz, 'logo') and active_biz.logo:
        try:
            import os
            from flask import current_app
            logo_val = active_biz.logo
            if logo_val.startswith('/'):
                logo_path = os.path.join(current_app.root_path, logo_val.lstrip('/'))
            else:
                logo_path = logo_val
            img = Image(logo_path, width=20*mm, height=20*mm)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 2*mm))
        except Exception:
            pass

    elements.append(Paragraph(active_biz.business_name.upper(), style_center_bold))
    address = active_biz.address if active_biz.address else '-'
    elements.append(Paragraph(address, style_center))
    phone = active_biz.phone if active_biz.phone else '-'
    elements.append(Paragraph(f"WA/Telp: {phone}", style_center))

    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.75, color=colors.black, spaceAfter=2*mm))

    # 2. Transaction Info
    info_table_data = [
        [Paragraph("<b>No. Transaksi:</b>", style_left), Paragraph(sale.invoice_number, style_right)],
        [Paragraph("<b>Tanggal & Jam:</b>", style_left), Paragraph(_wib_dt.strftime('%d/%m/%Y %H:%M WIB'), style_right)],
        [Paragraph("<b>Metode Pembayaran:</b>", style_left), Paragraph(sale.payment_method, style_right)],
    ]
    t_info = Table(info_table_data, colWidths=[33*mm, 39*mm])
    t_info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))
    elements.append(t_info)

    elements.append(HRFlowable(width="100%", thickness=0.75, color=colors.black, spaceBefore=2*mm, spaceAfter=2*mm))

    # 3. Product Items Table
    items_data = [
        [Paragraph("<b>Item</b>", style_left_bold), Paragraph("<b>Total</b>", style_right_bold)]
    ]

    for detail in sale.sale_details:
        p_name = detail.product.name if detail.product else 'Produk Dihapus'
        item_title = Paragraph(f"<b>{p_name}</b>", style_left)
        subtotal_str = f"Rp {int(detail.subtotal):,}".replace(',', '.')
        subtotal_p = Paragraph(f"<b>{subtotal_str}</b>", style_right)
        items_data.append([item_title, subtotal_p])

        # Second row: qty x price
        qty_price_str = f"{detail.quantity} x Rp {int(detail.selling_price):,}".replace(',', '.')
        qty_p = Paragraph(f"&nbsp;&nbsp;{qty_price_str}", style_left)
        items_data.append([qty_p, Paragraph("", style_right)])

    t_items = Table(items_data, colWidths=[46*mm, 26*mm])
    t_items.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('TOPPADDING', (0,0), (-1,-1), 1),
    ]))
    elements.append(t_items)

    elements.append(HRFlowable(width="100%", thickness=0.75, color=colors.black, spaceBefore=2*mm, spaceAfter=2*mm))

    # 4. Total Row
    total_formatted = f"Rp {int(sale.total):,}".replace(',', '.')
    tot_table_data = [
        [Paragraph("<b>TOTAL PEMBAYARAN:</b>", ParagraphStyle('TotL', parent=style_left_bold, fontSize=8.5)),
         Paragraph(f"<b>{total_formatted}</b>", ParagraphStyle('TotR', parent=style_right_bold, fontSize=11))]
    ]
    t_tot = Table(tot_table_data, colWidths=[38*mm, 34*mm])
    t_tot.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_tot)

    elements.append(Spacer(1, 5 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.gray, spaceAfter=3*mm))

    # 5. Footer
    elements.append(Paragraph("Terima kasih telah berbelanja.", style_center_bold))

    # 6. QR Code (Optional)
    try:
        elements.append(Spacer(1, 4*mm))
        qr_code = qr.QrCodeWidget(sale.invoice_number)
        bounds = qr_code.getBounds()
        w = bounds[2] - bounds[0]
        h = bounds[3] - bounds[1]
        size = 22 * mm
        d = Drawing(size, size, transform=[size/w, 0, 0, size/h, 0, 0])
        d.add(qr_code)
        qr_flowable = KeepInFrame(80*mm, size, [d], hAlign='CENTER', vAlign='MIDDLE')
        elements.append(qr_flowable)
    except Exception:
        pass

    # Build PDF document
    doc.build(elements)

    buffer.seek(0)
    filename = f"Nota_{sale.invoice_number}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ─── 6. HAPUS TRANSAKSI ──────────────────────────────────────────────────

@transaksi_bp.route('/hapus/<string:item_type>/<int:id>', methods=['POST'])
@login_required
def hapus(item_type, id):
    """
    Delete a sale or expense transaction for active business.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    try:
        if item_type == 'pemasukan':
            sale = Sale.query.filter_by(id=id, business_id=active_biz.id).first_or_404()
            inv = sale.invoice_number
            db.session.delete(sale)
            db.session.commit()
            flash(f'Transaksi {inv} berhasil dihapus.', 'success')
            return redirect(url_for('transaksi.riwayat'))
        else:
            flash('Jenis transaksi tidak valid.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus transaksi: {str(e)}', 'danger')
    return redirect(url_for('transaksi.riwayat'))


@transaksi_bp.route('/pengeluaran/<int:id>/delete', methods=['POST'])
@login_required
def hapus_pengeluaran(id):
    """
    Delete an expense transaction for active business.
    """
    active_biz, err_redirect = _check_owner_and_active_biz()
    if err_redirect:
        return err_redirect

    try:
        expense = Expense.query.filter_by(id=id, business_id=active_biz.id).first_or_404()
        desc = expense.description
        db.session.delete(expense)
        db.session.commit()
        flash(f'Pengeluaran "{desc}" berhasil dihapus.', 'success')
        return redirect(url_for('transaksi.pengeluaran'))
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus pengeluaran: {str(e)}', 'danger')
        return redirect(url_for('transaksi.pengeluaran'))

# ─── 7. LAIN-LAIN ────────────────────────────────────────────────────────

