from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.admin import admin_bp
from app.routes.usaha import usaha_bp
from app.routes.produk import produk_bp
from app.routes.transaksi import transaksi_bp
from app.routes.laporan import laporan_bp

__all__ = ['auth_bp', 'dashboard_bp', 'admin_bp', 'usaha_bp', 'produk_bp', 'transaksi_bp', 'laporan_bp']
