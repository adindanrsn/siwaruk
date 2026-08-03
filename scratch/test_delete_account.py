import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.business import Business
from app.models.category import Category
from app.models.product import Product
from app.models.expense import Expense
from app.models.sale import Sale
from app.models.laporan_terkirim import LaporanTerkirim

app = create_app()

def test_delete_account_flow():
    with app.app_context():
        print("=== TEST: DELETE ACCOUNT FLOW (OWNER) ===")

        # 1. Create a test owner user
        username = "test_owner_del"
        # Cleanup if left from previous run
        existing = User.query.filter_by(username=username).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        test_user = User(
            username=username,
            full_name="Pemilik Test Hapus",
            role="owner",
            must_change_password=False
        )
        test_user.set_password("Password123")
        db.session.add(test_user)
        db.session.commit()

        # 2. Create related entities
        biz = Business(
            owner_id=test_user.id,
            business_name="Warung Hapus Test",
            owner_name="Pemilik Test Hapus",
            bidang_usaha="Kuliner"
        )
        db.session.add(biz)
        db.session.commit()

        cat = Category(business_id=biz.id, name="Makanan Test")
        db.session.add(cat)
        db.session.commit()

        prod = Product(business_id=biz.id, category_id=cat.id, name="Nasi Test", price=10000, stock=50)
        db.session.add(prod)
        db.session.commit()

        exp = Expense(business_id=biz.id, description="Beli Beras Test", amount=50000)
        db.session.add(exp)
        db.session.commit()

        lap = LaporanTerkirim(
            business_id=biz.id,
            sender_id=test_user.id,
            periode="bulan_ini",
            periode_label="Agustus 2026",
            start_date="2026-08-01",
            end_date="2026-08-31",
            status="Belum Ditinjau"
        )
        db.session.add(lap)
        db.session.commit()

        print(f"Created Test User ID: {test_user.id}")
        print(f"Created Business ID: {biz.id}")
        print(f"Created Category ID: {cat.id}")
        print(f"Created Product ID: {prod.id}")
        print(f"Created Expense ID: {exp.id}")
        print(f"Created LaporanTerkirim ID: {lap.id}")

        # 3. Simulate POST /profil with action=delete_account
        client = app.test_client()
        with client:
            with app.test_request_context():
                from flask_login import login_user
                login_user(test_user)

            with client.session_transaction() as sess:
                sess['_user_id'] = str(test_user.id)
                sess['_fresh'] = True

            res = client.post('/auth/profil', data={
                'action': 'delete_account'
            }, follow_redirects=True)

            print(f"\nResponse Code: {res.status_code}")
            assert res.status_code == 200
            assert b'Login' in res.data or b'Masuk' in res.data

        # 4. Verify no orphan data remains
        user_db = db.session.get(User, test_user.id)
        biz_db = db.session.get(Business, biz.id)
        cat_db = db.session.get(Category, cat.id)
        prod_db = db.session.get(Product, prod.id)
        exp_db = db.session.get(Expense, exp.id)
        lap_db = db.session.get(LaporanTerkirim, lap.id)

        assert user_db is None, "User was not deleted!"
        assert biz_db is None, "Business was not deleted!"
        assert cat_db is None, "Category was not deleted!"
        assert prod_db is None, "Product was not deleted!"
        assert exp_db is None, "Expense was not deleted!"
        assert lap_db is None, "LaporanTerkirim was not deleted!"

        print("\n[SUCCESS] VERIFICATION SUCCESSFUL:")
        print("- User deleted: YES")
        print("- Business deleted: YES")
        print("- Categories, Products, Expenses, Reports deleted: YES")
        print("- Zero orphan data left in DB: YES")

if __name__ == '__main__':
    test_delete_account_flow()
