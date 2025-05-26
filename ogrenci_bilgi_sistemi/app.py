from flask import Flask, render_template, request, redirect, flash, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from models import db, User, Ogrenci, Ders, Not, ogrenci_ders, DersProgrami, Duyuru, Mesaj, NotAralik
from datetime import datetime, date
import random, io, pandas as pd

pdfmetrics.registerFont(TTFont('DejaVu', 'static/fonts/DejaVuSans.ttf'))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///veritabani.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)





# Mail ayarları
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'oguzhanuluugur1905@gmail.com'  # değiştir
app.config['MAIL_PASSWORD'] = 'tkjn lclo grbv rcbw'      # değiştir
app.config['MAIL_DEFAULT_SENDER'] = 'oguzhanuluugur1905@gmail.com'  # değiştir

mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        rol = request.form.get('rol')
        user = User.query.filter_by(email=email, rol=rol).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Giriş başarılı!", "success")

            # 🔴 admin, öğretim üyesi, öğrenci kontrolü
            if user.rol == 'admin':
                return redirect(url_for('admin_panel'))  # admin paneline yönlendirme
            elif user.rol == 'ogretim_uyesi':
                return redirect(url_for('dashboard_ogretim'))
            else:
                return redirect(url_for('dashboard_ogrenci'))
        else:
            flash("Bilgiler hatalı!", "danger")
    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        rol = request.form.get('rol')

        if User.query.filter_by(email=email).first():
            flash("Bu e-posta zaten kayıtlı.", "danger")
        else:
            hashed_pw = generate_password_hash(password)
            user = User(name=name, email=email, password=hashed_pw, rol=rol)
            db.session.add(user)
            db.session.commit()

            if rol == 'ogrenci':
                yeni_ogr = Ogrenci(
                    ad=name,
                    ogrenci_no=email.split("@")[0],
                    email=email,
                    telefon="",
                    user_id=user.id
                )
                db.session.add(yeni_ogr)
                db.session.commit()

            flash("Kayıt başarılı!", "success")
            return redirect(url_for('login'))

    return render_template('auth/register.html')


@app.route('/dashboard/ogretim')
@login_required
def dashboard_ogretim():
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))
    return render_template('dashboard/dashboard_ogretim.html')




@app.route('/ogrenci-ekle', methods=['GET', 'POST'])
@login_required
def ogrenci_ekle():
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        if Ogrenci.query.filter_by(email=email).first():
            flash("Bu e-posta ile kayıtlı bir öğrenci zaten var.", "danger")
            return redirect(url_for('ogrenci_ekle'))

        ogr = Ogrenci(
            ad=request.form.get('ad'),
            ogrenci_no=request.form.get('ogrenci_no'),
            email=email,
            telefon=request.form.get('telefon')
        )
        db.session.add(ogr)
        db.session.commit()
        flash("Öğrenci başarıyla eklendi!", "success")
        return redirect(url_for('ogrenci_listesi'))

    return render_template('ogrenci/ekle.html')


@app.route('/ogrenci-listesi')
@login_required
def ogrenci_listesi():
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))
    ogrenciler = Ogrenci.query.all()
    return render_template('ogrenci/liste.html', ogrenciler=ogrenciler)


@app.route('/ogrenci-debug')
def ogrenci_debug():
    ogrenciler = Ogrenci.query.all()
    return "<br>".join([f"{o.id} - {o.ad} - {o.ogrenci_no} - {o.email}" for o in ogrenciler])


@app.route('/ogrenci-duzenle/<int:id>', methods=['GET', 'POST'])
@login_required
def ogrenci_duzenle(id):
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    ogrenci = Ogrenci.query.get_or_404(id)

    if request.method == 'POST':
        ogrenci.ad = request.form.get('ad')
        ogrenci.ogrenci_no = request.form.get('ogrenci_no')
        ogrenci.email = request.form.get('email')
        ogrenci.telefon = request.form.get('telefon')
        db.session.commit()
        flash("Öğrenci bilgileri güncellendi!", "success")
        return redirect(url_for('ogrenci_listesi'))

    return render_template('ogrenci/duzenle.html', ogrenci=ogrenci)


@app.route('/ogrenci-sil/<int:id>', methods=['GET'])
@login_required
def ogrenci_sil(id):
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    ogrenci = Ogrenci.query.get_or_404(id)
    db.session.delete(ogrenci)
    db.session.commit()
    flash("Öğrenci silindi.", "success")
    return redirect(url_for('ogrenci_listesi'))


@app.route('/ders-ekle', methods=['GET', 'POST'])
@login_required
def ders_ekle():
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))
    if request.method == 'POST':
        ders = Ders(
            ad=request.form.get('ad'),
            kredi=request.form.get('kredi'),
            anabilim_dali_id=request.form.get('anabilim_dali_id')
        )
        db.session.add(ders)
        db.session.commit()
        flash("Ders tanımlandı!", "success")
        return redirect(url_for('dashboard_ogretim'))
    return render_template('ders/ekle.html')


@app.route('/ders-ata', methods=['GET', 'POST'])
@login_required
def ders_ata():
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))
    if request.method == 'POST':
        ogrenci_id = request.form.get('ogrenci_id')
        ders_id = request.form.get('ders_id')
        db.session.execute(ogrenci_ders.insert().values(ogrenci_id=ogrenci_id, ders_id=ders_id))
        db.session.commit()
        flash("Ders atandı!", "success")
        return redirect(url_for('dashboard_ogretim'))
    return render_template('ders/ata.html')

@app.route('/not-gir/<int:ogrenci_id>/<int:ders_id>', methods=['GET', 'POST'])
@login_required
def not_gir(ogrenci_id, ders_id):
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    ders = Ders.query.get_or_404(ders_id)

    mevcut_not = Not.query.filter_by(ogrenci_id=ogrenci_id, ders_id=ders_id).first()

    if request.method == 'POST':
        vize = float(request.form.get('vize'))
        final = float(request.form.get('final'))

        if mevcut_not:
            mevcut_not.vize = vize
            mevcut_not.final = final
            flash("Not güncellendi.", "info")
        else:
            yeni_not = Not(
                ogrenci_id=ogrenci_id,
                ders_id=ders_id,
                vize=vize,
                final=final
            )
            db.session.add(yeni_not)
            flash("Not eklendi.", "success")

        db.session.commit()
        return redirect(url_for('dashboard_ogretim'))

    return render_template('ders/not_gir.html', ogrenci=ogrenci, ders=ders, mevcut_not=mevcut_not)


@app.route('/not-sec', methods=['GET', 'POST'])
@login_required
def not_giris_sec():
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    ogrenciler = Ogrenci.query.all()
    dersler = Ders.query.all()

    if request.method == 'POST':
        ogr_id = request.form.get('ogrenci_id')
        ders_id = request.form.get('ders_id')
        return redirect(url_for('not_gir', ogrenci_id=ogr_id, ders_id=ders_id))

    return render_template('ders/not_sec.html', ogrenciler=ogrenciler, dersler=dersler)
@app.route('/ogrenci-notlarim')
@login_required
def ogrenci_notlarim():
    if current_user.rol != 'ogrenci':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    ogrenci = Ogrenci.query.filter_by(email=current_user.email).first()
    notlar = Not.query.filter_by(ogrenci_id=ogrenci.id).all()
    dersler = {d.id: d.ad for d in Ders.query.all()}

    enriched = []
    for n in notlar:
        sonuc = harf_notu_hesapla(n.ortalama)

        enriched.append({
            "ders_id": n.ders_id,
            "vize": n.vize,
            "final": n.final,
            "ortalama": n.ortalama,
            "harf_notu": sonuc.get("harf", "Belirsiz"),
            "durum": sonuc.get("durum", "Belirsiz")
        })

    return render_template("ogrenci/notlar.html", notlar=enriched, dersler=dersler)




    






@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Çıkış yapıldı!", "info")
    return redirect(url_for('index'))
@app.route('/sifre-sifirla-kod', methods=['GET', 'POST'])
def sifre_sifirla_kod():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Bu e-posta sistemde kayıtlı değil.", "danger")
        else:
            kod = str(random.randint(100000, 999999))
            session['sifre_sifirla_email'] = email
            session['sifre_sifirla_kod'] = kod

            msg = Message("Şifre Sıfırlama Kodunuz", recipients=[email])
            msg.body = f"Merhaba {user.name},\n\nŞifre sıfırlama kodunuz: {kod}\nBu kodu kullanarak şifrenizi güncelleyebilirsiniz."
            mail.send(msg)

            flash("Doğrulama kodu e-posta adresinize gönderildi.", "info")
            return redirect(url_for('sifre_kodu_dogrula'))
    return render_template('auth/sifre_kod_gonder.html')


@app.route('/sifre-kodu-dogrula', methods=['GET', 'POST'])
def sifre_kodu_dogrula():
    if request.method == 'POST':
        kod = request.form.get('kod')
        yeni_sifre = request.form.get('yeni_sifre')

        if kod == session.get('sifre_sifirla_kod'):
            user = User.query.filter_by(email=session.get('sifre_sifirla_email')).first()
            if user:
                user.password = generate_password_hash(yeni_sifre)
                db.session.commit()
                session.pop('sifre_sifirla_kod')
                session.pop('sifre_sifirla_email')
                flash("Şifre başarıyla güncellendi. Giriş yapabilirsiniz.", "success")
                return redirect(url_for('login'))
        else:
            flash("Doğrulama kodu hatalı!", "danger")

    return render_template('auth/sifre_kod_dogrula.html')
@app.route('/sifre-degistir', methods=['GET', 'POST'])
@login_required
def sifre_degistir():
    if request.method == 'POST':
        eski_sifre = request.form.get('eski_sifre')
        yeni_sifre = request.form.get('yeni_sifre')

        if not check_password_hash(current_user.password, eski_sifre):
            flash("Eski şifreniz yanlış!", "danger")
        else:
            current_user.password = generate_password_hash(yeni_sifre)
            db.session.commit()
            flash("Şifreniz başarıyla güncellendi!", "success")
            return redirect(url_for('dashboard_ogretim' if current_user.rol == 'ogretim_uyesi' else 'dashboard_ogrenci'))

    return render_template('auth/sifre_degistir.html')
@app.route('/notlar-pdf/<int:ogrenci_id>')
@login_required
def notlar_pdf(ogrenci_id):
    if current_user.rol != 'ogrenci' or current_user.id != ogrenci_id:
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    notlar = Not.query.filter_by(ogrenci_id=ogrenci_id).all()

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Öğrenci Not Raporu")
    y -= 30
    p.setFont("Helvetica", 11)

    for n in notlar:
        ders = Ders.query.get(n.ders_id)
        sonuc = harf_notu_hesapla(n.ortalama)
        satir = f"{ders.ad}: Vize={n.vize}, Final={n.final}, Ortalama={n.ortalama}, Harf={sonuc['harf']}, Durum={sonuc['durum']}"
        p.drawString(50, y, satir)
        y -= 20

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="notlar.pdf", mimetype='application/pdf')
@app.route('/transkript/<int:ogrenci_id>')
@login_required
def transkript_indir(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    if current_user.rol != 'ogrenci':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    ogrenci = Ogrenci.query.filter_by(email=current_user.email).first()
    notlar = Not.query.filter_by(ogrenci_id=ogrenci.id).all()
    dersler = {d.id: d.ad for d in Ders.query.all()}

    enriched = []
    for n in notlar:
        sonuc = harf_notu_hesapla(n.ortalama)
        enriched.append({
            "ders_id": n.ders_id,
            "vize": n.vize,
            "final": n.final,
            "ortalama": n.ortalama,
            "harf_notu": sonuc["harf"],
        })

    pdf = create_transcript_pdf(enriched, dersler, ogrenci.ad)
    return send_file(pdf, as_attachment=True, download_name="transkript.pdf", mimetype='application/pdf')
def create_transcript_pdf(notlar, dersler, ogrenci_ad):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Başlık
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width / 2, height - 2 * cm, "Gümüşhane Üniversitesi")
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, height - 2.8 * cm, "Transkript Belgesi")
    
    # Öğrenci adı
    p.setFont("Helvetica", 10)
    p.drawString(2 * cm, height - 4 * cm, f"Öğrenci: {ogrenci_ad}")
    y = height - 5 * cm

    # Tablomuz
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2 * cm, y, "Ders")
    p.drawString(7 * cm, y, "Vize")
    p.drawString(9 * cm, y, "Final")
    p.drawString(11 * cm, y, "Ortalama")
    p.drawString(14 * cm, y, "Harf Notu")
    y -= 0.7 * cm

    p.setFont("Helvetica", 10)
    for n in notlar:
        p.drawString(2 * cm, y, dersler.get(n["ders_id"], "Bilinmeyen"))
        p.drawString(7 * cm, y, str(n["vize"]))
        p.drawString(9 * cm, y, str(n["final"]))
        p.drawString(11 * cm, y, str(n["ortalama"]))
        p.drawString(14 * cm, y, str(n["harf_notu"]))
        y -= 0.6 * cm
        if y < 2 * cm:
            p.showPage()
            y = height - 2 * cm

    # Alt bilgi
    p.setFont("Helvetica-Oblique", 8)
    p.drawString(2 * cm, 1.5 * cm, f"Bu belge sistem tarafından {date.today()} tarihinde üretilmiştir.")

    # İmza ve logo (opsiyonel, yollar doğruysa)
    try:
        p.drawImage("static/images/logo.png", 2 * cm, height - 3 * cm, width=2.5 * cm, preserveAspectRatio=True, mask='auto')
        p.drawImage("static/images/imza.png", width - 5 * cm, 1 * cm, width=3 * cm, preserveAspectRatio=True, mask='auto')
    except:
        pass  # Dosya yoksa geç

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

    



@app.route('/notlar-excel/<int:ogrenci_id>')
@login_required
def notlar_excel(ogrenci_id):
    if current_user.rol != 'ogrenci' or current_user.id != ogrenci_id:
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    notlar = Not.query.filter_by(ogrenci_id=ogrenci_id).all()

    veriler = []
    for n in notlar:
        ders = Ders.query.get(n.ders_id)
        sonuc = harf_notu_hesapla(n.ortalama)
        veriler.append({
            "Ders": ders.ad,
            "Vize": n.vize,
            "Final": n.final,
            "Ortalama": n.ortalama,
            "Durum": sonuc["durum"],
            "Harf Notu": sonuc["harf"]
        })

    df = pd.DataFrame(veriler)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Notlar')

    output.seek(0)
    return send_file(output, as_attachment=True, download_name="notlar.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')



@app.route('/program-ekle', methods=['GET', 'POST'])
@login_required
def program_ekle():
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    dersler = Ders.query.all()
    ogrenciler = Ogrenci.query.all()

    if request.method == 'POST':
        ders_id = request.form.get('ders_id')
        ogrenci_id = request.form.get('ogrenci_id')
        gun = request.form.get('gun')
        saat = request.form.get('saat')
        sinif = request.form.get('sinif')

        program = DersProgrami(
            ders_id=ders_id,
            ogrenci_id=ogrenci_id,
            gun=gun,
            saat=saat,
            sinif=sinif
        )
        db.session.add(program)
        db.session.commit()
        flash("Ders programı eklendi!", "success")
        return redirect(url_for('dashboard_ogretim'))

    return render_template("ders/program_ekle.html", dersler=dersler, ogrenciler=ogrenciler)
@app.route('/programim')
@login_required
def programim():
    if current_user.rol != 'ogrenci':
        flash("Bu sayfaya yalnızca öğrenciler erişebilir.", "danger")
        return redirect(url_for('index'))

    ogrenci = Ogrenci.query.filter_by(email=current_user.email).first()
    programlar = DersProgrami.query.filter_by(ogrenci_id=ogrenci.id).all()

    return render_template('ogrenci/program.html', programlar=programlar)


@app.route('/duyuru-ekle', methods=['GET', 'POST'])
@login_required
def duyuru_ekle():
    if current_user.rol != 'ogretim_uyesi':
        flash("Bu sayfaya sadece öğretim üyeleri erişebilir.", "danger")
        return redirect(url_for('index'))
    if request.method == 'POST':
        yeni = Duyuru(
            baslik=request.form.get('baslik'),
            icerik=request.form.get('icerik'),
            olusturan_id=current_user.id
        )
        db.session.add(yeni)
        db.session.commit()
        flash("Duyuru oluşturuldu.", "success")
        return redirect(url_for('dashboard_ogrenci'))

    return render_template('duyuru/ekle.html')


@app.route('/dashboard/ogrenci')
@login_required
def dashboard_ogrenci():
    if current_user.rol != 'ogrenci':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    duyurular = Duyuru.query.order_by(Duyuru.tarih.desc()).all()
    return render_template('dashboard/dashboard_ogrenci.html', duyurular=duyurular)
@app.route('/mesajlar')
@login_required
def mesajlar():
    gelenler = Mesaj.query.filter_by(alici_id=current_user.id).order_by(Mesaj.tarih.desc()).all()
    gidenler = Mesaj.query.filter_by(gonderen_id=current_user.id).order_by(Mesaj.tarih.desc()).all()
    return render_template('mesaj/mesajlar.html', gelenler=gelenler, gidenler=gidenler)

# @app.route('/mesaj-gonder', methods=['GET', 'POST'])
# @login_required
# def mesaj_gonder():
#     kullanicilar = User.query.filter(User.id != current_user.id).all()
#     if request.method == 'POST':
#         alici_id = request.form.get('alici_id')
#         icerik = request.form.get('icerik')

#         mesaj = Mesaj(gonderen_id=current_user.id, alici_id=alici_id, icerik=icerik)
#         db.session.add(mesaj)
#         db.session.commit()
#         flash("Mesaj gönderildi.", "success")
#         return redirect(url_for('mesajlar'))

#     return render_template('mesaj/gonder.html', kullanicilar=kullanicilar)
@app.route('/mesaj-gonder', methods=['GET', 'POST'])
@login_required
def mesaj_gonder():
    if request.method == 'POST':
        alici_id = request.form.get('alici_id')
        icerik = request.form.get('icerik')

        yeni_mesaj = Mesaj(
            gonderen_id=current_user.id,
            alici_id=alici_id,
            icerik=icerik,
            tarih=datetime.utcnow()
        )
        db.session.add(yeni_mesaj)
        db.session.commit()
        flash("Mesaj gönderildi!", "success")
        return redirect(url_for('mesajlar'))

    kullanicilar = User.query.all()
    return render_template('mesaj/gonder.html', kullanicilar=kullanicilar)
@app.route('/not-aralik-ekle', methods=['GET', 'POST'])
@login_required
def not_aralik_ekle():
    if current_user.rol != 'ogretim_uyesi':
        flash("Bu sayfaya sadece öğretim üyeleri erişebilir.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            min_puan = float(request.form.get('min_puan'))
            max_puan = float(request.form.get('max_puan'))
            harf = request.form.get('harf')
            durum = request.form.get('durum')  # 'Geçti', 'Şartlı Geçti', 'Kaldı'
            
            yeni = NotAralik(
                min_puan=min_puan,
                max_puan=max_puan,
                harf=harf,
                durum=durum
            )
            db.session.add(yeni)
            db.session.commit()
            flash("Harf notu aralığı eklendi!", "success")
            return redirect(url_for('not_aralik_ekle'))
        except Exception as e:
            flash(f"Hata oluştu: {str(e)}", "danger")

    araliklar = NotAralik.query.order_by(NotAralik.min_puan.desc()).all()
    return render_template('dashboard/not_aralik_ekle.html', araliklar=araliklar)


def harf_notu_hesapla(ortalama):
    aralik = NotAralik.query.filter(
        NotAralik.min_puan <= ortalama,
        NotAralik.max_puan >= ortalama
    ).first()

    if aralik:
        return {
            "harf": aralik.harf,
            "durum": "Şartlı Geçti" if aralik.sartli_gecme else aralik.durum
        }
    
    return {
        "harf": "FF",
        "durum": "Kaldı"
    }




@app.route('/not-aralik-sil/<int:id>')
@login_required
def not_aralik_sil(id):
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    aralik = NotAralik.query.get_or_404(id)
    db.session.delete(aralik)
    db.session.commit()
    flash("Harf notu aralığı silindi.", "success")
    return redirect(url_for('not_aralik_ekle'))

@app.route('/not-aralik-duzenle/<int:id>', methods=['GET', 'POST'])
@login_required
def not_aralik_duzenle(id):
    if current_user.rol != 'ogretim_uyesi':
        flash("Yetkiniz yok!", "danger")
        return redirect(url_for('index'))

    aralik = NotAralik.query.get_or_404(id)

    if request.method == 'POST':
        aralik.min_puan = float(request.form.get('min_puan'))
        aralik.max_puan = float(request.form.get('max_puan'))
        aralik.harf = request.form.get('harf')
        aralik.durum = request.form.get('durum')
        db.session.commit()
        flash("Harf notu aralığı güncellendi!", "success")
        return redirect(url_for('not_aralik_ekle'))

    return render_template('dashboard/not_aralik_duzenle.html', aralik=aralik)

# @app.route('/yedekle')
# @login_required
# def yedekle():
#     if current_user.rol != 'admin':
#         flash("Bu işlemi yalnızca admin yapabilir.", "danger")
#         return redirect(url_for("index"))

#     return send_file("sqlite.db", as_attachment=True)
# @app.route('/geri-yukle', methods=['GET', 'POST'])
# @login_required
# def geri_yukle():
#     if current_user.rol != 'admin':
#         flash("Bu işlemi yalnızca admin yapabilir.", "danger")
#         return redirect(url_for("index"))

#     if request.method == 'POST':
#         file = request.files['yedek']
#         if file and file.filename.endswith('.db'):
#             file.save("sqlite.db")  # mevcut veritabanını üzerine yazar
#             flash("Veritabanı başarıyla yüklendi. Uygulama yeniden başlatılmalı.", "success")
#             return redirect(url_for("index"))
#         else:
#             flash("Lütfen geçerli bir .db dosyası yükleyin.", "danger")

#     return render_template("admin/geri_yukle.html")
@app.route('/admin-panel')
@login_required
def admin_panel():
    if current_user.rol != 'admin':
        flash("Bu sayfaya sadece admin erişebilir!", "danger")
        return redirect(url_for('index'))
    return render_template('dashboard/dashboard_admin.html')
@app.route('/yedekle')
@login_required
def yedekle():
    if current_user.rol != 'admin':
        flash("Bu işlemi yalnızca admin yapabilir.", "danger")
        return redirect(url_for("index"))
    return send_file("sqlite.db", as_attachment=True)

@app.route('/geri-yukle', methods=['GET', 'POST'])
@login_required
def geri_yukle():
    if current_user.rol != 'admin':
        flash("Bu işlemi yalnızca admin yapabilir.", "danger")
        return redirect(url_for("index"))

    if request.method == 'POST':
        file = request.files['yedek']
        if file and file.filename.endswith('.db'):
            file.save("sqlite.db")
            flash("Veritabanı başarıyla geri yüklendi.", "success")
            return redirect(url_for("index"))
        else:
            flash("Lütfen geçerli bir .db dosyası yükleyin.", "danger")
    return render_template("admin/geri_yukle.html")















if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
