from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime



db = SQLAlchemy()

# Enstitü ve anabilim dalları
class Enstitu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    anabilim_dallari = db.relationship('AnabilimDali', backref='enstitu', lazy=True)

class AnabilimDali(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    enstitu_id = db.Column(db.Integer, db.ForeignKey('enstitu.id'), nullable=False)

class EgitimTipi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)

# Ders
class Ders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    kredi = db.Column(db.Integer)
    anabilim_dali_id = db.Column(db.Integer, db.ForeignKey('anabilim_dali.id'), nullable=False)

# Öğrenci
class Ogrenci(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    ogrenci_no = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    telefon = db.Column(db.String(20))
    egitim_tipi_id = db.Column(db.Integer, db.ForeignKey('egitim_tipi.id'))
    anabilim_dali_id = db.Column(db.Integer, db.ForeignKey('anabilim_dali.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# Öğretim Üyesi
class OgretimUyesi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    unvan = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)

# Öğrenci - Ders ilişkisi (Many-to-Many)
ogrenci_ders = db.Table('ogrenci_ders',
    db.Column('ogrenci_id', db.Integer, db.ForeignKey('ogrenci.id'), primary_key=True),
    db.Column('ders_id', db.Integer, db.ForeignKey('ders.id'), primary_key=True)
)

# Öğretim Üyesi - Ders ilişkisi
ogretim_uyesi_ders = db.Table('ogretim_uyesi_ders',
    db.Column('ogretim_uyesi_id', db.Integer, db.ForeignKey('ogretim_uyesi.id'), primary_key=True),
    db.Column('ders_id', db.Integer, db.ForeignKey('ders.id'), primary_key=True)
)

# Kullanıcılar
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), nullable=False)  # 'ogrenci' veya 'ogretim_uyesi'
    
    

# Notlar
class Not(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenci.id'))
    ders_id = db.Column(db.Integer, db.ForeignKey('ders.id'))
    vize = db.Column(db.Float)
    final = db.Column(db.Float)

    @property
    def ortalama(self):
        return round((self.vize * 0.4 + self.final * 0.6), 2)

    @property
    def harf_notu(self):
        from models import NotAralik  # İçeriden çağırmak recursive import'ı engeller
        ort = self.ortalama
        aralik = NotAralik.query.filter(NotAralik.min <= ort, NotAralik.max >= ort).first()
        return aralik.harf if aralik else "?"

    @property
    def durum(self):
        from models import NotAralik
        ort = self.ortalama
        aralik = NotAralik.query.filter(NotAralik.min <= ort, NotAralik.max >= ort).first()
        return aralik.durum if aralik else "?"

class DersProgrami(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenci.id'), nullable=False)
    ders_id = db.Column(db.Integer, db.ForeignKey('ders.id'), nullable=False)
    gun = db.Column(db.String(20), nullable=False)         # Örn: Pazartesi
    saat = db.Column(db.String(10), nullable=False)        # Örn: 09:00
    sinif = db.Column(db.String(10), nullable=True)        # Örn: A101

    ogrenci = db.relationship('Ogrenci', backref='programlar')
    ders = db.relationship('Ders', backref='programlar')
class Duyuru(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # öğretim üyesi
class Mesaj(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gonderen_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    alici_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    baslik = db.Column(db.String(100))
    icerik = db.Column(db.Text, nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)

    gonderen = db.relationship('User', foreign_keys=[gonderen_id], backref='gonderilen_mesajlar')
    alici = db.relationship('User', foreign_keys=[alici_id], backref='alinan_mesajlar')
class NotAralik(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    min_puan = db.Column(db.Float, nullable=False)
    max_puan = db.Column(db.Float, nullable=False)
    harf = db.Column(db.String(10), nullable=False)
    durum = db.Column(db.String(20), nullable=False)  # Geçti, Kaldı, Şartlı Geçti gibi
    sartli_gecme = db.Column(db.Boolean, default=False)  # <-- BU SATIRI EKLE
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin





   


        



        
