from flask_login import UserMixin
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

    # Relationships
    # One User owns one Business
    business = db.relationship(
        'Business',
        back_populates='user',
        uselist=False,
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<User {self.username}>'
