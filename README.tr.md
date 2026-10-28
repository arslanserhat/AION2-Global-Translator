<p align="center">
  <img src="assets/banner.svg" alt="AION 2 Global Translator — oyun metinlerini seçtiğiniz dile çevirin" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="docs/TRANSLATION.md">Çeviri iş akışı</a> ·
  <a href="docs/LANGUAGES.md">Dil uyumluluğu</a> ·
  <a href="CONTRIBUTING.md">Katkıda bulunun</a>
</p>

# AION 2 Global Translator

Kendi İngilizce oyun dosyalarınızdan **AION 2 için yerel metin çevirisi oluşturan**, orijinal dosyaları yedekleyen ve uyumlu oyun güncellemelerinden sonra yerel paketinizi yeniden hazırlayan ücretsiz, açık kaynaklı Windows uygulaması.

**v0.1.3 — Güncel doğrulanan kaynak: Steam 26262663, 153.297 kayıt.** Önceki 26077854 sürümüne göre 116 anahtar eklendi, 265 İngilizce metin değişti ve 4 anahtar kaldırıldı. Yeni veya değişen 381 kayıt için yerel Türkçe düzeltmeler hazırlandı. Eski çeviri, yalnız **anahtar ve İngilizce metin birlikte aynıysa** taşınır. [v0.1.3 sürüm notları](docs/RELEASE-v0.1.3.md).

Uygulama deneyseldir. Dosya biçiminin doğrulanması, bütün metinlerin anlamının veya bütün ekranların görünümünün doğru olduğunu kanıtlamaz. Dil desteği sağlayıcıya ve oyunun yazı tiplerine bağlıdır; bütün diller ve gelecekteki bütün istemci biçimleri için garanti verilmez.

## Başlangıç

1. [En son yayımın](https://github.com/arslanserhat/AION2-Global-Translator/releases/latest) Windows ZIP'ini indirip çıkarın; `AION2-Global-Translator.exe` uygulamasını açın. ZIP, `repak` aracını ve lisans bildirimlerini içerir; oyun DAT'ı veya tam çevrilmiş tablo içermez.
2. Steam AION 2 klasörünü ve **Hedef dil** seçimini yapın. Bu, oyunun çeviri hedefidir; uygulamanın Türkçe/İngilizce arayüz seçimi ayrıdır.
3. İlk paket için **Çeviri ayarları…** penceresini açın. Tam bir yerel JSON haritası içe aktarın veya İngilizce kaynak ile hedef dilinizi destekleyen LibreTranslate uyumlu sunucunuzu ayarlayın.
4. Hazırlanan çeviriyi inceleyin; AION 2'yi tamamen kapatıp **Çeviriyi uygula** düğmesine basın. Oyunun metin dili **English** olarak kalsın.
5. Oyunu normal şekilde yeniden açın; menüleri, beceri etkilerini, görevleri ve harflerin görünümünü kontrol edin.

Windows oyun klasörüne erişimi engelliyorsa isteğe bağlı `AION2-Global-Translator-Admin.exe` uygulamasını kullanabilirsiniz. Windows yönetici onayını kendiniz verirsiniz; normal uygulama yönetici yetkisi istemez.

**Ayrıntılar…** altında kurulum kontrolü, İngilizce kaynağı ve çeviriyi dışa aktarma, günlük ve hazır paket kurma seçenekleri bulunur. İngilizce hedefi seçmek **Orijinale dön** işlemini sunar.

## Güncellemeden sonra neler otomatik yapılır?

**Çeviriyi uygula**, seçili yerel paketin eski kaynağa ait olduğunu görürse güncel orijinal İngilizce tabloyla karşılaştırıp yeniden oluşturur. Eski DAT'ı yeni sürüme zorla kurmaz.

- **Anahtar ve İngilizce metin aynıysa** önceki çeviri korunur.
- Yeni veya değişen metin yeniden çevrilir. Yalnız sayı değişmesi de buna dahildir; başka anahtarda aynı İngilizce bulunması otomatik taşıma için yeterli değildir.
- Ayarlanmış LibreTranslate uyumlu sunucuya yalnız yeni veya değişen kaynak metinler gönderilir. Önce sunucunun İngilizce–hedef dil çiftini desteklediği denetlenir.
- Kullanılabilir sağlayıcı yoksa özel klasörde `pending.json` inceleme listesi oluşturulur. Gerekli `corrections.json` tamamlanıp yeniden uygulanabilir.
- Bütün çeviri hazır olup kontrollerden geçmeden kurulum yapılmaz. Eksik veya biçimi bozuk metin varsa önceki hazırlanmış paket korunur ve işlem durur.

İlk başarılı kurulumdan sonra **Güncellemelerden sonra otomatik onar** seçeneği varsayılan olarak açılır. Bu özellik **yalnız uygulama çalışırken** işler. Oyun açıksa kapanmasını bekler; ardından güncellemeyi dener. Windows başlangıcına görev veya arka plan hizmeti eklemez. **Orijinale dön** işlemi bu seçeneği kapatır.

Gelecekteki sürümler, güncel orijinal dil/başlangıç arşivlerinin parmak izleri, çözülen kaynak tablo ve yeniden kodlama denetimleriyle değerlendirilir. Yalnız sürüm numarası kabul edilerek uyumluluk verilmez. Şifreleme, kapsayıcı veya dosya biçimi değişirse uygulamanın da güncellenmesi gerekebilir.

İnceleme dosyalarının konumu ve sağlayıcı kurulumu için [artan güncelleme akışını](docs/TRANSLATION.md#incremental-game-updates) okuyabilirsiniz.

## Diller ve metin düzeltmeleri

Her hedef dilin kaynağı İngilizcedir; çeviri başka bir çevrilmiş dil üzerinden üretilmez. Bütün hedeflerde biçim öğeleri, sayılar, makrolar ve HP/MP gibi teknik kısaltmalar korunur.

Türkçede seçilmiş bağlamsal düzeltmeler ve başlık gösterim profili bulunur. On ek dil profili, sınırlı sayıda kısa arayüz etiketi ve oyun terimi sunar. Bu, o dillerde bütün paragrafların, yazı tiplerinin veya oynanışın doğrulandığı anlamına gelmez. [Dil uyumluluğu](docs/LANGUAGES.md).

Bir ifadeyi düzeltmek için hedef dili seçip **Ayrıntılar… → Çeviriyi dışa aktar…** yolunu kullanın. Tam JSON haritasındaki değerleri düzenleyip **Çeviri ayarları… → Çevrimdışı JSON** ile yeniden oluşturun. Düzenlenebilir harita, başlık gösterim dönüşümünden önceki yazımı korur. Oyun güncellemesindeki küçük `pending.json` / `corrections.json` akışı yalnız değişen kayıtları kapsar. [Harita sözleşmesi](docs/TRANSLATION.md#custom-maps).

Çevrimdışı haritada değişmeden kalan dilsel metinler varsa `unchanged-review.json` açıkça incelenip onaylanmalıdır. Yalnız bilerek aynı bırakılan adları veya etiketleri onaylayın; bu işlem tam anlam denetimi değildir.

## Türkçe harfler

Oyunun bazı İngilizce gösterim fontlarında Türkçe harfler eksik. Türkçe uyumluluk seçeneği, belirli ad/başlık alanlarında `Ödüller → Oduller` ve `Keskin Atış → Keskin Atis` gibi okunabilir temel Latin yazımları kullanır; normal gövde metni Türkçe harflerini korur. Seçili profil `â/Â` harflerini de kapsar.

**Başlıkları düzelt (Türkçe)**, doğrulanmış Türkçe pakete mevcut sınırlı düzeltmeyi uygular. Fontları değiştirmez ve bütün arayüz alanlarını onarmaz. Oyunu normal şekilde yeniden açıp ilgili metni kontrol edin. Önceki font bulguları ve inceleme kapsamı [v0.1.1 notlarında](docs/RELEASE-v0.1.1.md) ve [QUALITY.md](docs/QUALITY.md) dosyasında yer alır.

Bu yerel metin yöntemi ekran OCR'ı kullanmaz. Seslendirme, görsellere gömülü yazılar ve canlı oyuncu sohbeti kapsam dışındadır.

## Kaynak koddan çalıştırma

Python **3.12 veya üzerini** kullanın:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m aion2_global_translator
```

`Start-Translator.cmd` girişi de sağlanır. Bağımlılıklar arasında `cryptography`, `blake3` ve `lz4` bulunur. Kaynak kurulumunda Windows [repak 0.2.3](https://github.com/trumank/repak/releases/tag/v0.2.3) aracını `tools/repak.exe` yoluna koyun veya `REPAK_PATH` ayarlayın. Windows ZIP'i bu aracı içerir.

Uygulama ücretsizdir; seçtiğiniz sağlayıcının kendi ücretleri ve sınırları olabilir. Gerekli dil modelleriyle [LibreTranslate'i kendiniz barındırabilirsiniz](https://docs.libretranslate.com/guides/installation/). Sağlayıcı API anahtarı kaydedilmez; otomatik kontroller anahtarı uygulama sürecinin `AION2_TRANSLATION_API_KEY` ortam değişkeninden alabilir.

## Yedekler ve yerel veriler

Kurulumdan veya geri yüklemeden önce oyunu kapatın. Yedek, doğrulandığı kaynak sürüme aittir; eski yedeği yeni orijinal dosyaların üzerine kopyalamayın. Bilinmeyen yama, değişmiş yedek veya desteklenmeyen kaynakta işlem inceleme için durur.

Uygulamayı değiştirirken `private-data` klasörünü saklayın: hazırlanmış paketler, kaynak anlık görüntüleri, ayarlar, güncelleme incelemeleri ve yedekler buradadır. Herkese açık depo ve ZIP yalnız uygulama/araç dosyaları içerir; oyun DAT'ları, anahtar manifestleri, tam İngilizce veya çevrilmiş tablolar, oyun varlıkları, kimlik bilgileri ve özel yedekler paylaşılmaz. Ağ üzerinden çeviride kaynak metin seçtiğiniz sunucuya gider.

Bu proje NC ile bağlantısı veya NC onayı olmayan bağımsız bir topluluk aracıdır. İstemci kullanımını [oyunun bağlantı verdiği EULA](https://store.steampowered.com/eula/3393110_eula_0) düzenler.

## Emeği geçenler

Proje kaynağı [Apache-2.0](LICENSE) lisanslıdır. Kodlayıcı, [CUE4Parse'ın AION 2 biçim çalışmasından](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2) uyarlanmıştır; [Apache-2.0 bildirimini](https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE) koruyun. [repak](https://github.com/trumank/repak) MIT/Apache-2.0 lisanslıdır; bildirimleri Windows ZIP'ine eklenir. Dil listesi [LibreTranslate dil API'sinden](https://docs.libretranslate.com/api/operations/languages/) alınır. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
