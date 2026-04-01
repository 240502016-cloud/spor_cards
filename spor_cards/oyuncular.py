from abc import ABC, abstractmethod

class Oyuncu(ABC):
    def __init__(self, id, ad):
        self.oyuncuID = id
        self.oyuncuAdi = ad
        self.skor = 0
        self.kartListesi = []
        
        self.moral = 60
        self.galibiyetSerisi = 0
        self.kaybetmeSerisi = 0
        self.sonKaybedilenBrans = None
        
        self.kazanilanTurSayisi = 0
        self.toplamGalibiyetSerisiSayisi = 0 
        self.ozelYetenekleKazanilanTurSayisi = 0
        self.beraberlikSayisi = 0

    @abstractmethod
    def kartSec(self, *args): # 17. Madde İsteri
        pass

    def moralGuncelle(self, sonuc, oynanan_brans):
        if sonuc == "kazandi":
            self.galibiyetSerisi += 1
            self.kaybetmeSerisi = 0
            self.sonKaybedilenBrans = None
            if self.galibiyetSerisi == 2: self.moral += 10
            elif self.galibiyetSerisi >= 3: self.moral += 15
        elif sonuc == "kaybetti":
            self.kaybetmeSerisi += 1
            self.galibiyetSerisi = 0
            if self.kaybetmeSerisi >= 2: self.moral -= 10
            if self.sonKaybedilenBrans == oynanan_brans: self.moral -= 5
            self.sonKaybedilenBrans = oynanan_brans
        elif sonuc == "berabere":
            self.beraberlikSayisi += 1
            
        self.moral = max(0, min(100, self.moral))
        
    def kalanToplamEnerji(self): return sum(k.enerji for k in self.kartListesi)
        
    def enYuksekSeviyeliKartSayisi(self):
        if not self.kartListesi: return 0
        max_lvl = max(k.seviye for k in self.kartListesi)
        return sum(1 for k in self.kartListesi if k.seviye == max_lvl)

class Kullanici(Oyuncu):
    def __init__(self, id, ad="Kullanıcı"):
        super().__init__(id, ad)
        
    def kartSec(self, secilen_kart_idx, guncel_brans):
        uygun_kartlar = [k for k in self.kartListesi if isinstance(k, guncel_brans)]
        return uygun_kartlar[secilen_kart_idx] if uygun_kartlar else None

class Bilgisayar(Oyuncu):
    def __init__(self, id, ad="Bilgisayar Yapay Zeka"):
        super().__init__(id, ad)

    def kartSec(self, strateji, oyun_durumu):
        return strateji.kartSec(self.kartListesi, oyun_durumu)