from app.extensions import db
from app.models.base import BaseModel


class ExpenseCategory(BaseModel):
    """
    ExpenseCategory model for categorizing business operational expenses.
    """
    __tablename__ = 'expense_categories'

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(
        db.Integer,
        db.ForeignKey('businesses.id', ondelete='CASCADE'),
        nullable=False
    )
    name = db.Column(db.String(100), nullable=False)

    # Relationships
    business = db.relationship('Business', back_populates='expense_categories')
    expenses = db.relationship(
        'Expense',
        back_populates='expense_category',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<ExpenseCategory {self.name}>'
