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
    category_name = db.Column(db.String(100), nullable=True)
    expense_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    description = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Numeric(12, 2), nullable=True, default=1.00)
    unit = db.Column(db.String(50), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    notes = db.Column(db.Text, nullable=True)

    # Relationships
    business = db.relationship('Business', back_populates='expenses')
    expense_category = db.relationship('ExpenseCategory', back_populates='expenses')

    @property
    def purpose(self):
        return self.description

    @purpose.setter
    def purpose(self, val):
        self.description = val
        
    @property
    def category(self):
        return self.category_name
        
    @category.setter
    def category(self, val):
        self.category_name = val

    @property
    def total_amount(self):
        return self.amount

    @total_amount.setter
    def total_amount(self, val):
        self.amount = val
        
    @property
    def total_expense(self):
        return self.amount
        
    @total_expense.setter
    def total_expense(self, val):
        self.amount = val

    def __repr__(self):
        return f'<Expense {self.description} - {self.amount}>'
