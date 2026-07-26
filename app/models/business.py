from app.extensions import db
from app.models.base import BaseModel


class Business(BaseModel):
    """
    Business model representing MSME / UMKM profile.
    """
    __tablename__ = 'businesses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )
    business_name = db.Column(db.String(100), nullable=False)
    owner_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)

    # Relationships
    user = db.relationship('User', back_populates='business')
    categories = db.relationship(
        'Category',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    products = db.relationship(
        'Product',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    expense_categories = db.relationship(
        'ExpenseCategory',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    expenses = db.relationship(
        'Expense',
        back_populates='business',
        cascade='all, delete-orphan'
    )
    sales = db.relationship(
        'Sale',
        back_populates='business',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Business {self.business_name}>'
