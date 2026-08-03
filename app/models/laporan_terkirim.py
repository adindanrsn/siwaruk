from datetime import datetime
from app.extensions import db


class LaporanTerkirim(db.Model):
    """
    Menyimpan riwayat laporan keuangan yang dikirimkan
    oleh pemilik usaha kepada admin melalui fitur 'Kirim ke Admin'.
    """
    __tablename__ = 'laporan_terkirim'

    id = db.Column(db.Integer, primary_key=True)

    # Relasi ke usaha
    business_id = db.Column(
        db.Integer,
        db.ForeignKey('businesses.id', ondelete='CASCADE'),
        nullable=False
    )

    # Pengirim (user / pemilik usaha)
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )

    # Informasi periode laporan
    periode = db.Column(db.String(32), nullable=False)          # 'bulan_ini', 'custom', dst.
    periode_label = db.Column(db.String(128), nullable=False)   # "Juni 2026", "1–30 Jun 2026", dst.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # Metadata pengiriman
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Lokasi file PDF yang disimpan (path relatif dari INSTANCE_PATH/laporan_terkirim/)
    file_path = db.Column(db.String(512), nullable=True)

    # Status tinjauan admin
    STATUS_BELUM = 'Belum Ditinjau'
    STATUS_DITINJAU = 'Sedang Ditinjau'
    STATUS_SELESAI = 'Selesai Ditinjau'

    status = db.Column(db.String(64), nullable=False, default='Belum Ditinjau')

    # Catatan admin (opsional, bisa digunakan nanti)
    catatan_admin = db.Column(db.Text, nullable=True)

    # Relationships
    business = db.relationship('Business', backref=db.backref('laporan_terkirim', lazy='dynamic'))
    sender = db.relationship('User', backref=db.backref('laporan_terkirim', lazy='dynamic'))

    def __repr__(self):
        return f'<LaporanTerkirim id={self.id} biz={self.business_id} status={self.status}>'
