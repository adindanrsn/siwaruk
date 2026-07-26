from datetime import datetime
from app.extensions import db
from app.models.base import BaseModel


class Expense(BaseModel):
    """
    Expense model for recording business expenditures.
    """
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(
        db.Integer,
        db.ForeignKey('businesses.id', ondelete='CASCADE'),
        nullable=False
    )
    expense_category_id = db.Column(
        db.Integer,
        db.ForeignKey('expense_categories.id', ondelete='SET NULL'),
        nullable=True
    )
    expense_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    business = db.relationship('Business', back_populates='expenses')
    expense_category = db.relationship('ExpenseCategory', back_populates='expenses')

    def __repr__(self):
        return f'<Expense {self.description} - {self.amount}>'
