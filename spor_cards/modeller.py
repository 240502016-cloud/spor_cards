from abc import ABC, abstractmethod

class OzelYetenek(ABC):
    def __init__(self, ad, aciklama, tek_kullanimlik=False):
        self.ad = ad
        self.aciklama = aciklama
        self.tek_kullanimlik = tek_kullanimlik
        self.kullanildi = False
    
    @abstractmethod
    def bonus_hesapla(self, kart, rakip_kart, tur_sayisi, guncel_puan): pass

class ClutchPlayer(OzelYetenek):
    def __init__(self): super().__init__("Clutch Player", "Son 3 turda puanlara +10 bonus verir (Pasif).")
    def bonus_hesapla(self, kart, rakip_kart, tur_sayisi, guncel_puan): return 10 if tur_sayisi >= 22 else 0

class Captain(OzelYetenek):
    def __init__(self): super().__init__("Captain", "Takım kartlarına anında +5 moral etkisi sağlar (Pasif).")
    def bonus_hesapla(self, kart, rakip_kart, tur_sayisi, guncel_puan): return 0

class Legend(OzelYetenek):
    def __init__(self): super().__init__("Legend", "Maçta YALNIZCA BİR KEZ özelliği iki kat etkiler (Aktif).", tek_kullanimlik=True)
    def bonus_hesapla(self, kart, rakip_kart, tur_sayisi, guncel_puan):
        if not self.kullanildi:
            self.kullanildi = True
            return guncel_puan 
        return 0

class Defender(OzelYetenek):
    def __init__(self): super().__init__("Defender", "Rakibin o tur kazandığı bonusu yarıya düşürür (Pasif).")
    def bonus_hesapla(self, kart, rakip_kart, tur_sayisi, guncel_puan): return 0

class Veteran(OzelYetenek):
    def __init__(self): super().__init__("Veteran", "Maç sonu yaşanacak enerji kaybını %50 azaltır (Pasif).")
    def bonus_hesapla(self, kart, rakip_kart, tur_sayisi, guncel_puan): return 0

class Finisher(OzelYetenek):
    def __init__(self): super().__init__("Finisher", "Enerjisi kritik seviyedeyken +8 ek bonus alır (Pasif).")
    def bonus_hesapla(self, kart, rakip_kart, tur_sayisi, guncel_puan): return 8 if kart.enerji < 40 else 0

def yetenek_olustur(yetenek_adi):
    yetenekler = {"Clutch Player": ClutchPlayer(), "Captain": Captain(), "Legend": Legend(),
                  "Defender": Defender(), "Veteran": Veteran(), "Finisher": Finisher()}
    return yetenekler.get(yetenek_adi, None)

class Sporcu(ABC):
    def __init__(self, id, ad, takim, dayaniklilik, enerji, ozel_yetenek_adi):
        self.sporcuID = id
        self.sporcuAdi = ad
        self.sporcuTakim = takim
        self.dayaniklilik = int(dayaniklilik)
        self.enerji = int(enerji)
        self.maxEnerji = 100
        self.seviye = 1
        self.deneyimPuani = 0
        self.ozelYetenek = yetenek_olustur(ozel_yetenek_adi)
        
        self.kartKullanildiMi = False # 17. Madde İsteri
        self.kullanimSayisi = 0
        self.kazanmaSayisi = 0
        self.kaybetmeSayisi = 0
        self.seviyeAtladiOdulBekliyor = False

    def sporcuPuaniGoster(self):
        return self.ozellikler

    def kartBilgisiYazdir(self): # 17. Madde İsteri
        yetenek_adi = self.ozelYetenek.ad if self.ozelYetenek else "Yok"
        return f"ID: {self.sporcuID} | İsim: {self.sporcuAdi} | Seviye: {self.seviye} | Enerji: {self.enerji} | Yetenek: {yetenek_adi}"

    @abstractmethod
    def performansHesapla(self, ozellik_adi, takim_morali): pass

    def ozelYetenekUygula(self, rakip_kart, tur_sayisi, guncel_puan): # 17. Madde İsteri
        if self.ozelYetenek:
            return self.ozelYetenek.bonus_hesapla(self, rakip_kart, tur_sayisi, guncel_puan) * getattr(self, 'ozelYetenekKatsayisi', 1)
        return 0

    def enerjiGuncelle(self, miktar, veteran_mi=False):
        if veteran_mi and miktar < 0: miktar = miktar / 2
        self.enerji = int(max(0, min(self.maxEnerji, self.enerji + miktar)))

    def seviyeAtlaKontrol(self):
        if self.seviye >= 3: return False
        eski_seviye = self.seviye
        if self.seviye == 1 and (self.kazanmaSayisi >= 2 or self.deneyimPuani >= 4): self.seviye = 2
        if self.seviye == 2 and (self.kazanmaSayisi >= 4 or self.deneyimPuani >= 8): self.seviye = 3
        
        if self.seviye > eski_seviye:
            self.maxEnerji += 10
            self.dayaniklilik += 5
            for key in self.ozellikler: self.ozellikler[key] += 5
            self.seviyeAtladiOdulBekliyor = True
            return True
        return False

class Futbolcu(Sporcu):
    def __init__(self, id, ad, takim, penalti, serbest_vurus, kaleci_kk, dayaniklilik, enerji, yetenek):
        super().__init__(id, ad, takim, dayaniklilik, enerji, yetenek)
        self.brans = "Futbolcu"
        self.penalti, self.serbestVurus, self.kaleciKarsiKarsiya = int(penalti), int(serbest_vurus), int(kaleci_kk)
        self.ozelYetenekKatsayisi = 1
        self.ozellikler = {"Penaltı": self.penalti, "SerbestVurus": self.serbestVurus, "KaleciKarsiKarsiya": self.kaleciKarsiKarsiya}

    def performansHesapla(self, ozellik_adi, takim_morali):
        temel = self.ozellikler.get(ozellik_adi, 0)
        ceza = (temel * 0.1) if 40 <= self.enerji <= 70 else ((temel * 0.2) if 0 < self.enerji < 40 else 0)
        moral_bonusu = 10 if takim_morali >= 90 else (5 if takim_morali >= 70 else (-5 if takim_morali < 50 else 0))
        return temel + moral_bonusu + ((self.seviye - 1) * 5) - ceza

class Basketbolcu(Sporcu):
    def __init__(self, id, ad, takim, ucluk, ikilik, serbest_atis, dayaniklilik, enerji, yetenek):
        super().__init__(id, ad, takim, dayaniklilik, enerji, yetenek)
        self.brans = "Basketbolcu"
        self.ucluk, self.ikilik, self.serbestAtis = int(ucluk), int(ikilik), int(serbest_atis)
        self.ozelYetenekKatsayisi = 1
        self.ozellikler = {"Ucluk": self.ucluk, "Ikilik": self.ikilik, "SerbestAtis": self.serbestAtis}

    def performansHesapla(self, ozellik_adi, takim_morali):
        temel = self.ozellikler.get(ozellik_adi, 0)
        ceza = (temel * 0.1) if 40 <= self.enerji <= 70 else ((temel * 0.2) if 0 < self.enerji < 40 else 0)
        moral_bonusu = 10 if takim_morali >= 90 else (5 if takim_morali >= 70 else (-5 if takim_morali < 50 else 0))
        return temel + moral_bonusu + ((self.seviye - 1) * 5) - ceza

class Voleybolcu(Sporcu):
    def __init__(self, id, ad, takim, servis, blok, smac, dayaniklilik, enerji, yetenek):
        super().__init__(id, ad, takim, dayaniklilik, enerji, yetenek)
        self.brans = "Voleybolcu"
        self.servis, self.blok, self.smac = int(servis), int(blok), int(smac)
        self.ozelYetenekKatsayisi = 1
        self.ozellikler = {"Servis": self.servis, "Blok": self.blok, "Smac": self.smac}

    def performansHesapla(self, ozellik_adi, takim_morali):
        temel = self.ozellikler.get(ozellik_adi, 0)
        ceza = (temel * 0.1) if 40 <= self.enerji <= 70 else ((temel * 0.2) if 0 < self.enerji < 40 else 0)
        moral_bonusu = 10 if takim_morali >= 90 else (5 if takim_morali >= 70 else (-5 if takim_morali < 50 else 0))
        return temel + moral_bonusu + ((self.seviye - 1) * 5) - ceza
