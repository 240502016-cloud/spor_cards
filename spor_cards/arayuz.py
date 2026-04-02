import sys
import os
import random
import csv
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QTextEdit, QMessageBox, QCheckBox, QInputDialog, 
                             QStackedWidget, QComboBox, QLineEdit, QGraphicsDropShadowEffect, QSplitter,
                             QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QRect, QTimer, QPropertyAnimation
from PyQt5.QtGui import QPixmap, QPainter, QFont, QColor

from modeller import Futbolcu, Basketbolcu, Voleybolcu
from oyuncular import Kullanici, Bilgisayar
from stratejiler import OrtaStrateji

# ==============================================================================
# --- NYP: YARDIMCI VE VERİ YÖNETİMİ SINIFLARI ---
# ==============================================================================

class Araclar:
    """Genel yardımcı metotları barındıran statik sınıf."""
    @staticmethod
    def dosya_ismi_temizle(isim):
        isim = isim.replace(" ", "_")
        ceviriler = str.maketrans("ıİşŞçÇöÖüÜğĞ", "iIsScCoOuUgG")
        return isim.translate(ceviriler)

class KullaniciYoneticisi:
    """Veritabanı olmadan yerel JSON dosyası ile düz metin kullanıcı yönetimi."""
    DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kullanicilar.json")

    @classmethod
    def kullanici_yukle(cls):
        if not os.path.exists(cls.DOSYA):
            with open(cls.DOSYA, "w", encoding="utf-8") as f:
                json.dump({}, f)
        with open(cls.DOSYA, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def kayit_ol(cls, kullanici_adi, sifre):
        kullanicilar = cls.kullanici_yukle()
        
        if len(kullanici_adi) < 3 or len(sifre) < 3:
            return False, "Kullanıcı adı ve şifre en az 3 karakter olmalıdır!"
            
        if kullanici_adi in kullanicilar:
            return False, "Bu kullanıcı adı zaten kullanılıyor!"
            
        kullanicilar[kullanici_adi] = sifre
        with open(cls.DOSYA, "w", encoding="utf-8") as f:
            json.dump(kullanicilar, f, indent=4)
            
        return True, "Kayıt başarılı! Şimdi giriş yapabilirsiniz."

    @classmethod
    def giris_yap(cls, kullanici_adi, sifre):
        kullanicilar = cls.kullanici_yukle()
        
        if kullanici_adi not in kullanicilar:
            return False, "Böyle bir kullanıcı bulunamadı!"
            
        if kullanicilar[kullanici_adi] == sifre:
            return True, f"Hoş geldin, {kullanici_adi}!"
            
        return False, "Hatalı şifre!"

class ResimOnbellek:
    _onbellek = {}
    @classmethod
    def getir(cls, dosya_yolu, genislik, yukseklik):
        anahtar = (dosya_yolu, genislik, yukseklik)
        if anahtar not in cls._onbellek:
            tam_yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), dosya_yolu)
            pixmap = QPixmap(tam_yol)
            if not pixmap.isNull():
                cls._onbellek[anahtar] = pixmap.scaled(genislik, yukseklik, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            else:
                cls._onbellek[anahtar] = None
        return cls._onbellek[anahtar]

class VeriOkuyucu:
    @staticmethod
    def dosyadanKartlariOkur(dosya_adi):
        tam_yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), dosya_adi)
        if not os.path.exists(tam_yol):
            raise FileNotFoundError(f"'{tam_yol}' bulunamadı! Lütfen verileri içeren dosyayı ekleyin.")
        with open(tam_yol, 'r', encoding='utf-8') as f:
            return list(csv.reader(f))
            
    @staticmethod
    def nesnelereDonusturur(satirlar):
        liste = []
        sinif_haritasi = {"Futbolcu": Futbolcu, "Basketbolcu": Basketbolcu, "Voleybolcu": Voleybolcu}
        for i, r in enumerate(satirlar):
            if not r or len(r) < 9: continue
            sinif = sinif_haritasi.get(r[0])
            if sinif: liste.append(sinif(i, r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]))
        return liste

class MacIstatistik:
    def __init__(self):
        self.veriler = []
    def veriEkle(self, mesaj):
        temiz_mesaj = mesaj.replace('<b>', '').replace('</b>', '').replace('<font color=\'#00FF00\'>', '').replace('<font color=\'#FF5555\'>', '').replace('<font color=\'#FFA500\'>', '').replace('</font>', '')
        self.veriler.append(temiz_mesaj)
    def raporOlustur(self):
        return "\n".join(self.veriler)

# ==============================================================================
# --- OYUN YÖNETİCİSİ SINIFI (Tüm Mantık ve Oyun Motoru) ---
# ==============================================================================
class OyunYonetici:
    def __init__(self, kullanici, bilgisayar, strateji, log_callback, zorluk="Orta"):
        self.kullanici = kullanici
        self.bilgisayar = bilgisayar
        self.strateji = strateji
        self.istatistik = MacIstatistik()
        self.log_callback = log_callback 
        self.tur_sayisi = 1
        self.brans_sirasi = [Futbolcu, Basketbolcu, Voleybolcu]
        self.bilgisayar.moral = 80 if zorluk == "Zor" else (40 if zorluk == "Kolay" else 60)

    def log(self, metin):
        self.istatistik.veriEkle(metin); self.log_callback(metin)

    def kartlariDagit(self, tum_kartlar, beraberlik_test=False):
        import copy
        brans_sozlugu = {
            "Futbolcu": [k for k in tum_kartlar if isinstance(k, Futbolcu)],
            "Basketbolcu": [k for k in tum_kartlar if isinstance(k, Basketbolcu)],
            "Voleybolcu": [k for k in tum_kartlar if isinstance(k, Voleybolcu)]
        }
        for liste in brans_sozlugu.values(): random.shuffle(liste)
        
        if beraberlik_test:
            f, b, v = brans_sozlugu["Futbolcu"][0], brans_sozlugu["Basketbolcu"][0], brans_sozlugu["Voleybolcu"][0]
            self.kullanici.kartListesi = [copy.deepcopy(f) for _ in range(4)] + [copy.deepcopy(b) for _ in range(4)] + [copy.deepcopy(v) for _ in range(4)]
            self.bilgisayar.kartListesi = [copy.deepcopy(f) for _ in range(4)] + [copy.deepcopy(b) for _ in range(4)] + [copy.deepcopy(v) for _ in range(4)]
        else:
            self.kullanici.kartListesi = brans_sozlugu["Futbolcu"][:4] + brans_sozlugu["Basketbolcu"][:4] + brans_sozlugu["Voleybolcu"][:4]
            self.bilgisayar.kartListesi = brans_sozlugu["Futbolcu"][4:8] + brans_sozlugu["Basketbolcu"][4:8] + brans_sozlugu["Voleybolcu"][4:8]
            
        random.shuffle(self.kullanici.kartListesi); random.shuffle(self.bilgisayar.kartListesi)

    def oyunAkisiniYonet(self): return self.tur_sayisi <= 24

    def kartlariKarsilastir(self, k_kart, b_kart, ozellik, kp, bp, y_bonus_k, y_bonus_b):
        if kp > bp: return 1
        if bp > kp: return 2
        self.log("- Eşitlik! Branş İçi Yedek Özelliklere bakılıyor...")
        for yedek_oz in k_kart.ozellikler.keys():
            if yedek_oz != ozellik:
                if k_kart.ozellikler[yedek_oz] > b_kart.ozellikler[yedek_oz]: return 1
                if b_kart.ozellikler[yedek_oz] > k_kart.ozellikler[yedek_oz]: return 2
        self.log("- Eşitlik! Özel Yetenek Bonusu Etkisine bakılıyor...")
        if y_bonus_k > y_bonus_b: return 1
        if y_bonus_b > y_bonus_k: return 2
        self.log("- Eşitlik! Dayanıklılığa bakılıyor...")
        if k_kart.dayaniklilik > b_kart.dayaniklilik: return 1
        if b_kart.dayaniklilik > k_kart.dayaniklilik: return 2
        self.log("- Eşitlik! Enerjiye bakılıyor...")
        if k_kart.enerji > b_kart.enerji: return 1
        if b_kart.enerji > k_kart.enerji: return 2
        self.log("- Eşitlik! Seviyeye bakılıyor...")
        if k_kart.seviye > b_kart.seviye: return 1
        if b_kart.seviye > k_kart.seviye: return 2
        return 0

    def puanlariGuncelle(self, kazanan, k_kart, b_kart, y_bonus_k, y_bonus_b, brans_adi):
        k_enerji_kayip = -5 if kazanan == 1 else (-10 if kazanan == 2 else -3)
        b_enerji_kayip = -5 if kazanan == 2 else (-10 if kazanan == 1 else -3)
        if y_bonus_k > 0 or (k_kart.ozelYetenek and k_kart.ozelYetenek.ad in ["Veteran", "Defender"]): k_enerji_kayip -= 5
        if y_bonus_b > 0 or (b_kart.ozelYetenek and b_kart.ozelYetenek.ad in ["Veteran", "Defender"]): b_enerji_kayip -= 5

        if kazanan == 1:
            puan = 15 if y_bonus_k > 0 else 10
            if k_kart.enerji < 30: puan += 5
            if k_kart.seviyeAtladiOdulBekliyor:
                puan += 5; self.log("⭐ Seviye atladıktan sonraki ilk galibiyet! (+5 Puan)"); k_kart.seviyeAtladiOdulBekliyor = False
            self.log(f"<font color='#00E676'>Turu Kazandın! (+{puan} Puan)</font>")
            self.kullanici.skor += puan; self.kullanici.kazanilanTurSayisi += 1
            if y_bonus_k > 0: self.kullanici.ozelYetenekleKazanilanTurSayisi += 1
            self.kullanici.moralGuncelle("kazandi", brans_adi); self.bilgisayar.moralGuncelle("kaybetti", brans_adi)
            k_kart.deneyimPuani += 2; k_kart.kazanmaSayisi += 1; b_kart.kaybetmeSayisi += 1
        elif kazanan == 2:
            self.log("<font color='#FF5252'>Turu Kaybettin!</font>")
            self.bilgisayar.skor += (15 if y_bonus_b > 0 else 10); self.bilgisayar.kazanilanTurSayisi += 1
            if y_bonus_b > 0: self.bilgisayar.ozelYetenekleKazanilanTurSayisi += 1
            self.kullanici.moralGuncelle("kaybetti", brans_adi); self.bilgisayar.moralGuncelle("kazandi", brans_adi)
            b_kart.deneyimPuani += 2; b_kart.kazanmaSayisi += 1; k_kart.kaybetmeSayisi += 1
        else:
            self.log("<font color='#FFC107'>Tam Beraberlik! (Puan yok, kartlar yanmadı ancak enerji azaldı)</font>")
            self.kullanici.moralGuncelle("berabere", brans_adi); self.bilgisayar.moralGuncelle("berabere", brans_adi)
            k_kart.deneyimPuani += 1; b_kart.deneyimPuani += 1
            k_kart.kartKullanildiMi = False; b_kart.kartKullanildiMi = False
            k_kart.kullanimSayisi = max(0, k_kart.kullanimSayisi - 1); b_kart.kullanimSayisi = max(0, b_kart.kullanimSayisi - 1)

        k_kart.enerjiGuncelle(k_enerji_kayip); b_kart.enerjiGuncelle(b_enerji_kayip)

        for oyuncu_objesi in (self.kullanici, self.bilgisayar):
            if oyuncu_objesi.galibiyetSerisi == 3: 
                oyuncu_objesi.skor += 10; oyuncu_objesi.toplamGalibiyetSerisiSayisi += 1
                if oyuncu_objesi == self.kullanici: self.log("🔥 3'lü Seri! (+10 Puan)")
            elif oyuncu_objesi.galibiyetSerisi == 5: 
                oyuncu_objesi.skor += 20; oyuncu_objesi.toplamGalibiyetSerisiSayisi += 1
                if oyuncu_objesi == self.kullanici: self.log("🔥🔥 5'li Seri! (+20 Puan)")
        
        if k_kart.seviyeAtlaKontrol(): self.log(f"⭐ Tebrikler! {k_kart.sporcuAdi.replace('_', ' ')} Seviye {k_kart.seviye} oldu!")
        b_kart.seviyeAtlaKontrol()

    def kazananiBelirle(self):
        k, b = self.kullanici, self.bilgisayar
        if k.skor != b.skor: return ("SEN KAZANDIN!" if k.skor > b.skor else "BİLGİSAYAR KAZANDI!"), "Toplam Puan Üstünlüğü"
        if k.kazanilanTurSayisi != b.kazanilanTurSayisi: return ("SEN KAZANDIN!" if k.kazanilanTurSayisi > b.kazanilanTurSayisi else "BİLGİSAYAR KAZANDI!"), "En Fazla Tur Kazanma"
        if k.toplamGalibiyetSerisiSayisi != b.toplamGalibiyetSerisiSayisi: return ("SEN KAZANDIN!" if k.toplamGalibiyetSerisiSayisi > b.toplamGalibiyetSerisiSayisi else "BİLGİSAYAR KAZANDI!"), "Toplam Galibiyet Serisi"
        if k.kalanToplamEnerji() != b.kalanToplamEnerji(): return ("SEN KAZANDIN!" if k.kalanToplamEnerji() > b.kalanToplamEnerji() else "BİLGİSAYAR KAZANDI!"), "Kalan Toplam Enerji"
        if k.enYuksekSeviyeliKartSayisi() != b.enYuksekSeviyeliKartSayisi(): return ("SEN KAZANDIN!" if k.enYuksekSeviyeliKartSayisi() > b.enYuksekSeviyeliKartSayisi() else "BİLGİSAYAR KAZANDI!"), "Yüksek Seviye Kart Sayısı"
        return "TAM BERABERLİK!", "Tüm kurallarda eşitlik bozulmadı."

    def raporuDosyayaKaydet(self):
        try:
            with open("mac_raporu.txt", "w", encoding="utf-8") as f:
                f.write("HYBRID LEAGUE - MAÇ İSTATİSTİK RAPORU\n" + "="*45 + "\n")
                f.write(f"Senin Skorun: {self.kullanici.skor} | Bilgisayar Skoru: {self.bilgisayar.skor}\n" + "="*45 + "\n\n")
                f.write(self.istatistik.raporOlustur())
        except Exception as e: print("Rapor kaydedilemedi:", e)

    def turBaslat(self, secilen_kart_idx, manuel_ozellik=None):
        guncel_brans = self.brans_sirasi[(self.tur_sayisi - 1) % 3]
        brans_adi = guncel_brans.__name__
        k_kart = self.kullanici.kartSec(secilen_kart_idx, guncel_brans)
        b_kart = self.bilgisayar.kartSec(self.strateji, {"brans": guncel_brans, "moral": self.bilgisayar.moral})
        
        if not b_kart:
            self.log(f"\n<b>--- {self.tur_sayisi}. TUR ({brans_adi}) ---</b>")
            self.log("Bilgisayarın uygun kartı yok! Hükmen Kazandın (+8 Puan)")
            self.kullanici.skor += 8; self.kullanici.kazanilanTurSayisi += 1; self.tur_sayisi += 1
            return not self.oyunAkisiniYonet()
            
        ozellik = manuel_ozellik if manuel_ozellik else random.choice(list(k_kart.ozellikler.keys()))
        self.log(f"\n<b>--- {self.tur_sayisi}. TUR ({brans_adi}) ---</b>")
        
        k_kart.kullanimSayisi += 1; b_kart.kullanimSayisi += 1
        k_kart.kartKullanildiMi = b_kart.kartKullanildiMi = True
        
        for kart, sahip in [(k_kart, self.kullanici), (b_kart, self.bilgisayar)]:
            if kart.ozelYetenek and kart.ozelYetenek.ad == "Captain":
                sahip.moral = min(100, sahip.moral + 5)
                if sahip == self.kullanici: self.log("👑 Captain Yeteneği Aktif: Takım Morali +5 arttı!")
        
        kp = k_kart.performansHesapla(ozellik, self.kullanici.moral)
        bp = b_kart.performansHesapla(ozellik, self.bilgisayar.moral)
        
        y_bonus_k = k_kart.ozelYetenekUygula(b_kart, self.tur_sayisi, kp)
        if y_bonus_k > 0 and k_kart.ozelYetenek.ad == "Legend": self.log("✨ Legend Aktif: Özellik gücü İKİ KATINA çıktı!")
        kp += y_bonus_k
        
        y_bonus_b = b_kart.ozelYetenekUygula(k_kart, self.tur_sayisi, bp)
        bp += y_bonus_b
            
        if k_kart.ozelYetenek and k_kart.ozelYetenek.ad == "Defender": bp -= (y_bonus_b/2)
        if b_kart.ozelYetenek and b_kart.ozelYetenek.ad == "Defender": kp -= (y_bonus_k/2)

        self.log(f"Seçilen Özellik: <b>{ozellik}</b>\nSen: {k_kart.sporcuAdi.replace('_', ' ')} ({kp:.1f}) vs PC: {b_kart.sporcuAdi.replace('_', ' ')} ({bp:.1f})")
        kazanan = self.kartlariKarsilastir(k_kart, b_kart, ozellik, kp, bp, y_bonus_k, y_bonus_b)
        self.puanlariGuncelle(kazanan, k_kart, b_kart, y_bonus_k, y_bonus_b, brans_adi)
        self.tur_sayisi += 1
        return not self.oyunAkisiniYonet()

# ==============================================================================
# --- BİREYSEL KART VE DİNAMİK YERLEŞİM (Custom Widget) ---
# ==============================================================================
KART_SABLONLARI = {
    "Futbolcu": {"ebat": (365, 490), "bg_yol": "assets/futbol_bg.png", "stat_kisaltmalar": ["PNLT", "STMN", "KKK"], "layout": {"name": (20, 240, 325, 30, 15, "white", Qt.AlignCenter), "seviye": (20, 20, 60, 60, 24, "gold", Qt.AlignCenter), "enerji": (20, 345, 325, 30, 13, "white", Qt.AlignCenter), "stat1": (40, 295, 80, 30, 11, "white", Qt.AlignCenter), "stat2": (140, 295, 80, 30, 11, "white", Qt.AlignCenter), "stat3": (240, 295, 80, 30, 11, "white", Qt.AlignCenter), "xp": (20, 375, 325, 20, 10, "lightgray", Qt.AlignCenter)}},
    "Basketbolcu": {"ebat": (284, 473), "bg_yol": "assets/basket_bg.png", "stat_kisaltmalar": ["THRP", "TWP", "FS"], "layout": {"name": (10, 245, 264, 30, 13, "white", Qt.AlignCenter), "seviye": (10, 10, 50, 50, 20, "cyan", Qt.AlignCenter), "enerji": (10, 340, 264, 30, 11, "white", Qt.AlignCenter), "stat1": (25, 295, 70, 30, 9, "white", Qt.AlignCenter), "stat2": (105, 295, 70, 30, 9, "white", Qt.AlignCenter), "stat3": (185, 295, 70, 30, 9, "white", Qt.AlignCenter), "xp": (10, 370, 264, 20, 9, "lightgray", Qt.AlignCenter)}},
    "Voleybolcu": {"ebat": (370, 490), "bg_yol": "assets/volley_bg.png", "stat_kisaltmalar": ["SRVS", "BLOK", "SMAÇ"], "layout": {"name": (20, 275, 330, 30, 15, "white", Qt.AlignCenter), "seviye": (20, 20, 60, 60, 24, "red", Qt.AlignCenter), "enerji": (20, 365, 330, 30, 13, "white", Qt.AlignCenter), "stat1": (45, 315, 80, 30, 11, "white", Qt.AlignCenter), "stat2": (145, 315, 80, 30, 11, "white", Qt.AlignCenter), "stat3": (245, 315, 80, 30, 11, "white", Qt.AlignCenter), "xp": (20, 395, 330, 20, 10, "lightgray", Qt.AlignCenter)}}
}
ISTISNA_SABLONLAR = {"Zehra_Gunes": {"name": (50, 275, 290, 30, 12, "white", Qt.AlignCenter)}, "Gabi_Guimaraes": {"name": (50, 275, 290, 30, 12, "white", Qt.AlignCenter)}, "Dilay_Ozdemir": {}}

class CardWidget(QWidget):
    def __init__(self, sporcu):
        super().__init__()
        self.sporcu = sporcu
        self.sablon = KART_SABLONLARI.get(type(sporcu).__name__, KART_SABLONLARI["Futbolcu"])
        temiz_isim = Araclar.dosya_ismi_temizle(sporcu.sporcuAdi)
        genislik, yukseklik = self.sablon["ebat"]
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        resim_yolu = f"assets/{temiz_isim}.png"
        if not os.path.exists(os.path.join(base_dir, resim_yolu)): resim_yolu = f"assets/{sporcu.sporcuAdi}.png"
        if not os.path.exists(os.path.join(base_dir, resim_yolu)): resim_yolu = self.sablon["bg_yol"]
                
        self.bg_pixmap = ResimOnbellek.getir(resim_yolu, genislik, yukseklik)
        if self.bg_pixmap is None: self.bg_pixmap = QPixmap(genislik, yukseklik); self.bg_pixmap.fill(QColor("#2d3436"))
        self.setFixedSize(genislik, yukseklik)

        if sporcu.ozelYetenek:
            kullanim = " (KULLANILDI)" if sporcu.ozelYetenek.tek_kullanimlik and sporcu.ozelYetenek.kullanildi else ""
            self.setToolTip(f"<span style='font-size:12pt; font-weight:bold; color: #f1c40f;'>🛡️ {sporcu.ozelYetenek.ad}: {sporcu.ozelYetenek.aciklama}{kullanim}</span>")
            self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing); painter.setRenderHint(QPainter.TextAntialiasing)
        
        painter.setBrush(QColor(0, 0, 0, 50))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(5, 5, self.width()-5, self.height()-5, 10, 10)
        
        painter.drawPixmap(0, 0, self.bg_pixmap)
        s = self.sporcu
        durum = " (DIŞI)" if s.enerji <= 0 else (" (KRİTİK)" if s.enerji < 20 else "")
        kisaltmalar = self.sablon["stat_kisaltmalar"]
        
        veri_haritasi = {
            "name": s.sporcuAdi.replace("_", " "), "seviye": f"Lv{s.seviye}", "enerji": f"⚡ {s.enerji}{durum} | 🛡️ {s.ozelYetenek.ad if s.ozelYetenek else 'Yok'}",
            "stat1": f"{list(s.ozellikler.values())[0]} {kisaltmalar[0]}", "stat2": f"{list(s.ozellikler.values())[1]} {kisaltmalar[1]}",
            "stat3": f"{list(s.ozellikler.values())[2]} {kisaltmalar[2]}", "xp": f"XP: {s.deneyimPuani} | Oyn: {s.kullanimSayisi} | Kaz: {s.kazanmaSayisi} | Kay: {s.kaybetmeSayisi}"
        }
        
        layout = self.sablon["layout"].copy()
        if s.sporcuAdi in ISTISNA_SABLONLAR: layout.update(ISTISNA_SABLONLAR[s.sporcuAdi])

        for key, (x, y, w, h, fs, renk, hizalama) in layout.items():
            painter.setFont(QFont("Segoe UI", fs, QFont.Bold))
            painter.setPen(QColor(renk))
            painter.drawText(QRect(x, y, w, h), hizalama, veri_haritasi[key])
            
        if s.seviyeAtladiOdulBekliyor:
            painter.setFont(QFont("Segoe UI", 40)); painter.setPen(QColor("gold")); painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignRight, "⭐")
        painter.end()


# ==============================================================================
# --- GİRİŞ EKRANI (Kimlik Doğrulama / Register-Login) ---
# ==============================================================================
class GirisEkraniWidget(QWidget):
    def __init__(self, ana_pencere):
        super().__init__()
        self.ana_pencere = ana_pencere
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("girisEkrani")
        
        self.setStyleSheet("""
            #girisEkrani { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f2027, stop:0.5 #203a43, stop:1 #2c5364); 
            }
            QLabel { color: #ffffff; font-weight: 600; font-family: 'Segoe UI'; }
            QLineEdit { 
                background-color: rgba(255, 255, 255, 0.08); color: #ffffff; font-size: 16px; 
                padding: 12px 18px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.2); 
            }
            QLineEdit:focus { 
                border: 1px solid #00d2ff; background-color: rgba(255, 255, 255, 0.12); 
            }
            QPushButton { 
                font-size: 16px; font-weight: 800; border-radius: 12px; padding: 14px; 
                font-family: 'Segoe UI'; outline: none; border: none;
            }
            QPushButton:focus { outline: none; border: none; }
            QPushButton#btnGiris { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #11998e, stop:1 #38ef7d); color: white; 
            }
            QPushButton#btnGiris:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #15b9ab, stop:1 #42ff8f); 
            }
            QPushButton#btnKayit { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f2994a, stop:1 #f2c94c); color: #2c3e50; 
            }
            QPushButton#btnKayit:hover { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffaa5b, stop:1 #ffda5d); 
            }
            
            QMessageBox { background-color: #1e272e; border: 1px solid #485460; border-radius: 8px; }
            QMessageBox QLabel { color: #d2dae2; background-color: transparent; font-size: 14px; font-weight: normal; }
            QMessageBox QPushButton { 
                background-color: #0fb9b1; color: white; font-size: 14px; font-weight: bold; 
                border-radius: 6px; padding: 8px 24px; outline: none; 
            }
            QMessageBox QPushButton:hover { background-color: #2bcbba; }
        """)
        
        layout = QVBoxLayout()
        layout.addStretch()
        
        baslik = QLabel("HYBRID LEAGUE")
        baslik.setAlignment(Qt.AlignCenter)
        baslik.setStyleSheet("font-size: 55px; font-weight: 900; color: #00d2ff; margin-bottom: 5px; letter-spacing: 2px;")
        
        alt_baslik = QLabel("Sisteme Giriş Yapın")
        alt_baslik.setAlignment(Qt.AlignCenter)
        alt_baslik.setStyleSheet("font-size: 18px; color: #bdc3c7; margin-bottom: 30px;")
        
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        
        self.txt_kullanici = QLineEdit()
        self.txt_kullanici.setPlaceholderText("👤 Kullanıcı Adı")
        self.txt_kullanici.setFixedWidth(380)
        
        self.txt_sifre = QLineEdit()
        self.txt_sifre.setPlaceholderText("🔑 Şifre")
        self.txt_sifre.setEchoMode(QLineEdit.Password) 
        self.txt_sifre.setFixedWidth(380)
        
        btn_giris = QPushButton("🔓 GİRİŞ YAP")
        btn_giris.setObjectName("btnGiris")
        btn_giris.setFixedWidth(380)
        btn_giris.setCursor(Qt.PointingHandCursor)
        btn_giris.clicked.connect(self.giris_yap)
        
        shadow_giris = QGraphicsDropShadowEffect()
        shadow_giris.setBlurRadius(15); shadow_giris.setColor(QColor(17, 153, 142, 150)); shadow_giris.setOffset(0, 4)
        btn_giris.setGraphicsEffect(shadow_giris)

        btn_kayit = QPushButton("📝 YENİ HESAP OLUŞTUR")
        btn_kayit.setObjectName("btnKayit")
        btn_kayit.setFixedWidth(380)
        btn_kayit.setCursor(Qt.PointingHandCursor)
        btn_kayit.clicked.connect(self.kayit_ol)

        shadow_kayit = QGraphicsDropShadowEffect()
        shadow_kayit.setBlurRadius(15); shadow_kayit.setColor(QColor(242, 153, 74, 150)); shadow_kayit.setOffset(0, 4)
        btn_kayit.setGraphicsEffect(shadow_kayit)

        for w in [self.txt_kullanici, self.txt_sifre]:
            form_layout.addWidget(w, alignment=Qt.AlignCenter)
            
        layout.addWidget(baslik, alignment=Qt.AlignCenter)
        layout.addWidget(alt_baslik, alignment=Qt.AlignCenter)
        layout.addLayout(form_layout)
        layout.addSpacing(25)
        layout.addWidget(btn_giris, alignment=Qt.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(btn_kayit, alignment=Qt.AlignCenter)
        
        layout.addStretch()
        self.setLayout(layout)

    def giris_yap(self):
        kadi = self.txt_kullanici.text().strip()
        sifre = self.txt_sifre.text().strip()
        
        basarili_mi, mesaj = KullaniciYoneticisi.giris_yap(kadi, sifre)
        if basarili_mi:
            self.txt_sifre.clear()
            self.ana_pencere.show_menu()
        else:
            QMessageBox.warning(self, "Hata", mesaj)

    def kayit_ol(self):
        kadi = self.txt_kullanici.text().strip()
        sifre = self.txt_sifre.text().strip()
        
        basarili_mi, mesaj = KullaniciYoneticisi.kayit_ol(kadi, sifre)
        if basarili_mi:
            QMessageBox.information(self, "Kayıt Başarılı", mesaj)
            self.txt_sifre.clear()
        else:
            QMessageBox.warning(self, "Kayıt Hatası", mesaj)


# ==============================================================================
# --- OYUN EKRANI (Game Widget) ---
# ==============================================================================
class OyunEkraniGUI(QWidget):
    def __init__(self, ana_pencere):
        super().__init__()
        self.ana_pencere = ana_pencere
        
        self.setAttribute(Qt.WA_StyledBackground, True); self.setObjectName("oyunEkrani")
        zorluk = self.ana_pencere.ayarlar["zorluk"]
        self.pc_kartlari_gorunsun = self.ana_pencere.ayarlar["pc_kart_goster"]
        self.manuel_secim_aktif = self.ana_pencere.ayarlar["manuel_secim"]
        
        self.setStyleSheet("""
            #oyunEkrani { background-color: #0B0E1B; }
            QWidget { color: #f1f5f9; font-family: 'Segoe UI'; }
            QStackedWidget { background-color: transparent; border: none; }
            QLabel { background-color: transparent; color: #f8fafc; }
            
            QPushButton { 
                background-color: #3b82f6; color: white; border-radius: 8px; padding: 12px; 
                font-weight: bold; font-size: 14px; border: none; outline: none;
            }
            QPushButton:focus { outline: none; border: none; }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:disabled { background-color: #334155; color: #94a3b8; }
            
            QTextEdit { 
                background-color: #1e293b; color: #10b981; border: 1px solid #334155; 
                border-radius: 10px; font-family: 'Consolas'; font-size: 14px; padding: 12px;
            }
            QTextEdit QScrollBar:vertical { background: #0f172a; width: 12px; border-radius: 6px; }
            QTextEdit QScrollBar::handle:vertical { background: #475569; border-radius: 6px; }
            QInputDialog { background-color: #1e293b; color: white; }
            
            /* Sürüklenebilir terminal (QSplitter) stil ayarları */
            QSplitter::handle {
                background-color: #334155;
                height: 5px;
                margin: 5px 0px;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #3b82f6;
            }
            QSplitter::handle:pressed {
                background-color: #60a5fa;
            }
        """)
        
        try: tum_kartlar = VeriOkuyucu.nesnelereDonusturur(VeriOkuyucu.dosyadanKartlariOkur('sporcular.csv'))
        except Exception as e: QMessageBox.critical(self, "Kritik Hata", str(e)); sys.exit()
            
        self.yonetici = OyunYonetici(Kullanici(1), Bilgisayar(2), OrtaStrateji(), self.log_ekrana_yaz, zorluk)
        beraberlik_aktif = self.ana_pencere.ayarlar.get("beraberlik_test", False)
        self.yonetici.kartlariDagit(tum_kartlar, beraberlik_test=beraberlik_aktif)
        
        self.fade_timer = QTimer()
        self.fade_timer.setSingleShot(True)
        self.fade_timer.timeout.connect(self.mesaji_temizle)
        
        self.init_ui(); self.arayuz_guncelle()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Üst Kısım (Topbar, Kartlar ve Tur Sonucu) ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        top_bar_layout = QHBoxLayout()
        self.btn_ana_menu = QPushButton("◀ Ana Menü")
        self.btn_ana_menu.setStyleSheet("background-color: #f59e0b; color: #fff; padding: 10px 20px; font-weight: 800;")
        self.btn_ana_menu.setCursor(Qt.PointingHandCursor)
        self.btn_ana_menu.clicked.connect(self.ana_menuye_don)
        
        self.lbl_skor = QLabel("🏆 SKOR: Sen 0 - 0 PC")
        self.lbl_moral = QLabel("🔥 MORAL: Sen 60 - 60 PC")
        self.lbl_tur = QLabel("📅 TUR: 1 (Futbolcu)")
        
        label_style = "font-size: 16px; font-weight: 800; background-color: #1e293b; padding: 12px 20px; border-radius: 8px; border: 1px solid #334155;"
        for lbl in [self.lbl_skor, self.lbl_moral, self.lbl_tur]: 
            lbl.setStyleSheet(label_style)
            
        top_bar_layout.addWidget(self.btn_ana_menu)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.lbl_skor)
        top_bar_layout.addSpacing(15)
        top_bar_layout.addWidget(self.lbl_moral)
        top_bar_layout.addSpacing(15)
        top_bar_layout.addWidget(self.lbl_tur)
        
        cards_layout = QHBoxLayout()
        cards_layout.setContentsMargins(0, 10, 0, 10)
        
        kul_layout = QVBoxLayout()
        self.lbl_kul_durum = QLabel("SENİN KARTIN (0/0)")
        self.lbl_kul_durum.setAlignment(Qt.AlignCenter)
        self.lbl_kul_durum.setStyleSheet("font-size: 20px; font-weight: 900; color: #10b981; letter-spacing: 1px; margin-bottom: 10px;")
        self.kullanici_stacked = QStackedWidget()
        
        nav_k_layout = QHBoxLayout()
        self.btn_prev_k = QPushButton("◀ Önceki")
        self.btn_next_k = QPushButton("Sonraki ▶")
        for btn in [self.btn_prev_k, self.btn_next_k]: btn.setCursor(Qt.PointingHandCursor)
        self.btn_prev_k.clicked.connect(self.k_onceki); self.btn_next_k.clicked.connect(self.k_sonraki)
        nav_k_layout.addWidget(self.btn_prev_k); nav_k_layout.addWidget(self.btn_next_k)
        
        kul_layout.addWidget(self.lbl_kul_durum); kul_layout.addWidget(self.kullanici_stacked, alignment=Qt.AlignCenter); kul_layout.addLayout(nav_k_layout)
        
        pc_layout = QVBoxLayout()
        self.lbl_pc_durum = QLabel("BİLGİSAYAR (0/0)")
        self.lbl_pc_durum.setAlignment(Qt.AlignCenter)
        self.lbl_pc_durum.setStyleSheet("font-size: 20px; font-weight: 900; color: #ef4444; letter-spacing: 1px; margin-bottom: 10px;")
        self.pc_stacked = QStackedWidget()
        
        nav_p_layout = QHBoxLayout()
        self.btn_prev_p = QPushButton("◀ Önceki")
        self.btn_next_p = QPushButton("Sonraki ▶")
        for btn in [self.btn_prev_p, self.btn_next_p]: btn.setCursor(Qt.PointingHandCursor)
        self.btn_prev_p.clicked.connect(self.p_onceki); self.btn_next_p.clicked.connect(self.p_sonraki)
        nav_p_layout.addWidget(self.btn_prev_p); nav_p_layout.addWidget(self.btn_next_p)
        
        pc_layout.addWidget(self.lbl_pc_durum); pc_layout.addWidget(self.pc_stacked, alignment=Qt.AlignCenter); pc_layout.addLayout(nav_p_layout)
        
        if not self.pc_kartlari_gorunsun:
            self.lbl_pc_durum.setText("RAKİP KARTI (GİZLİ)")
            self.lbl_pc_durum.setStyleSheet("font-size: 20px; font-weight: 900; color: #64748b; letter-spacing: 1px; margin-bottom: 10px;")
            self.pc_stacked.hide(); self.btn_prev_p.hide(); self.btn_next_p.hide()
        
        cards_layout.addLayout(kul_layout); cards_layout.addLayout(pc_layout)
        
        # Dinamik Sonuç Metni
        self.lbl_tur_sonucu = QLabel("")
        self.lbl_tur_sonucu.setAlignment(Qt.AlignCenter)
        
        self.opacity_effect = QGraphicsOpacityEffect()
        self.lbl_tur_sonucu.setGraphicsEffect(self.opacity_effect)
        
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(1500)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        
        top_layout.addLayout(top_bar_layout)
        top_layout.addLayout(cards_layout)
        top_layout.addWidget(self.lbl_tur_sonucu)
        
        # --- Alt Kısım (Terminal / Log Ekranı) ---
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        rapor_lbl = QLabel("MAÇ RAPORU VE İSTATİSTİKLER (Boyutu ayarlanabilir)")
        rapor_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8; margin-top: 5px;")
        
        self.log_ekrani = QTextEdit()
        self.log_ekrani.setReadOnly(True)
        
        self.btn_oyna = QPushButton("🚀 EKRANDAKİ KARTI OYNA")
        self.btn_oyna.setCursor(Qt.PointingHandCursor)
        self.btn_oyna.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669); color: white; font-size: 22px; font-weight: 900; padding: 20px; border-radius: 12px; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981); }
            QPushButton:disabled { background: #334155; color: #64748b; }
        """)
        self.btn_oyna.setEnabled(False); self.btn_oyna.clicked.connect(self.tur_baslat_ui)
        
        bottom_layout.addWidget(rapor_lbl)
        bottom_layout.addWidget(self.log_ekrani)
        bottom_layout.addWidget(self.btn_oyna)

        # Splitter (Yukarı-aşağı çekilebilir alan)
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(top_widget)
        self.splitter.addWidget(bottom_widget)
        
        # Başlangıç ekran paylarını ayarlama (Üst kısım daha geniş)
        self.splitter.setStretchFactor(0, 7)
        self.splitter.setStretchFactor(1, 3)

        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

    def mesaji_temizle(self):
        self.fade_anim.start()

    def ana_menuye_don(self):
        if QMessageBox.question(self, "Onay", "Oyun ilerlemesi silinecek. Emin misiniz?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes: self.ana_pencere.show_menu()
    def log_ekrana_yaz(self, metin): self.log_ekrani.append(metin)
    
    def k_onceki(self):
        idx = self.kullanici_stacked.currentIndex()
        if idx > 0: self.kullanici_stacked.setCurrentIndex(idx - 1); self.k_durum_guncelle()
    def k_sonraki(self):
        idx = self.kullanici_stacked.currentIndex()
        if idx < self.kullanici_stacked.count() - 1: self.kullanici_stacked.setCurrentIndex(idx + 1); self.k_durum_guncelle()
    def p_onceki(self):
        idx = self.pc_stacked.currentIndex()
        if idx > 0: self.pc_stacked.setCurrentIndex(idx - 1); self.p_durum_guncelle()
    def p_sonraki(self):
        idx = self.pc_stacked.currentIndex()
        if idx < self.pc_stacked.count() - 1: self.pc_stacked.setCurrentIndex(idx + 1); self.p_durum_guncelle()

    def k_durum_guncelle(self):
        count = self.kullanici_stacked.count(); idx = self.kullanici_stacked.currentIndex()
        if count > 0:
            self.lbl_kul_durum.setText(f"SENİN KARTIN ({idx+1}/{count})")
            self.btn_prev_k.setEnabled(idx > 0); self.btn_next_k.setEnabled(idx < count - 1)
            k_kart = self.yonetici.kullanici.kartSec(idx, self.yonetici.brans_sirasi[(self.yonetici.tur_sayisi - 1) % 3])
            if k_kart and k_kart.enerji > 0:
                self.btn_oyna.setEnabled(True); self.btn_oyna.setText("🚀 EKRANDAKİ KARTI OYNA")
            else:
                self.btn_oyna.setEnabled(False); self.btn_oyna.setText("❌ BU KART OYNAYAMAZ (ENERJİ YETERSİZ)")
        else: self.lbl_kul_durum.setText("SENİN KARTIN (0/0)"); self.btn_oyna.setEnabled(False)

    def p_durum_guncelle(self):
        if not self.pc_kartlari_gorunsun: return
        count = self.pc_stacked.count()
        idx = self.pc_stacked.currentIndex()
        if count > 0: 
            self.lbl_pc_durum.setText(f"BİLGİSAYAR ({idx+1}/{count})")
            self.btn_prev_p.setEnabled(idx > 0)
            self.btn_next_p.setEnabled(idx < count - 1)
        else: 
            self.lbl_pc_durum.setText("BİLGİSAYAR (0/0)")

    def arayuz_guncelle(self):
        for stacked in (self.kullanici_stacked, self.pc_stacked):
            while stacked.count() > 0:
                widget = stacked.widget(0); stacked.removeWidget(widget); widget.deleteLater()
        guncel_brans = self.yonetici.brans_sirasi[(self.yonetici.tur_sayisi - 1) % 3]
        for k in self.yonetici.kullanici.kartListesi:
            if isinstance(k, guncel_brans): self.kullanici_stacked.addWidget(CardWidget(k))
        for k in self.yonetici.bilgisayar.kartListesi:
            if isinstance(k, guncel_brans): self.pc_stacked.addWidget(CardWidget(k))
                
        self.kullanici_stacked.setCurrentIndex(0); self.pc_stacked.setCurrentIndex(0)
        self.k_durum_guncelle(); self.p_durum_guncelle()
        self.lbl_skor.setText(f"🏆 SKOR: Sen {self.yonetici.kullanici.skor} - {self.yonetici.bilgisayar.skor} PC")
        self.lbl_moral.setText(f"🔥 MORAL: Sen {self.yonetici.kullanici.moral} - {self.yonetici.bilgisayar.moral} PC")
        self.lbl_tur.setText(f"📅 TUR: {self.yonetici.tur_sayisi}/24 ({guncel_brans.__name__})")

    def tur_baslat_ui(self):
        idx = self.kullanici_stacked.currentIndex()
        if idx == -1: return
        manuel_ozellik = None
        if self.manuel_secim_aktif:
            k_kart = self.yonetici.kullanici.kartSec(idx, self.yonetici.brans_sirasi[(self.yonetici.tur_sayisi - 1) % 3])
            secilen, ok = QInputDialog.getItem(self, "Özellik Seçimi", f"{k_kart.sporcuAdi.replace('_', ' ')} için özellik seçin:", list(k_kart.ozellikler.keys()), 0, False)
            if not ok or not secilen: return
            manuel_ozellik = secilen
            
        # Tur başlamadan önceki kazanılan tur sayıları (Kıyaslama için)
        eski_k_tur = self.yonetici.kullanici.kazanilanTurSayisi
        eski_p_tur = self.yonetici.bilgisayar.kazanilanTurSayisi
            
        oyun_bitti_mi = self.yonetici.turBaslat(idx, manuel_ozellik)
        
        # Tur sonrasındaki kazanılan tur sayıları
        yeni_k_tur = self.yonetici.kullanici.kazanilanTurSayisi
        yeni_p_tur = self.yonetici.bilgisayar.kazanilanTurSayisi
        
        # Ekranda sonucu belirginleştirme
        self.fade_timer.stop()
        self.fade_anim.stop()
        if yeni_k_tur > eski_k_tur:
            self.lbl_tur_sonucu.setText("🎉 TURU KAZANDIN! 🎉")
            self.lbl_tur_sonucu.setStyleSheet("font-size: 32px; font-weight: 900; color: #10b981; margin: 5px;")
        elif yeni_p_tur > eski_p_tur:
            self.lbl_tur_sonucu.setText("💀 TURU KAYBETTİN! 💀")
            self.lbl_tur_sonucu.setStyleSheet("font-size: 32px; font-weight: 900; color: #ef4444; margin: 5px;")
        else:
            self.lbl_tur_sonucu.setText("🤝 BERABERE! 🤝")
            self.lbl_tur_sonucu.setStyleSheet("font-size: 32px; font-weight: 900; color: #f59e0b; margin: 5px;")
            
        self.opacity_effect.setOpacity(1.0)
        self.fade_timer.start(2000)
        
        self.btn_oyna.setEnabled(False); self.arayuz_guncelle()
        
        if oyun_bitti_mi:
            self.log_ekrana_yaz("\n<b>--- LİG SONA ERDİ ---</b>"); self.yonetici.raporuDosyayaKaydet() 
            kazanan, sebep = self.yonetici.kazananiBelirle()
            msg = f"<font color='white'>🏆 ŞAMPİYON: {kazanan}<br><br>Sebep: {sebep}<br><br>Senin Skorun: {self.yonetici.kullanici.skor}<br>PC Skoru: {self.yonetici.bilgisayar.skor}<br><br>(Not: Maç istatistikleri kaydedildi!)</font>"
            QMessageBox.information(self, "Lig Bitti", msg)
            self.ana_pencere.show_menu()


# ==============================================================================
# --- AYARLAR MENÜSÜ ---
# ==============================================================================
class AyarlarWidget(QWidget):
    def __init__(self, ana_pencere):
        super().__init__()
        self.ana_pencere = ana_pencere
        
        self.setAttribute(Qt.WA_StyledBackground, True); self.setObjectName("ayarlarEkrani")
        self.setStyleSheet("""
            #ayarlarEkrani { background-color: #0f172a; }
            QLabel { color: #f8fafc; font-size: 18px; font-weight: 600; font-family: 'Segoe UI'; }
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb); 
                color: white; font-size: 18px; font-weight: bold; border-radius: 12px; padding: 15px; border: none; outline: none;
            }
            QPushButton:focus { outline: none; border: none; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6); }
            QComboBox { 
                font-size: 16px; color: white; padding: 10px; background-color: #1e293b; 
                border: 1px solid #334155; border-radius: 8px; font-weight: bold;
            }
            QComboBox::drop-down { border: none; }
            QCheckBox { font-size: 18px; color: #f8fafc; padding: 5px; font-weight: 500; }
            QCheckBox::indicator { width: 24px; height: 24px; border-radius: 4px; border: 2px solid #3b82f6; }
            QCheckBox::indicator:checked { background-color: #3b82f6; }
        """)
        
        layout = QVBoxLayout(); layout.addStretch() 
        baslik = QLabel("⚙️ SİSTEM AYARLARI")
        baslik.setAlignment(Qt.AlignCenter)
        baslik.setStyleSheet("font-size: 45px; font-weight: 900; color: #e2e8f0; margin-bottom: 30px; letter-spacing: 2px;")
        
        zorluk_layout = QHBoxLayout()
        self.cmb_zorluk = QComboBox()
        self.cmb_zorluk.addItems(["Kolay", "Orta", "Zor"])
        self.cmb_zorluk.setFixedWidth(200)
        lbl_zorluk = QLabel("🕹️ Oyun Zorluğu:")
        zorluk_layout.addStretch(); zorluk_layout.addWidget(lbl_zorluk); zorluk_layout.addSpacing(15); zorluk_layout.addWidget(self.cmb_zorluk); zorluk_layout.addStretch()
        
        pc_kart_layout = QHBoxLayout()
        self.chk_pc_kart = QCheckBox("Rakip (PC) Kartlarını Açık Göster")
        self.chk_pc_kart.setCursor(Qt.PointingHandCursor)
        pc_kart_layout.addStretch(); pc_kart_layout.addWidget(self.chk_pc_kart); pc_kart_layout.addStretch()
        
        manuel_layout = QHBoxLayout()
        self.chk_manuel = QCheckBox("Manuel Özellik Seçimi (Karşılaştırılacak özelliği ben seçerim)")
        self.chk_manuel.setCursor(Qt.PointingHandCursor)
        manuel_layout.addStretch(); manuel_layout.addWidget(self.chk_manuel); manuel_layout.addStretch()
        
        beraberlik_layout = QHBoxLayout()
        self.chk_beraberlik_test = QCheckBox("🧪 Beraberlik Test Senaryosu (PC'ye seninle %100 aynı kartlar verilir)")
        self.chk_beraberlik_test.setCursor(Qt.PointingHandCursor)
        self.chk_beraberlik_test.setStyleSheet("color: #facc15; font-weight: bold;")
        beraberlik_layout.addStretch(); beraberlik_layout.addWidget(self.chk_beraberlik_test); beraberlik_layout.addStretch()
        
        btn_kaydet = QPushButton("💾 KAYDET VE ANA MENÜYE DÖN")
        btn_kaydet.setFixedWidth(400); btn_kaydet.setCursor(Qt.PointingHandCursor); btn_kaydet.clicked.connect(self.ayarlari_kaydet)
        
        layout.addWidget(baslik, alignment=Qt.AlignCenter); layout.addSpacing(40)
        layout.addLayout(zorluk_layout); layout.addSpacing(25)
        layout.addLayout(pc_kart_layout); layout.addSpacing(20)
        layout.addLayout(manuel_layout); layout.addSpacing(20)
        layout.addLayout(beraberlik_layout); layout.addSpacing(40)
        layout.addWidget(btn_kaydet, alignment=Qt.AlignCenter); layout.addStretch() 
        self.setLayout(layout)

    def ayarlari_yukle(self):
        self.cmb_zorluk.setCurrentText(self.ana_pencere.ayarlar["zorluk"]); self.chk_pc_kart.setChecked(self.ana_pencere.ayarlar["pc_kart_goster"]); self.chk_manuel.setChecked(self.ana_pencere.ayarlar["manuel_secim"])
        self.chk_beraberlik_test.setChecked(self.ana_pencere.ayarlar.get("beraberlik_test", False))
    def ayarlari_kaydet(self):
        self.ana_pencere.ayarlar["zorluk"] = self.cmb_zorluk.currentText(); self.ana_pencere.ayarlar["pc_kart_goster"] = self.chk_pc_kart.isChecked(); self.ana_pencere.ayarlar["manuel_secim"] = self.chk_manuel.isChecked()
        self.ana_pencere.ayarlar["beraberlik_test"] = self.chk_beraberlik_test.isChecked()
        self.ana_pencere.show_menu()


# ==============================================================================
# --- ANA MENÜ (Oyun Seçenekleri Ekranı) ---
# ==============================================================================
class AnaMenuWidget(QWidget):
    def __init__(self, ana_pencere):
        super().__init__()
        self.ana_pencere = ana_pencere
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("anaMenuWidget")
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        bg_path = os.path.join(base_dir, "assets", "menu_bg.jpg").replace("\\", "/")
        
        self.setStyleSheet(f"""
            #anaMenuWidget {{ 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #020617, stop:1 #1e293b); 
                border-image: url({bg_path}) 0 0 0 0 stretch stretch;
            }}
            QPushButton {{ 
                font-family: 'Segoe UI'; font-size: 20px; font-weight: 900; 
                border-radius: 15px; padding: 18px; border: none; color: white; outline: none;
            }}
            QPushButton:focus {{ outline: none; border: none; }}
            QPushButton#btnBasla {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #d97706); }}
            QPushButton#btnBasla:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fbbf24, stop:1 #f59e0b); }}
            
            QPushButton#btnAyarlar {{ background: rgba(59, 130, 246, 0.9); }}
            QPushButton#btnAyarlar:hover {{ background: rgba(96, 165, 250, 1); }}
            
            QPushButton#btnCikis {{ background: rgba(239, 68, 68, 0.9); }}
            QPushButton#btnCikis:hover {{ background: rgba(248, 113, 113, 1); }}
        """)
        
        layout = QVBoxLayout(); layout.addStretch()
        
        baslik = QLabel("HYBRID LEAGUE")
        baslik.setAlignment(Qt.AlignCenter)
        baslik.setStyleSheet("font-size: 65px; font-weight: 900; color: #facc15; font-family: 'Segoe UI Black'; text-shadow: 2px 2px 10px rgba(0,0,0,0.8); background-color: transparent;")
        
        alt_baslik = QLabel("Gelişmiş Kart Simülasyonu • v1.0")
        alt_baslik.setAlignment(Qt.AlignCenter)
        alt_baslik.setStyleSheet("font-size: 22px; color: #e2e8f0; font-weight: 600; background-color: transparent; letter-spacing: 2px;")
        
        btn_basla = QPushButton("▶ OYUNA BAŞLA")
        btn_basla.setObjectName("btnBasla"); btn_basla.setFixedWidth(420); btn_basla.setCursor(Qt.PointingHandCursor)
        btn_basla.clicked.connect(self.ana_pencere.start_game)
        
        btn_ayarlar = QPushButton("⚙️ AYARLAR")
        btn_ayarlar.setObjectName("btnAyarlar"); btn_ayarlar.setFixedWidth(420); btn_ayarlar.setCursor(Qt.PointingHandCursor)
        btn_ayarlar.clicked.connect(self.ana_pencere.show_ayarlar)
        
        btn_cikis = QPushButton("ÇIKIŞ YAP VE FARKLI HESAPLA GİR")
        btn_cikis.setObjectName("btnCikis"); btn_cikis.setFixedWidth(420); btn_cikis.setCursor(Qt.PointingHandCursor)
        btn_cikis.clicked.connect(self.ana_pencere.show_login)
        
        for btn in [btn_basla, btn_ayarlar, btn_cikis]:
            shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 180)); shadow.setOffset(0, 5)
            btn.setGraphicsEffect(shadow)
        
        layout.addWidget(baslik, alignment=Qt.AlignCenter); layout.addSpacing(5)
        layout.addWidget(alt_baslik, alignment=Qt.AlignCenter); layout.addSpacing(60)
        layout.addWidget(btn_basla, alignment=Qt.AlignCenter); layout.addSpacing(20)
        layout.addWidget(btn_ayarlar, alignment=Qt.AlignCenter); layout.addSpacing(20)
        layout.addWidget(btn_cikis, alignment=Qt.AlignCenter)
        layout.addStretch()
        self.setLayout(layout)

# ==============================================================================
# --- APP YÖNETİCİSİ (Pencereler Arası Geçiş ve Global Ayarlar) ---
# ==============================================================================
class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hybrid League")
        self.setGeometry(50, 50, 1400, 900)
        
        self.setStyleSheet("""
            QMessageBox { background-color: #1e293b; color: white; border: 2px solid #3b82f6; border-radius: 10px; }
            QMessageBox QLabel { color: #ffffff; font-size: 14px; min-width: 300px; padding: 10px; background-color: transparent; }
            QMessageBox QPushButton { background-color: #3b82f6; color: white; padding: 8px 20px; border-radius: 5px; font-weight: bold; }
            QMessageBox QPushButton:hover { background-color: #2563eb; }
        """)
        
        self.ayarlar = {"zorluk": "Orta", "pc_kart_goster": False, "manuel_secim": False, "beraberlik_test": False}
        self.aktif_kullanici = None
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.giris_widget = GirisEkraniWidget(self)
        self.menu_widget = AnaMenuWidget(self)
        self.ayarlar_widget = AyarlarWidget(self)
        
        self.stacked_widget.addWidget(self.giris_widget)
        self.stacked_widget.addWidget(self.menu_widget)
        self.stacked_widget.addWidget(self.ayarlar_widget)
        
        self.show_login()
        
    def show_login(self):
        self.aktif_kullanici = None 
        self.stacked_widget.setCurrentWidget(self.giris_widget)

    def show_menu(self):
        self.stacked_widget.setCurrentWidget(self.menu_widget)
        
    def show_ayarlar(self):
        self.ayarlar_widget.ayarlari_yukle()
        self.stacked_widget.setCurrentWidget(self.ayarlar_widget)
        
    def start_game(self):
        self.game_widget = OyunEkraniGUI(self)
        self.stacked_widget.addWidget(self.game_widget)
        self.stacked_widget.setCurrentWidget(self.game_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = AppWindow()
    win.show()
    sys.exit(app.exec_())
