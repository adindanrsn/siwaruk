from flask import Flask

from config import Config
from app.extensions import db, login_manager, migrate

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    @app.route("/")
    def home():
        return "<h1>Hello, UMKM!</h1>"

    return app