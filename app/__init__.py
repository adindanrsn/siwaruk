from flask import Flask, redirect, url_for, request, flash
from flask_login import current_user

from config import Config
from app.extensions import db, login_manager, migrate
from app.utils import get_whatsapp_link


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    # Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Flask-Login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login terlebih dahulu untuk mengakses halaman ini.'
    login_manager.login_message_category = 'warning'

    from app import models
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.utils import get_whatsapp_link, get_active_business

    # Context Processors
    @app.context_processor
    def inject_global_vars():
        active_biz = get_active_business()
        user_bizs = current_user.businesses.all() if current_user.is_authenticated and current_user.role == 'owner' else []
        return {
            'wa_register_link': get_whatsapp_link('register'),
            'wa_forgot_password_link': get_whatsapp_link('forgot_password'),
            'active_business': active_biz,
            'user_businesses': user_bizs,
        }

    # Before Request Guard: Enforce password change if must_change_password is True
    @app.before_request
    def force_password_change_guard():
        if current_user.is_authenticated and getattr(current_user, 'must_change_password', False):
            allowed_endpoints = ['auth.profil', 'auth.change_password', 'auth.logout', 'static']
            if request.endpoint and request.endpoint not in allowed_endpoints:
                flash('Anda harus mengganti password terlebih dahulu sebelum dapat mengakses halaman lain.', 'warning')
                return redirect(url_for('auth.profil'))

    # Register Blueprints
    from app.routes import auth_bp, dashboard_bp, admin_bp, usaha_bp, produk_bp, transaksi_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(usaha_bp)
    app.register_blueprint(produk_bp)
    app.register_blueprint(transaksi_bp)

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            if current_user.must_change_password:
                return redirect(url_for("auth.profil"))
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    return app