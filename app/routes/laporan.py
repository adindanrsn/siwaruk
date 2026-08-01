from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.sale import Sale
from app.models.sale_detail import SaleDetail
from app.models.expense import Expense
from app.utils import get_active_business
from sqlalchemy import func
from datetime import datetime, timedelta, timezone as _tz
from zoneinfo import ZoneInfo
import calendar
import io
import openpyxl

# PDF Export imports
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

laporan_bp = Blueprint('laporan', __name__, url_prefix='/laporan')
_WIB = ZoneInfo('Asia/Jakarta')

def _check_owner_and_active_biz():
    active_biz = get_active_business()
    if not active_biz:
        flash('Pilih atau buat usaha terlebih dahulu.', 'warning')
        return None, redirect(url_for('usaha.kelola'))
    if current_user.role != 'owner':
        flash('Anda tidak memiliki akses ke halaman laporan.', 'danger')
        return None, redirect(url_for('dashboard.index'))
    return active_biz, None

def get_date_range(periode, start_str, end_str):
    now = datetime.now(_WIB)
    start_wib, end_wib = None, None
    
    if periode == 'hari_ini':
        start_wib = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_wib = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif periode == 'minggu_ini':
        start_wib = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_wib = (start_wib + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
    elif periode == 'bulan_ini':
        start_wib = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(now.year, now.month)[1]
        end_wib = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
    elif periode == 'tahun_ini':
        start_wib = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_wib = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    elif periode == 'custom' and start_str and end_str:
        try:
            st = datetime.strptime(start_str, '%Y-%m-%d').replace(tzinfo=_WIB)
            en = datetime.strptime(end_str, '%Y-%m-%d').replace(tzinfo=_WIB)
            start_wib = st.replace(hour=0, minute=0, second=0, microsecond=0)
            end_wib = en.replace(hour=23, minute=59, second=59, microsecond=999999)
        except ValueError:
            pass

    # Fallback to bulan_ini if invalid custom or missing
    if not start_wib or not end_wib:
        start_wib = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = calendar.monthrange(now.year, now.month)[1]
        end_wib = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
        periode = 'bulan_ini'

    return start_wib, end_wib, periode

def to_utc_naive(dt_wib):
    return dt_wib.astimezone(_tz.utc).replace(tzinfo=None)

def from_utc_naive(dt_utc):
    if dt_utc is None: return None
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=_tz.utc)
    return dt_utc.astimezone(_WIB)

def get_report_data(active_biz, start_wib, end_wib, periode):
    start_utc = to_utc_naive(start_wib)
    end_utc = to_utc_naive(end_wib)

    # 1. Total Pemasukan
    sales = Sale.query.filter(
        Sale.business_id == active_biz.id,
        Sale.transaction_date >= start_utc,
        Sale.transaction_date <= end_utc
    ).all()
    total_pemasukan = sum(s.total for s in sales)

    # 2. Total Pengeluaran
    expenses = Expense.query.filter(
        Expense.business_id == active_biz.id,
        Expense.expense_date >= start_utc,
        Expense.expense_date <= end_utc
    ).all()
    total_pengeluaran = sum(e.amount for e in expenses)

    # 3. Laba Bersih
    laba_bersih = total_pemasukan - total_pengeluaran

    # 4. Top Products (Limit 5)
    top_products = db.session.query(
        SaleDetail.product_id,
        func.sum(SaleDetail.quantity).label('qty'),
        func.sum(SaleDetail.subtotal).label('subtotal')
    ).join(Sale, Sale.id == SaleDetail.sale_id).filter(
        Sale.business_id == active_biz.id,
        Sale.transaction_date >= start_utc,
        Sale.transaction_date <= end_utc
    ).group_by(SaleDetail.product_id).order_by(db.text('qty DESC')).limit(5).all()

    from app.models.product import Product
    top_products_list = []
    for pid, qty, subtotal in top_products:
        prod = Product.query.get(pid)
        if prod:
            top_products_list.append({
                'name': prod.name,
                'qty': qty,
                'subtotal': subtotal
            })

    # 5. Chart Data
    chart_pemasukan = {}
    chart_pengeluaran = {}
    
    # helper for bucketing
    def _add_to_dict(d, dt, val, grouping):
        if grouping == 'hour':
            lbl = f"{dt.hour:02d}.00"
        elif grouping == 'day_name': # minggu_ini
            days = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
            lbl = days[dt.weekday()]
        elif grouping == 'date_only': # bulan_ini
            lbl = str(dt.day)
        elif grouping == 'month_name': # tahun_ini
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des']
            lbl = months[dt.month - 1]
        elif grouping == 'custom_day':
            lbl = dt.strftime('%d %b %Y')
        else: # custom_month
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des']
            lbl = f"{months[dt.month - 1]} {dt.year}"
        d[lbl] = d.get(lbl, 0) + float(val)

    # Determine grouping
    if periode == 'hari_ini':
        grouping = 'hour'
        labels = [f"{i:02d}.00" for i in range(24)]
    elif periode == 'minggu_ini':
        grouping = 'day_name'
        labels = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
    elif periode == 'bulan_ini':
        grouping = 'date_only'
        last_day = calendar.monthrange(start_wib.year, start_wib.month)[1]
        labels = [str(i) for i in range(1, last_day + 1)]
    elif periode == 'tahun_ini':
        grouping = 'month_name'
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des']
    else: # custom
        days_diff = (end_wib - start_wib).days
        if days_diff <= 1:
            grouping = 'hour'
            labels = [f"{i:02d}.00" for i in range(24)]
        elif days_diff <= 62:
            grouping = 'custom_day'
            labels = []
            curr = start_wib
            while curr <= end_wib:
                labels.append(curr.strftime('%d %b %Y'))
                curr += timedelta(days=1)
        else:
            grouping = 'custom_month'
            labels = []
            curr = start_wib.replace(day=1)
            months_indo = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des']
            while curr <= end_wib:
                labels.append(f"{months_indo[curr.month - 1]} {curr.year}")
                # add 1 month
                nxt_month = curr.month % 12 + 1
                nxt_year = curr.year + (curr.month // 12)
                curr = curr.replace(year=nxt_year, month=nxt_month, day=1)
            
    for s in sales:
        dt_wib = from_utc_naive(s.transaction_date)
        _add_to_dict(chart_pemasukan, dt_wib, s.total, grouping)
        
    for e in expenses:
        dt_wib = from_utc_naive(e.expense_date)
        _add_to_dict(chart_pengeluaran, dt_wib, e.amount, grouping)

    data_pemasukan = []
    data_laba_bersih = []
    
    for lbl in labels:
        p = chart_pemasukan.get(lbl, 0)
        e = chart_pengeluaran.get(lbl, 0)
        data_pemasukan.append(p)
        data_laba_bersih.append(p - e)

    return {
        'total_pemasukan': total_pemasukan,
        'total_pengeluaran': total_pengeluaran,
        'laba_bersih': laba_bersih,
        'top_products': top_products_list,
        'chart_labels': labels,
        'chart_pemasukan': data_pemasukan,
        'chart_laba_bersih': data_laba_bersih,
        'sales': sales,
        'expenses': expenses
    }

@laporan_bp.route('/', methods=['GET'])
@login_required
def index():
    active_biz, err = _check_owner_and_active_biz()
    if err: return err

    periode = request.args.get('periode', 'bulan_ini')
    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')

    start_wib, end_wib, periode = get_date_range(periode, start_str, end_str)
    
    data = get_report_data(active_biz, start_wib, end_wib, periode)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Remove full objects before returning JSON
        data.pop('sales', None)
        data.pop('expenses', None)
        return jsonify({
            'status': 'success',
            'periode': periode,
            'start_date': start_wib.strftime('%Y-%m-%d'),
            'end_date': end_wib.strftime('%Y-%m-%d'),
            'data': data
        })

    return render_template(
        'laporan/index.html',
        active_business=active_biz,
        periode=periode,
        start_date=start_wib.strftime('%Y-%m-%d'),
        end_date=end_wib.strftime('%Y-%m-%d'),
        data=data
    )

@laporan_bp.route('/export/pdf', methods=['GET'])
@login_required
def export_pdf():
    active_biz, err = _check_owner_and_active_biz()
    if err: return err

    periode = request.args.get('periode', 'bulan_ini')
    start_wib, end_wib, _ = get_date_range(periode, request.args.get('start_date'), request.args.get('end_date'))
    data = get_report_data(active_biz, start_wib, end_wib, periode)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER)
    
    elements.append(Paragraph(f"Laporan Keuangan - {active_biz.business_name}", title_style))
    elements.append(Paragraph(f"Periode: {start_wib.strftime('%d %b %Y')} - {end_wib.strftime('%d %b %Y')}", styles['Normal']))
    elements.append(Spacer(1, 20))

    # Ringkasan
    summary_data = [
        ['Total Pemasukan', f"Rp {int(data['total_pemasukan']):,}".replace(',', '.')],
        ['Total Pengeluaran', f"Rp {int(data['total_pengeluaran']):,}".replace(',', '.')],
        ['Laba Bersih', f"Rp {int(data['laba_bersih']):,}".replace(',', '.')],
    ]
    t = Table(summary_data, colWidths=[200, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    elements.append(t)
    
    # Top Products
    if data['top_products']:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("5 Produk Terlaris", styles['Heading3']))
        prod_data = [['Nama Produk', 'Terjual', 'Total Penjualan']]
        for p in data['top_products']:
            prod_data.append([p['name'], str(p['qty']), f"Rp {int(p['subtotal']):,}".replace(',', '.')])
        
        pt = Table(prod_data, colWidths=[250, 80, 150])
        pt.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('PADDING', (0,0), (-1,-1), 6)
        ]))
        elements.append(pt)

    doc.build(elements)
    buffer.seek(0)
    
    filename = f"Laporan_{start_wib.strftime('%Y%m%d')}_{end_wib.strftime('%Y%m%d')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

@laporan_bp.route('/export/excel', methods=['GET'])
@login_required
def export_excel():
    active_biz, err = _check_owner_and_active_biz()
    if err: return err

    periode = request.args.get('periode', 'bulan_ini')
    start_wib, end_wib, _ = get_date_range(periode, request.args.get('start_date'), request.args.get('end_date'))
    data = get_report_data(active_biz, start_wib, end_wib, periode)

    wb = openpyxl.Workbook()
    
    # Sheet 1: Ringkasan
    ws_sum = wb.active
    ws_sum.title = "Ringkasan"
    ws_sum.append(["Laporan Keuangan", active_biz.business_name])
    ws_sum.append(["Periode", f"{start_wib.strftime('%d %b %Y')} - {end_wib.strftime('%d %b %Y')}"])
    ws_sum.append([])
    ws_sum.append(["Keterangan", "Total (Rp)"])
    ws_sum.append(["Total Pemasukan", float(data['total_pemasukan'])])
    ws_sum.append(["Total Pengeluaran", float(data['total_pengeluaran'])])
    ws_sum.append(["Laba Bersih", float(data['laba_bersih'])])

    # Sheet 2: Produk Terlaris
    ws_prod = wb.create_sheet("Produk Terlaris")
    ws_prod.append(["Nama Produk", "Terjual", "Total Penjualan (Rp)"])
    for p in data['top_products']:
        ws_prod.append([p['name'], p['qty'], float(p['subtotal'])])

    # Sheet 3: Riwayat Pemasukan
    ws_in = wb.create_sheet("Riwayat Pemasukan")
    ws_in.append(["No Invoice", "Tanggal", "Metode Pembayaran", "Total (Rp)"])
    for s in data['sales']:
        dt = from_utc_naive(s.transaction_date).strftime('%Y-%m-%d %H:%M')
        ws_in.append([s.invoice_number, dt, s.payment_method, float(s.total)])

    # Sheet 4: Riwayat Pengeluaran
    ws_ex = wb.create_sheet("Riwayat Pengeluaran")
    ws_ex.append(["Keperluan", "Kategori", "Tanggal", "Total (Rp)"])
    for e in data['expenses']:
        dt = from_utc_naive(e.expense_date).strftime('%Y-%m-%d %H:%M')
        cat = e.category_name or (e.expense_category.name if e.expense_category else "-")
        ws_ex.append([e.description, cat, dt, float(e.amount)])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"Laporan_{start_wib.strftime('%Y%m%d')}_{end_wib.strftime('%Y%m%d')}.xlsx"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
