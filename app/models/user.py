from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.base import BaseModel


class User(UserMixin, BaseModel):
    """
    User model representing system accounts (admin or owner).
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='owner')  # admin or owner
    must_change_password = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    phone = db.Column(db.String(20), nullable=True)

    # Relationships
    # One Owner can have many Businesses (one-to-many)
    businesses = db.relationship(
        'Business',
        back_populates='owner',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    @property
    def role_label(self):
        """
        Human-readable role label for UI display.
        """
        if self.role == 'admin':
            return 'Admin'
        return 'Pemilik Usaha'

    # Password Hashing Methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

