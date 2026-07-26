from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.utils import get_active_business

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
@login_required
def index():
    """
    Beranda main route for authenticated users.
    Uses active business stored in session for UMKM owners.
    """
    active_biz = get_active_business()
    return render_template('dashboard/index.html', user=current_user, active_business=active_biz)
