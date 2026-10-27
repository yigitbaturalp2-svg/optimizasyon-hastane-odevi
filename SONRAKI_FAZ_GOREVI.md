# Ankara SağlıkNet — Sonraki Faz Görevi (Faz 002)

> **Durum:** Faz 001 başarıyla tamamlandı, doğrulandı ve GitHub'a push edildi.
> **Sonraki Adım:** Teknik Görev 002 — 112 Ambulans İstasyonları ve Acil Müdahale Optimizasyonu
> **Ayrıntılı Teknik Şartname:** [docs/TEKNIK_GOREV_002.md](docs/TEKNIK_GOREV_002.md)

---

# ANKARA SAĞLIKNET — TEKNİK GÖREV 002

## 112 AMBULANS İSTASYONLARI VE ACİL MÜDAHALE OPTİMİZASYONU



**Teknik Yönetici:** ChatGPT  

**Mühendis:** Antigravity  

**Karar:** Faz 001 temel mimarisi kabul edildi. Faz 002 geliştirmesine koşullu izin verildi.



Artık aynı hastane optimizasyonunu baştan yazmıyoruz. Mevcut modüler mimariyi koruyarak ambulans istasyonu yerleşim modelini ekleyeceğiz.



## AŞAMA A — Önce kalan dört hatayı kapat



1. `app.py` içinde optimizasyon başarısızlığı kontrolünü sonuç metadata'sını okumadan önce yap. Hata halinde Streamlit çökmemeli; açıklayıcı mesaj görünmeli.



2. OSRM için binlerce tekil HTTP isteği göndermeyi bırak. Uygun boyutlu OSRM Table API sorguları, önbellek ve yapılandırılabilir zaman aşımı kullan. Kamu sunucusuna ağır toplu yük bindirme. Servis başarısızlıklarında kullanıcıya açık bilgi ver.



3. `0.35 başvuru/kişi/yıl` değerini doğrulanmış resmî norm olarak gösterme. Kaynak kanıtı yoksa simülasyon parametresi olarak işaretle. Kanıtsız doğrulama tarihlerine gerçek teyit tarihi muamelesi yapma. 32 talep bölgesinin yaklaşık bölgelere dağıtılmış model verisi olduğunu açıkla.



4. `BUDGET_LIMIT` ve `COMBINED` modlarında eksik, negatif veya sonsuz bütçe değerlerini açıkça reddet. Sıfır talep halinde `EXACT_COUNT` kuralını ihlal eden sessiz başarı oluşmamasını sağla.



Testleri çalıştır. Aşama A başarıyla tamamlanmadan Aşama B'ye geçme.



## AŞAMA B — Ambulans istasyonları için bağımsız veri modeli



Hastanelerden ayrı `AmbulanceStation` veri modeli oluştur.



Desteklenecek alanlar:



- İstasyon ID.

- İstasyon adı ve coğrafi konum.

- Mevcut veya aday statüsü.

- Doğrulanmış veya simülasyon veri durumu.

- İstasyondaki ambulans sayısı.

- Aynı anda müsait ambulans sayısı.

- Tahmini kuruluş/işletme maliyeti.

- Kaynak ve veri yılı.



Ankara'daki gerçek 112 istasyonlarının konumlarını güvenilir kaynaktan doğrulayabilirsen ekle.



Doğrulayamadığın istasyonları kesinlikle gerçek 112 istasyonu olarak gösterme. Bu durumda açıkça etiketlenmiş temsili istasyon verisi kullan.



Faz 001'de ayrılan dört aday acil üssünü de değerlendir; ancak bir acil üssünün otomatik olarak resmî 112 istasyonu olduğunu varsayma.



## AŞAMA C — Ambulans istasyonu yer seçimi



Hastane CFLP modelinden ayrı bir **MCLP (Maximum Covering Location Problem)** çözümü geliştir.



Amaç: Belirli tesis sayısı, ambulans sayısı veya yatırım bütçesi altında, hedef müdahale süresi içinde kapsanan tahmini acil çağrı talebini en üst düzeye çıkarmak.



Temel kurallar:



- Talep bölgeleri ve ağırlıkları.

- İstasyon-vaka ulaşım süreleri.

- 10, 15 ve 20 dakika kapsama senaryoları.

- En fazla p yeni istasyon.

- İsteğe bağlı parasal bütçe sınırı.

- İstasyonun yalnızca açılmışsa hizmet verebilmesi.

- Birden fazla istasyonun aynı bölgeyi kapsamasının kapsanan nüfusu iki kez saymaması.



MCLP'nin bir yerleşim/kapsama modeli olduğunu unutma. İstasyon sayısını ya da hedef süre içi coğrafi kapsama oranını gerçek ambulans müsaitlik garantisi gibi gösterme.



## AŞAMA D — Basit acil vaka sevk simülasyonu



İki bağımsız ulaşım bacağı hesapla:



1. Ambulans istasyonu → Vaka konumu.

2. Vaka konumu → Uygun hastane.



Sistem yalnızca müsait ambulansları değerlendirerek uygun bir ambulans seçebilmeli.



Hastane seçimi mevcut hastane optimizasyonundan yararlanmalı, ancak simüle yıllık kapasiteyi anlık boş yatak sayısı gibi kullanmamalı.



Gerçek zamanlı yatak ve ambulans müsaitliği verimiz olmadığından, vaka sevkinde kullanılan anlık müsaitlik değerlerini ayrı senaryo varsayımları olarak modelle.



Şimdilik kullanıcı şu akışı deneyebilsin:



- Haritada bir acil vaka noktası seçer.

- Vaka türü ve simüle önceliği seçer.

- Sistem uygun/müsait istasyonu belirler.

- Ambulansın olay yerine tahmini ulaşım süresi gösterilir.

- Uygun hastane belirlenir.

- Hastaneye tahmini nakil süresi ayrıca gösterilir.

- Araç müsait değilse veya uygun hastane bulunmazsa açık uyarı verir.



Bu akademik bir simülasyondur; gerçek hasta sevki veya klinik triyaj sistemi değildir.



## AŞAMA E — Harita ve kullanıcı deneyimi



Mevcut Streamlit/Folium arayüzünü koru.



Yeni bir **112 Ambulans Ağı** sekmesi oluştur.



Haritada ayrı katmanlar bulunmalı:



- Mevcut hastaneler.

- Aday hastaneler.

- Mevcut veya temsili ambulans istasyonları.

- Aday ambulans istasyonları.

- Talep bölgeleri.

- Seçilen acil vaka.

- İstasyon → Vaka rotası.

- Vaka → Hastane rotası.



Açılan rota çizgisinin gerçek yol geometrisi mi yoksa tahmini bağlantı çizgisi mi olduğunu açıkça göster.



Kullanıcı "Önce / Sonra" karşılaştırmasında ambulans istasyonu yatırımlarının hizmet kapsama oranına etkisini görebilsin.



## AŞAMA F — Testler



Mevcut 23 testi koru.



Ayrıca şu davranışları doğrula:



- Hastane ambulans istasyonu olarak sayılmıyor.

- İstasyon hasta kabul eden hastane gibi davranmıyor.

- Kapanan istasyon ambulans gönderemiyor.

- Müsait ambulansı olmayan istasyon görev alamıyor.

- MCLP aynı talebi iki kez saymıyor.

- İstasyon sayısı ve bütçe sınırları korunuyor.

- Yol ağı erişilemeyen bağlantıları doğru yönetiyor.

- İstasyon → Vaka ve Vaka → Hastane süreleri birbirine karıştırılmıyor.

- Simüle müsaitlik verileri gerçek statü olarak gösterilmiyor.

- Başarısız senaryolar kullanıcı arayüzünü çökertmiyor.



## TESLİMAT



Bu görevde yalnızca Ambulans Ağı'nın ilk çalışan dikey kesitini tamamla. AFAD, Kızılay, itfaiye ve tam afet simülasyonuna henüz başlama.



Şunları teslim et:



1. Düzeltilmiş Faz 001 sorunlarının test kanıtları.

2. Yeni ambulans veri modeli.

3. Çalışan MCLP çözücüsü.

4. Basit vaka-sevk simülatörü.

5. Güncel 112 harita ekran görüntüleri.

6. Yeni ve eski testlerin gerçek çıktısı.

7. Değişen dosyaların özeti.

8. Git commit kimliği.

9. Güncellenmiş `review_bundle.zip`.



Görev tamamlandığında dur ve teknik yönetici incelemesini bekle.



**Temel başarı kriteri:** Kullanıcı Ankara haritasında bir vaka oluşturabilmeli; sistem senaryo verilerine dayanarak müsait ambulansı ve uygun hastaneyi seçip iki ayrı ulaşım süresini doğru gösterebilmeli. 

<ADDITIONAL_METADATA>
The current local time is: 2026-10-28T01:49:55+03:00.
</ADDITIONAL_METADATA>