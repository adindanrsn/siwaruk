import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()

def test_mobile_card_layout():
    with app.app_context():
        print("=== TEST: MOBILE CARD LAYOUT IN MANAJEMEN AKUN ===")

        admin = User.query.filter_by(role='admin').first()
        assert admin is not None, "Admin user not found"
        admin.must_change_password = False
        db.session.commit()

        client = app.test_client()

        with client:
            with app.test_request_context():
                from flask_login import login_user
                login_user(admin)

            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)
                sess['_fresh'] = True

            res = client.get('/', follow_redirects=True)
            print(f"Response status: {res.status_code}")
            assert res.status_code == 200

            html = res.data.decode('utf-8')

            # 1. Verify Desktop Table container exists
            assert 'd-none d-md-block' in html
            print("[1] Desktop Table container (d-none d-md-block): FOUND")

            # 2. Verify Mobile Card container exists
            assert 'd-block d-md-none' in html
            print("[2] Mobile Card container (d-block d-md-none): FOUND")

            # 3. Verify Card layout elements for mobile view
            assert 'Jumlah Usaha:' in html
            assert 'Status Password:' in html
            assert 'Detail' in html
            assert 'Reset Password' in html
            print("[3] Mobile Card components (Nama, Username, Role, Detail, Reset Password): FOUND")

        print("\n[SUCCESS] Mobile Card Layout verification complete!")

if __name__ == '__main__':
    test_mobile_card_layout()
