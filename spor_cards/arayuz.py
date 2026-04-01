import sys
import os
import random
import csv
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QTextEdit, QMessageBox, QCheckBox, QInputDialog, QStackedWidget, QComboBox)
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPixmap, QPainter, QFont, QColor
from modeller import Futbolcu, Basketbolcu, Voleybolcu
from oyuncular import Kullanici, Bilgisayar
from stratejiler import OrtaStrateji

# ==============================================================================
# --- NYP: YARDIMCI VE OPTİMİZASYON SINIFLARI ---
# ==============================================================================

class Araclar:
    """Genel yardımcı metotları barındıran statik sınıf."""
    @staticmethod
    def dosya_ismi_temizle(isim):
        isim = isim.replace(" ", "_")
        ceviriler = str.maketrans("ıİşŞçÇöÖüÜğĞ", "iIsScCoOuUgG")
        return isim.translate(ceviriler)

class ResimOnbellek:
    """
    Flyweight Design Pattern: Resimlerin diskten tekrar tekrar okunmasını engeller.
    RAM ve CPU kullanımını optimize ederek oyunun akıcı çalışmasını sağlar.
    """
    _onbellek = {}

    @classmethod
    def getir(cls, dosya_yolu, genislik, yukseklik):
        anahtar = (dosya_yolu, genislik, yukseklik)
        if anahtar not in cls._onbellek:
            pixmap = QPixmap(dosya_yolu)
            if not pixmap.isNull():
                cls._onbellek[anahtar] = pixmap.scaled(genislik, yukseklik, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            else:
                cls._onbellek[anahtar] = None
        return cls._onbellek[anahtar]

class VeriOkuyucu:
    """SRP: Sadece veri okuma ve nesne dönüştürme işlerinden sorumludur."""
    @staticmethod
    def dosyadanKartlariOkur(dosya_adi):
        if not os.path.exists(dosya_adi):
            raise FileNotFoundError(f"'{dosya_adi}' bulunamadı! Lütfen verileri içeren dosyayı ekleyin.")
        with open(dosya_adi, 'r', encoding='utf-8') as f:
            return list(csv.reader(f))
            
    @staticmethod
    def nesnelereDonusturur(satirlar):
        liste = []
        sinif_haritasi = {
            "Futbolcu": Futbolcu,
            "Basketbolcu": Basketbolcu,
            "Voleybolcu": Voleybolcu
        }
        for i, r in enumerate(satirlar):
            if not r or len(r) < 9: continue
            sinif = sinif_haritasi.get(r[0])
            if sinif:
                liste.append(sinif(i, r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]))
        return liste

class MacIstatistik:
    """SRP: Sadece oyun içi kayıt (log) ve istatistik yönetimini yapar."""
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
        self.istatistik.veriEkle(metin)
        self.log_callback(metin)

    def kartlariDagit(self, tum_kartlar):
        brans_sozlugu = {
            "Futbolcu": [k for k in tum_kartlar if isinstance(k, Futbolcu)],
            "Basketbolcu": [k for k in tum_kartlar if isinstance(k, Basketbolcu)],
            "Voleybolcu": [k for k in tum_kartlar if isinstance(k, Voleybolcu)]
        }
        
        for liste in brans_sozlugu.values():
            random.shuffle(liste)
            
        self.kullanici.kartListesi = brans_sozlugu["Futbolcu"][:4] + brans_sozlugu["Basketbolcu"][:4] + brans_sozlugu["Voleybolcu"][:4]
        self.bilgisayar.kartListesi = brans_sozlugu["Futbolcu"][4:8] + brans_sozlugu["Basketbolcu"][4:8] + brans_sozlugu["Voleybolcu"][4:8]
        
        random.shuffle(self.kullanici.kartListesi)
        random.shuffle(self.bilgisayar.kartListesi)

    def oyunAkisiniYonet(self):
        return self.tur_sayisi <= 24

    def kartlariKarsilastir(self, k_kart, b_kart, ozellik, kp, bp):
        if kp > bp: return 1
        if bp > kp: return 2
        
        self.log("- Eşitlik! Yedek özelliklere bakılıyor...")
        for yedek_oz in k_kart.ozellikler.keys():
            if yedek_oz != ozellik:
                if k_kart.ozellikler[yedek_oz] > b_kart.ozellikler[yedek_oz]: return 1
                if b_kart.ozellikler[yedek_oz] > k_kart.ozellikler[yedek_oz]: return 2
                
        self.log("- Eşitlik! Dayanıklılığa bakılıyor...")
        if k_kart.dayaniklilik > b_kart.dayaniklilik: return 1
        if b_kart.dayaniklilik > k_kart.dayaniklilik: return 2
        
        self.log("- Eşitlik! Enerjiye ve Seviyeye bakılıyor...")
        if k_kart.enerji > b_kart.enerji: return 1
        if b_kart.enerji > k_kart.enerji: return 2
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
                puan += 5
                self.log("⭐ Seviye atladıktan sonraki ilk galibiyet! (+5 Puan)")
                k_kart.seviyeAtladiOdulBekliyor = False
            
            self.log(f"<font color='#2ecc71'>Turu Kazandın! (+{puan} Puan)</font>")
            self.kullanici.skor += puan; self.kullanici.kazanilanTurSayisi += 1
            if y_bonus_k > 0: self.kullanici.ozelYetenekleKazanilanTurSayisi += 1
            self.kullanici.moralGuncelle("kazandi", brans_adi); self.bilgisayar.moralGuncelle("kaybetti", brans_adi)
            k_kart.deneyimPuani += 2; k_kart.kazanmaSayisi += 1; b_kart.kaybetmeSayisi += 1
            
        elif kazanan == 2:
            self.log("<font color='#e74c3c'>Turu Kaybettin!</font>")
            self.bilgisayar.skor += (15 if y_bonus_b > 0 else 10); self.bilgisayar.kazanilanTurSayisi += 1
            if y_bonus_b > 0: self.bilgisayar.ozelYetenekleKazanilanTurSayisi += 1
            self.kullanici.moralGuncelle("kaybetti", brans_adi); self.bilgisayar.moralGuncelle("kazandi", brans_adi)
            b_kart.deneyimPuani += 2; b_kart.kazanmaSayisi += 1; k_kart.kaybetmeSayisi += 1
            
        else:
            self.log("<font color='#f39c12'>Tam Beraberlik! (Puan yok)</font>")
            self.kullanici.moralGuncelle("berabere", brans_adi); self.bilgisayar.moralGuncelle("berabere", brans_adi)
            k_kart.deneyimPuani += 1; b_kart.deneyimPuani += 1

        k_kart.enerjiGuncelle(k_enerji_kayip)
        b_kart.enerjiGuncelle(b_enerji_kayip)

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
                f.write("HYBRID LEAGUE - MAÇ İSTATİSTİK RAPORU\n")
                f.write("="*45 + "\n")
                f.write(f"Senin Skorun: {self.kullanici.skor} | Bilgisayar Skoru: {self.bilgisayar.skor}\n")
                f.write("="*45 + "\n\n")
                f.write(self.istatistik.raporOlustur())
        except Exception as e:
            print("Rapor kaydedilemedi:", e)

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

        kazanan = self.kartlariKarsilastir(k_kart, b_kart, ozellik, kp, bp)
        self.puanlariGuncelle(kazanan, k_kart, b_kart, y_bonus_k, y_bonus_b, brans_adi)
        
        self.tur_sayisi += 1
        return not self.oyunAkisiniYonet()

# ==============================================================================
# --- BİREYSEL KART VE DİNAMİK YERLEŞİM (Custom Widget) ---
# ==============================================================================

KART_SABLONLARI = {
    "Futbolcu": {
        "ebat": (365, 490),
        "bg_yol": "assets/futbol_bg.png",
        "stat_kisaltmalar": ["PNLT", "STMN", "KKK"],
        "layout": {
            "name": (20, 240, 325, 30, 15, "white", Qt.AlignCenter),
            "seviye": (20, 20, 60, 60, 24, "gold", Qt.AlignCenter),
            "enerji": (20, 345, 325, 30, 13, "white", Qt.AlignCenter),
            "stat1": (40, 295, 80, 30, 11, "white", Qt.AlignCenter),  
            "stat2": (140, 295, 80, 30, 11, "white", Qt.AlignCenter), 
            "stat3": (240, 295, 80, 30, 11, "white", Qt.AlignCenter), 
            "xp": (20, 375, 325, 20, 10, "lightgray", Qt.AlignCenter)
        }
    },
    "Basketbolcu": {
        "ebat": (284, 473),
        "bg_yol": "assets/basket_bg.png",
        "stat_kisaltmalar": ["THRP", "TWP", "FS"],
        "layout": {
            "name": (10, 245, 264, 30, 13, "white", Qt.AlignCenter),
            "seviye": (10, 10, 50, 50, 20, "cyan", Qt.AlignCenter),
            "enerji": (10, 340, 264, 30, 11, "white", Qt.AlignCenter), 
            "stat1": (25, 295, 70, 30, 9, "white", Qt.AlignCenter),
            "stat2": (105, 295, 70, 30, 9, "white", Qt.AlignCenter),
            "stat3": (185, 295, 70, 30, 9, "white", Qt.AlignCenter),
            "xp": (10, 370, 264, 20, 9, "lightgray", Qt.AlignCenter)
        }
    },
    "Voleybolcu": {
        "ebat": (370, 490),
        "bg_yol": "assets/volley_bg.png",
        "stat_kisaltmalar": ["SRVS", "BLOK", "SMAÇ"],
        "layout": {
            "name": (20, 275, 330, 30, 15, "white", Qt.AlignCenter),
            "seviye": (20, 20, 60, 60, 24, "red", Qt.AlignCenter),
            "enerji": (20, 365, 330, 30, 13, "white", Qt.AlignCenter),
            "stat1": (45, 315, 80, 30, 11, "white", Qt.AlignCenter), 
            "stat2": (145, 315, 80, 30, 11, "white", Qt.AlignCenter),
            "stat3": (245, 315, 80, 30, 11, "white", Qt.AlignCenter),
            "xp": (20, 395, 330, 20, 10, "lightgray", Qt.AlignCenter)
        }
    }
}

ISTISNA_SABLONLAR = {
    "Zehra_Gunes": {"name": (50, 275, 290, 30, 12, "white", Qt.AlignCenter)},
    "Gabi_Guimaraes": {"name": (50, 275, 290, 30, 12, "white", Qt.AlignCenter)},
    "Dilay_Ozdemir": {} 
}

class CardWidget(QWidget):
    def __init__(self, sporcu):
        super().__init__()
        self.sporcu = sporcu
        self.sinif_adi = type(sporcu).__name__
        self.sablon = KART_SABLONLARI.get(self.sinif_adi, KART_SABLONLARI["Futbolcu"])
        
        temiz_isim = Araclar.dosya_ismi_temizle(sporcu.sporcuAdi)
        genislik, yukseklik = self.sablon["ebat"]
        
        resim_yolu = f"assets/{temiz_isim}.png"
        if not os.path.exists(resim_yolu):
            resim_yolu = f"assets/{sporcu.sporcuAdi}.png"
            if not os.path.exists(resim_yolu):
                resim_yolu = self.sablon["bg_yol"]
                
        self.bg_pixmap = ResimOnbellek.getir(resim_yolu, genislik, yukseklik)
        if self.bg_pixmap is None:
            self.bg_pixmap = QPixmap(genislik, yukseklik)
            self.bg_pixmap.fill(QColor("darkgray"))
            
        self.setFixedSize(genislik, yukseklik)

        if sporcu.ozelYetenek:
            kullanim = " (KULLANILDI)" if sporcu.ozelYetenek.tek_kullanimlik and sporcu.ozelYetenek.kullanildi else ""
            self.setToolTip(f"<span style='font-size:12pt; font-weight:bold;'>🛡️ {sporcu.ozelYetenek.ad}: {sporcu.ozelYetenek.aciklama}{kullanim}</span>")
            self.setCursor(Qt.PointingHandCursor)

    def _koordinatlari_getir(self):
        temel_layout = self.sablon["layout"].copy()
        if self.sporcu.sporcuAdi in ISTISNA_SABLONLAR:
            temel_layout.update(ISTISNA_SABLONLAR[self.sporcu.sporcuAdi])
        return temel_layout

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.drawPixmap(0, 0, self.bg_pixmap)
        
        s = self.sporcu
        durum = " (DIŞI)" if s.enerji <= 0 else (" (KRİTİK)" if s.enerji < 20 else "")
        kisaltmalar = self.sablon["stat_kisaltmalar"]
        
        veri_haritasi = {
            "name": s.sporcuAdi.replace("_", " "), 
            "seviye": f"Lv{s.seviye}",
            "enerji": f"⚡ {s.enerji}{durum} | 🛡️ {s.ozelYetenek.ad if s.ozelYetenek else 'Yok'}",
            "stat1": f"{list(s.ozellikler.values())[0]} {kisaltmalar[0]}",
            "stat2": f"{list(s.ozellikler.values())[1]} {kisaltmalar[1]}",
            "stat3": f"{list(s.ozellikler.values())[2]} {kisaltmalar[2]}",
            "xp": f"XP: {s.deneyimPuani} | Oyn: {s.kullanimSayisi} | Kaz: {s.kazanmaSayisi} | Kay: {s.kaybetmeSayisi}"
        }

        for key, (x, y, w, h, fs, renk, hizalama) in self._koordinatlari_getir().items():
            painter.setFont(QFont("Arial", fs, QFont.Bold))
            painter.setPen(QColor(renk))
            painter.drawText(QRect(x, y, w, h), hizalama, veri_haritasi[key])

        if s.seviyeAtladiOdulBekliyor:
            painter.setFont(QFont("Arial", 40))
            painter.setPen(QColor("gold"))
            painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignRight, "⭐")
            
        painter.end()


# ==============================================================================
# --- OYUN EKRANI (Game Widget) ---
# ==============================================================================
class OyunEkraniGUI(QWidget):
    def __init__(self, ana_pencere):
        super().__init__()
        self.ana_pencere = ana_pencere
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("oyunEkrani")
        
        zorluk = self.ana_pencere.ayarlar["zorluk"]
        self.pc_kartlari_gorunsun = self.ana_pencere.ayarlar["pc_kart_goster"]
        self.manuel_secim_aktif = self.ana_pencere.ayarlar["manuel_secim"]
        
        self.setStyleSheet("""
            #oyunEkrani { background-color: #242d35; }
            QWidget { background-color: #242d35; color: #d2dae2; }
            QStackedWidget { background-color: #242d35; border: none; }
            QLabel { background-color: transparent; color: #f5f6fa; }
            QPushButton { background-color: #0fb9b1; color: white; border-radius: 5px; padding: 10px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #2bcbba; }
            QPushButton:disabled { background-color: #4b6584; color: #a4b0be; }
            QTextEdit { background-color: #2f3640; color: #f5f6fa; border: 1px solid #718093; border-radius: 5px; font-family: Consolas; font-size: 14px; }
            QInputDialog { background-color: #242d35; color: white; }
        """)
        
        try:
            tum_kartlar = VeriOkuyucu.nesnelereDonusturur(VeriOkuyucu.dosyadanKartlariOkur('sporcular.csv'))
        except Exception as e:
            QMessageBox.critical(self, "Kritik Hata", str(e)); sys.exit()
            
        self.yonetici = OyunYonetici(Kullanici(1), Bilgisayar(2), OrtaStrateji(), self.log_ekrana_yaz, zorluk)
        self.yonetici.kartlariDagit(tum_kartlar)
        
        self.init_ui()
        self.arayuz_guncelle()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        top_bar_layout = QHBoxLayout()
        self.btn_ana_menu = QPushButton("◀ Ana Menüye Dön")
        self.btn_ana_menu.setStyleSheet("background-color: #e1b12c; color: #2f3640;")
        self.btn_ana_menu.clicked.connect(self.ana_menuye_don)
        
        self.lbl_skor = QLabel("🏆 SKOR: Sen 0 - 0 PC")
        self.lbl_moral = QLabel("🔥 TAKIM MORALİ: Sen 60 - 60 PC")
        self.lbl_tur = QLabel("📅 TUR: 1 (Branş: Futbolcu)")
        
        for lbl in [self.lbl_skor, self.lbl_moral, self.lbl_tur]:
            lbl.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #2f3640; padding: 8px; border-radius: 5px;")
            
        top_bar_layout.addWidget(self.btn_ana_menu); top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.lbl_skor); top_bar_layout.addWidget(self.lbl_moral); top_bar_layout.addWidget(self.lbl_tur)
        
        cards_layout = QHBoxLayout()
        
        kul_layout = QVBoxLayout()
        self.lbl_kul_durum = QLabel("<b>Senin Kartın (0/0)</b>")
        self.lbl_kul_durum.setAlignment(Qt.AlignCenter)
        self.lbl_kul_durum.setStyleSheet("font-size: 18px; color: #4cd137;")
        
        self.kullanici_stacked = QStackedWidget()
        
        nav_k_layout = QHBoxLayout()
        self.btn_prev_k = QPushButton("◀ Önceki Kart")
        self.btn_next_k = QPushButton("Sonraki Kart ▶")
        self.btn_prev_k.clicked.connect(self.k_onceki)
        self.btn_next_k.clicked.connect(self.k_sonraki)
        nav_k_layout.addWidget(self.btn_prev_k); nav_k_layout.addWidget(self.btn_next_k)
        
        kul_layout.addWidget(self.lbl_kul_durum); kul_layout.addWidget(self.kullanici_stacked, alignment=Qt.AlignCenter); kul_layout.addLayout(nav_k_layout)
        
        pc_layout = QVBoxLayout()
        self.lbl_pc_durum = QLabel("<b>Bilgisayarın Kartı (0/0)</b>")
        self.lbl_pc_durum.setAlignment(Qt.AlignCenter)
        self.lbl_pc_durum.setStyleSheet("font-size: 18px; color: #e84118;")
        
        self.pc_stacked = QStackedWidget()
        
        nav_p_layout = QHBoxLayout()
        self.btn_prev_p = QPushButton("◀ Önceki Kart")
        self.btn_next_p = QPushButton("Sonraki Kart ▶")
        self.btn_prev_p.clicked.connect(self.p_onceki)
        self.btn_next_p.clicked.connect(self.p_sonraki)
        nav_p_layout.addWidget(self.btn_prev_p); nav_p_layout.addWidget(self.btn_next_p)
        
        pc_layout.addWidget(self.lbl_pc_durum); pc_layout.addWidget(self.pc_stacked, alignment=Qt.AlignCenter); pc_layout.addLayout(nav_p_layout)
        
        if not self.pc_kartlari_gorunsun:
            self.lbl_pc_durum.setText("<b>Bilgisayarın Kartı (Gizli)</b>")
            self.lbl_pc_durum.setStyleSheet("font-size: 18px; color: #7f8c8d;")
            self.pc_stacked.hide(); self.btn_prev_p.hide(); self.btn_next_p.hide()
        
        cards_layout.addLayout(kul_layout); cards_layout.addLayout(pc_layout)
        
        bottom_layout = QVBoxLayout()
        self.log_ekrani = QTextEdit()
        self.log_ekrani.setReadOnly(True)
        
        self.btn_oyna = QPushButton("EKRANDAKİ KARTI OYNA")
        self.btn_oyna.setStyleSheet("background-color: #44bd32; color: white; font-size: 18px; padding: 15px;")
        self.btn_oyna.setEnabled(False)
        self.btn_oyna.clicked.connect(self.tur_baslat_ui)

        bottom_layout.addWidget(QLabel("<b>Maç Raporu ve İstatistikler:</b>"))
        bottom_layout.addWidget(self.log_ekrani); bottom_layout.addWidget(self.btn_oyna)

        main_layout.addLayout(top_bar_layout); main_layout.addLayout(cards_layout); main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)

    def ana_menuye_don(self):
        if QMessageBox.question(self, "Onay", "Oyun ilerlemesi silinecek. Emin misiniz?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.ana_pencere.show_menu()

    def log_ekrana_yaz(self, metin):
        self.log_ekrani.append(metin)

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
        count = self.kullanici_stacked.count()
        idx = self.kullanici_stacked.currentIndex()
        if count > 0:
            self.lbl_kul_durum.setText(f"<b>Senin Kartın ({idx+1}/{count})</b>")
            self.btn_prev_k.setEnabled(idx > 0); self.btn_next_k.setEnabled(idx < count - 1)
            
            k_kart = self.yonetici.kullanici.kartSec(idx, self.yonetici.brans_sirasi[(self.yonetici.tur_sayisi - 1) % 3])
            
            if k_kart and k_kart.enerji > 0:
                self.btn_oyna.setEnabled(True); self.btn_oyna.setText("EKRANDAKİ KARTI OYNA")
                self.btn_oyna.setStyleSheet("background-color: #44bd32; color: white; font-size: 18px; padding: 15px;")
            else:
                self.btn_oyna.setEnabled(False); self.btn_oyna.setText("BU KART OYNAYAMAZ (ENERJİ YETERSİZ)")
                self.btn_oyna.setStyleSheet("background-color: #7f8c8d; color: white; font-size: 18px; padding: 15px;")
        else:
            self.lbl_kul_durum.setText("<b>Senin Kartın (0/0)</b>"); self.btn_oyna.setEnabled(False)

    def p_durum_guncelle(self):
        if not self.pc_kartlari_gorunsun: return
        count = self.pc_stacked.count()
        idx = self.pc_stacked.currentIndex()
        if count > 0:
            self.lbl_pc_durum.setText(f"<b>Bilgisayarın Kartı ({idx+1}/{count})</b>")
            self.btn_prev_p.setEnabled(idx > 0); self.btn_next_p.setEnabled(idx < count - 1)
        else:
            self.lbl_pc_durum.setText("<b>Bilgisayarın Kartı (0/0)</b>")

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
        self.lbl_moral.setText(f"🔥 TAKIM MORALİ: Sen {self.yonetici.kullanici.moral} - {self.yonetici.bilgisayar.moral} PC")
        self.lbl_tur.setText(f"📅 TUR: {self.yonetici.tur_sayisi}/24 (Branş: {guncel_brans.__name__})")

    def tur_baslat_ui(self):
        idx = self.kullanici_stacked.currentIndex()
        if idx == -1: return
        
        manuel_ozellik = None
        if self.manuel_secim_aktif:
            guncel_brans = self.yonetici.brans_sirasi[(self.yonetici.tur_sayisi - 1) % 3]
            k_kart = self.yonetici.kullanici.kartSec(idx, guncel_brans)
            secilen, ok = QInputDialog.getItem(self, "Özellik Seçimi", f"{k_kart.sporcuAdi.replace('_', ' ')} için özellik seçin:", list(k_kart.ozellikler.keys()), 0, False)
            if not ok or not secilen: return
            manuel_ozellik = secilen
            
        oyun_bitti_mi = self.yonetici.turBaslat(idx, manuel_ozellik)
        self.btn_oyna.setEnabled(False)
        self.arayuz_guncelle()
        
        if oyun_bitti_mi:
            self.log_ekrana_yaz("\n<b>--- LİG SONA ERDİ ---</b>")
            self.yonetici.raporuDosyayaKaydet() 
            kazanan, sebep = self.yonetici.kazananiBelirle()
            QMessageBox.information(self, "Lig Bitti", f"🏆 ŞAMPİYON: {kazanan}\n\nSebep: {sebep}\n\nSenin Skorun: {self.yonetici.kullanici.skor}\nPC Skoru: {self.yonetici.bilgisayar.skor}\n\n(Not: Maç istatistikleri kaydedildi!)")
            self.ana_pencere.show_menu()


# ==============================================================================
# --- AYARLAR MENÜSÜ ---
# ==============================================================================
class AyarlarWidget(QWidget):
    def __init__(self, ana_pencere):
        super().__init__()
        self.ana_pencere = ana_pencere
        
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("ayarlarEkrani")
        
        self.setStyleSheet("""
            #ayarlarEkrani { background-color: #192a56; }
            QWidget { background-color: #192a56; }
            QLabel { color: #f5f6fa; font-size: 18px; font-weight: bold; background-color: transparent; }
            QPushButton { background-color: #44bd32; color: white; font-size: 18px; font-weight: bold; border-radius: 8px; padding: 12px; border: none; }
            QPushButton:hover { background-color: #4cd137; }
            QComboBox { font-size: 16px; color: #192a56; padding: 5px; background-color: #f5f6fa; }
            QCheckBox { font-size: 16px; color: #f5f6fa; padding: 5px; background-color: transparent; }
            QCheckBox::indicator { width: 20px; height: 20px; }
        """)
        
        layout = QVBoxLayout()
        
        layout.addStretch() # DİKKAT: ÜSTTEN BOŞLUK (TÜM İÇERİĞİ ORTAYA İTER)
        
        baslik = QLabel("⚙️ AYARLAR")
        baslik.setAlignment(Qt.AlignCenter)
        baslik.setStyleSheet("font-size: 40px; color: #fbc531; background-color: transparent;")
        
        zorluk_layout = QHBoxLayout()
        self.cmb_zorluk = QComboBox()
        self.cmb_zorluk.addItems(["Kolay", "Orta", "Zor"])
        zorluk_layout.addStretch(); zorluk_layout.addWidget(QLabel("Oyun Zorluğu:")); zorluk_layout.addWidget(self.cmb_zorluk); zorluk_layout.addStretch()
        
        pc_kart_layout = QHBoxLayout()
        self.chk_pc_kart = QCheckBox("Rakip (PC) Kartlarını Açık Göster")
        pc_kart_layout.addStretch(); pc_kart_layout.addWidget(self.chk_pc_kart); pc_kart_layout.addStretch()
        
        manuel_layout = QHBoxLayout()
        self.chk_manuel = QCheckBox("Manuel Özellik Seçimi (Karşılaştırılacak özelliği ben seçerim)")
        manuel_layout.addStretch(); manuel_layout.addWidget(self.chk_manuel); manuel_layout.addStretch()
        
        btn_kaydet = QPushButton("Kaydet ve Ana Menüye Dön")
        btn_kaydet.setFixedWidth(350)
        btn_kaydet.clicked.connect(self.ayarlari_kaydet)
        
        layout.addWidget(baslik, alignment=Qt.AlignCenter); layout.addSpacing(30)
        layout.addLayout(zorluk_layout); layout.addSpacing(20)
        layout.addLayout(pc_kart_layout); layout.addSpacing(20)
        layout.addLayout(manuel_layout); layout.addSpacing(40)
        layout.addWidget(btn_kaydet, alignment=Qt.AlignCenter)
        
        layout.addStretch() # DİKKAT: ALTTAN BOŞLUK (TÜM İÇERİĞİ ORTAYA İTER)
        
        self.setLayout(layout)

    def ayarlari_yukle(self):
        self.cmb_zorluk.setCurrentText(self.ana_pencere.ayarlar["zorluk"])
        self.chk_pc_kart.setChecked(self.ana_pencere.ayarlar["pc_kart_goster"])
        self.chk_manuel.setChecked(self.ana_pencere.ayarlar["manuel_secim"])

    def ayarlari_kaydet(self):
        self.ana_pencere.ayarlar["zorluk"] = self.cmb_zorluk.currentText()
        self.ana_pencere.ayarlar["pc_kart_goster"] = self.chk_pc_kart.isChecked()
        self.ana_pencere.ayarlar["manuel_secim"] = self.chk_manuel.isChecked()
        self.ana_pencere.show_menu()


# ==============================================================================
# --- ANA MENÜ (Giriş Ekranı) ---
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
                border-image: url({bg_path}); 
                background-color: #192a56; 
            }}
            QLabel {{ 
                color: #f5f6fa; 
                background-color: rgba(0, 0, 0, 150); 
                border-radius: 10px;
                padding: 10px;
            }}
            QPushButton {{ 
                background-color: rgba(225, 177, 44, 230); 
                color: #192a56; 
                font-size: 20px; 
                font-weight: bold; 
                border-radius: 10px; 
                padding: 15px; 
                border: 2px solid #fbc531;
            }}
            QPushButton:hover {{ background-color: rgba(251, 197, 49, 255); }}
        """)
        
        layout = QVBoxLayout()
        
        layout.addStretch() # DİKKAT: ÜSTTEN BOŞLUK (TÜM İÇERİĞİ ORTAYA İTER)
        
        baslik = QLabel("🏆 HYBRID LEAGUE 🏆")
        baslik.setAlignment(Qt.AlignCenter)
        baslik.setStyleSheet("font-size: 50px; font-weight: bold; color: #fbc531; background-color: rgba(0, 0, 0, 200);")
        
        alt_baslik = QLabel("Gelişmiş Kart Simülasyonu - v1.0")
        alt_baslik.setAlignment(Qt.AlignCenter)
        alt_baslik.setStyleSheet("font-size: 20px;")
        
        btn_basla = QPushButton("▶ OYUNA BAŞLA")
        btn_basla.setFixedWidth(400)
        btn_basla.clicked.connect(self.ana_pencere.start_game)
        
        btn_ayarlar = QPushButton("⚙️ Ayarlar")
        btn_ayarlar.setFixedWidth(400)
        btn_ayarlar.clicked.connect(self.ana_pencere.show_ayarlar)
        
        btn_cikis = QPushButton("❌ Çıkış")
        btn_cikis.setFixedWidth(400)
        btn_cikis.setStyleSheet("background-color: rgba(194, 54, 22, 230); color: white; border: 2px solid #e84118;")
        btn_cikis.clicked.connect(sys.exit)
        
        layout.addWidget(baslik, alignment=Qt.AlignCenter); layout.addSpacing(10)
        layout.addWidget(alt_baslik, alignment=Qt.AlignCenter); layout.addSpacing(40)
        layout.addWidget(btn_basla, alignment=Qt.AlignCenter); layout.addSpacing(15)
        layout.addWidget(btn_ayarlar, alignment=Qt.AlignCenter); layout.addSpacing(15)
        layout.addWidget(btn_cikis, alignment=Qt.AlignCenter)
        
        layout.addStretch() # DİKKAT: ALTTAN BOŞLUK (TÜM İÇERİĞİ ORTAYA İTER)
        
        self.setLayout(layout)

# ==============================================================================
# --- APP YÖNETİCİSİ (Pencereler Arası Geçiş ve Global Ayarlar) ---
# ==============================================================================
class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hybrid League")
        self.setGeometry(50, 50, 1400, 900)
        
        self.ayarlar = {"zorluk": "Orta", "pc_kart_goster": False, "manuel_secim": False}
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.menu_widget = AnaMenuWidget(self)
        self.ayarlar_widget = AyarlarWidget(self)
        
        self.stacked_widget.addWidget(self.menu_widget)
        self.stacked_widget.addWidget(self.ayarlar_widget)
        
        self.show_menu()
        
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
    pencere = AppWindow()
    pencere.show()
    sys.exit(app.exec_())