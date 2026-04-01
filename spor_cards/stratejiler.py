import random
from abc import ABC, abstractmethod

class KartSecmeStratejisi(ABC):
    @abstractmethod
    def kartSec(self, kartlar, oyunDurumu): # 17. Madde İsteri
        pass

class KolayStrateji(KartSecmeStratejisi):
    def kartSec(self, kartlar, oyunDurumu):
        brans_sinifi = oyunDurumu.get("brans")
        uygun = [k for k in kartlar if isinstance(k, brans_sinifi) and k.enerji > 0]
        return random.choice(uygun) if uygun else None

class OrtaStrateji(KartSecmeStratejisi):
    def kartSec(self, kartlar, oyunDurumu):
        brans_sinifi = oyunDurumu.get("brans")
        takim_morali = oyunDurumu.get("moral")
        uygun = [k for k in kartlar if isinstance(k, brans_sinifi) and k.enerji > 0]
        
        if not uygun: return None
        
        en_iyi_kart = None
        en_yuksek_ortalama = -1
        
        for kart in uygun:
            toplam = sum(kart.performansHesapla(oz, takim_morali) for oz in kart.ozellikler.keys())
            ortalama = toplam / len(kart.ozellikler)
            if ortalama > en_yuksek_ortalama:
                en_yuksek_ortalama = ortalama
                en_iyi_kart = kart
                
        return en_iyi_kart