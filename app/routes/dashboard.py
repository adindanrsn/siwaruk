from flask import Blueprint, render_template, session, request
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime, timezone

from app.extensions import db
from app.utils import get_active_business
from app.models.user import User
from app.models.business import Business, BIDANG_USAHA_CHOICES
from app.models.sales_transaction import SalesTransaction
from app.models.expense_transaction import ExpenseTransaction

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    """
    Beranda main route for authenticated users.
    Admin gets BUMDes monitoring dashboard.
    Owner gets their own business dashboard.
    """
    if current_user.role == 'admin':
        # ── Basic counts ────────────────────────────────────────────
        total_owners = User.query.filter_by(role='owner').count()
        total_businesses = Business.query.count()

        # ── Session-based one-time modal data ───────────────────────
        new_account = session.pop('new_account_created', None)
        reset_info = session.pop('reset_password_success', None)

        # ── Aggregate financials across all businesses ───────────────
        total_omzet = db.session.query(
            func.coalesce(func.sum(SalesTransaction.total_amount), 0)
        ).scalar()

        total_expense_all = db.session.query(
            func.coalesce(func.sum(ExpenseTransaction.total_amount), 0)
        ).scalar()

        total_laba_bersih = float(total_omzet) - float(total_expense_all)

        # ── Top 5 UMKM by total income ───────────────────────────────
        top_umkm_rows = (
            db.session.query(
                Business.id,
                Business.business_name,
                Business.owner_name,
                func.coalesce(func.sum(SalesTransaction.total_amount), 0).label('total_income'),
            )
            .outerjoin(SalesTransaction, SalesTransaction.business_id == Business.id)
            .group_by(Business.id, Business.business_name, Business.owner_name)
            .order_by(func.coalesce(func.sum(SalesTransaction.total_amount), 0).desc())
            .limit(5)
            .all()
        )

        # ── Bidang usaha distribution ────────────────────────────────
        bidang_rows = (
            db.session.query(
                Business.bidang_usaha,
                func.count(Business.id).label('count')
            )
            .group_by(Business.bidang_usaha)
            .all()
        )
        # Build ordered dict following BIDANG_USAHA_CHOICES order
        bidang_data = {choice: 0 for choice in BIDANG_USAHA_CHOICES}
        for row in bidang_rows:
            key = row.bidang_usaha if row.bidang_usaha in bidang_data else 'Lain-lain'
            bidang_data[key] += row.count

        # ── New businesses this month ────────────────────────────────
        now = datetime.now(timezone.utc)
        new_businesses_month = Business.query.filter(
            func.extract('year',  Business.created_at) == now.year,
            func.extract('month', Business.created_at) == now.month,
        ).count()

        # ── Users query with filtering, sorting, and pagination ────────
        search = request.args.get('search', '').strip()
        role_filter = request.args.get('role', 'Semua')
        status_filter = request.args.get('status', 'Semua')
        sort_by = request.args.get('sort', 'Terbaru')
        page = request.args.get('page', 1, type=int)

        query = User.query

        if search:
            search_term = f"%{search}%"
            
            # Smart phone number search matching
            import re
            from app.utils import normalize_whatsapp_number
            
            cleaned_search = re.sub(r'[^\d+]', '', search)
            if cleaned_search:
                normalized_phone = normalize_whatsapp_number(search)
                phone_query = db.or_(
                    User.phone.ilike(search_term),
                    User.phone.ilike(f"%{normalized_phone}%"),
                    User.phone.ilike(f"%{cleaned_search}%")
                )
            else:
                phone_query = User.phone.ilike(search_term)

            query = query.filter(
                db.or_(
                    User.full_name.ilike(search_term),
                    User.username.ilike(search_term),
                    phone_query
                )
            )

        if role_filter == 'Admin':
            query = query.filter(User.role == 'admin')
        elif role_filter == 'Pemilik Usaha':
            query = query.filter(User.role == 'owner')

        if status_filter == 'Aktif':
            query = query.filter(User.must_change_password == False)
        elif status_filter == 'Wajib Ganti Password':
            query = query.filter(User.must_change_password == True)

        if sort_by == 'Nama A-Z':
            query = query.order_by(User.full_name.asc())
        elif sort_by == 'Nama Z-A':
            query = query.order_by(User.full_name.desc())
        elif sort_by == 'Jumlah Usaha Terbanyak':
            biz_count_subq = db.session.query(
                Business.owner_id, func.count(Business.id).label('biz_count')
            ).group_by(Business.owner_id).subquery()
            
            query = query.outerjoin(biz_count_subq, User.id == biz_count_subq.c.owner_id)\
                         .order_by(func.coalesce(biz_count_subq.c.biz_count, 0).desc(), User.created_at.desc())
        else: # 'Terbaru'
            query = query.order_by(User.created_at.desc())

        users_pagination = query.paginate(page=page, per_page=10, error_out=False)

        return render_template(
            'dashboard/index.html',
            user=current_user,
            total_owners=total_owners,
            total_businesses=total_businesses,
            total_omzet=total_omzet,
            total_laba_bersih=total_laba_bersih,
            top_umkm=top_umkm_rows,
            bidang_data=bidang_data,
            new_businesses_month=new_businesses_month,
            users=users_pagination,
            search=search,
            role_filter=role_filter,
            status_filter=status_filter,
            sort_by=sort_by,
            new_account=new_account,
            reset_info=reset_info,
        )
    else:
        # ── Owner dashboard: real financial summary (same logic as laporan) ──
        from app.models.sale import Sale
        from app.models.expense import Expense
        from zoneinfo import ZoneInfo
        from datetime import timedelta, timezone as _tz
        import calendar

        _WIB = ZoneInfo('Asia/Jakarta')
        now_wib = datetime.now(_WIB)

        # Build periode options
        start_hari   = now_wib.replace(hour=0,  minute=0,  second=0,  microsecond=0)
        end_hari     = now_wib.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_minggu = (now_wib - timedelta(days=now_wib.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_minggu   = (start_minggu + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=999999)
        start_bulan  = now_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day     = calendar.monthrange(now_wib.year, now_wib.month)[1]
        end_bulan    = now_wib.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

        periodes = {
            'hari_ini':   ('Hari Ini',   start_hari,   end_hari),
            'minggu_ini': ('Minggu Ini', start_minggu, end_minggu),
            'bulan_ini':  ('Bulan Ini',  start_bulan,  end_bulan),
        }

        selected_periode = request.args.get('periode', 'bulan_ini')
        if selected_periode not in periodes:
            selected_periode = 'bulan_ini'

        periode_label, start_wib, end_wib = periodes[selected_periode]

        # Convert to UTC naive — identical to laporan.py's to_utc_naive()
        start_utc = start_wib.astimezone(_tz.utc).replace(tzinfo=None)
        end_utc   = end_wib.astimezone(_tz.utc).replace(tzinfo=None)

        active_biz = get_active_business()
        summary = {'pemasukan': 0.0, 'pengeluaran': 0.0, 'laba_bersih': 0.0}
        recent_sales = []

        if active_biz:
            sales = Sale.query.filter(
                Sale.business_id == active_biz.id,
                Sale.transaction_date >= start_utc,
                Sale.transaction_date <= end_utc,
            ).order_by(Sale.transaction_date.desc()).all()

            expenses = Expense.query.filter(
                Expense.business_id == active_biz.id,
                Expense.expense_date >= start_utc,
                Expense.expense_date <= end_utc,
            ).all()

            total_pemasukan   = sum(float(s.total) for s in sales)
            total_pengeluaran = sum(float(e.amount) for e in expenses)
            summary = {
                'pemasukan':   total_pemasukan,
                'pengeluaran': total_pengeluaran,
                'laba_bersih': total_pemasukan - total_pengeluaran,
            }
            recent_sales = sales[:3]

        user_businesses = current_user.businesses.all()

        return render_template(
            'dashboard/index.html',
            user=current_user,
            active_business=active_biz,
            user_businesses=user_businesses,
            summary=summary,
            recent_sales=recent_sales,
            periodes=periodes,
            selected_periode=selected_periode,
            periode_label=periode_label,
        )
