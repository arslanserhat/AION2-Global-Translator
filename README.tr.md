<p align="center">
  <img src="assets/banner.svg" alt="AION 2 Global Translator — oyun metinlerini seçtiğiniz dile çevirin" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="docs/LANGUAGES.md">Dil uyumluluğu</a> ·
  <a href="docs/TRANSLATION.md">Çeviri iş akışı</a> ·
  <a href="docs/QUALITY.md">Kalite incelemesi</a> ·
  <a href="CONTRIBUTING.md">Katkıda bulunun</a>
</p>

# AION 2 Global Translator

Kendi oyun kurulumunuzdan **AION 2'nin yerel metin dosyalarını çevirmek ve yönetmek** için geliştirilen ücretsiz, açık kaynaklı bir Windows uygulaması. Çeviri sağlayıcınızı seçin, yerel bir dil paketi oluşturun ve doğrulanmış yedekle kurun.

Hedef dil desteği, seçtiğiniz sağlayıcıya ve oyunun yazı tiplerine bağlıdır. Proje, bütün dillerin çalıştığını iddia etmez.

## Neler yapar?

- Desteklenen İngilizce yerelleştirme biçimini kendi oyun dosyalarınızdan okur.
- Sizin belirlediğiniz LibreTranslate uyumlu sunucuyla çalışır; dil listesini o sunucudan alır.
- Tam bir yerel JSON çeviri haritasını içe aktararak çevrimdışı paket oluşturur.
- Ana ekrandan hedef dil seçmenizi ve uyumlu yerel paketi uygulamanızı sağlar.
- Kayıt kimliklerini ve gerekli biçim öğelerini koruyarak yerel metin dosyası oluşturur.
- Orijinal dosyaları geri yüklemek üzere yedekler; değişiklikten önce oyun sürümünü denetler.
- Çeviriyi oluşturma ve oyuna kurma adımlarını ayırır; sonucu önce inceleyebilirsiniz.
- Gövde metnindeki Türkçe harfleri koruyarak oyunun kısıtlı başlık yazı tipleri için uyumlu gösterim sunar.

Oyun, hazırlanan metin dosyasını doğrudan okur. Bu yöntem ekran görüntüsü OCR'ına dayanmaz. Seslendirme, görsellere gömülü yazılar ve canlı oyuncu sohbeti kapsam dışındadır.

## Mevcut durum

**Deneysel.** Kodlayıcı, Windows Steam **25926599** sürümünün **153.042 kayıt** içeren İngilizce metin tablosuyla doğrulandı. Kaynağı bayt düzeyinde koruyan yeniden yazım ve değiştirilmiş Unicode metnin kodlanıp geri okunması testleri geçti. Bunlar dosya biçimini doğrular; bütün oyunun sorunsuz çalıştığını kanıtlamaz.

**153.042 kayıtlı Türkçe yama üretildi ve yerel olarak kuruldu**; orijinal dosyaların yedeği korundu. Bütün kaynak tablo programatik olarak tarandıktan sonra seçilmiş düzenlemeler, bağlam kuralları ve şablonlardan **18.712 farklı düzeltme anahtarı** kurulu sürüme birleştirildi. Dosyanın geri okunan tam anahtar/metin haritası ve yeniden kodlama denetimi geçti; çözülmemiş biçim hatası kalmadı. Bu düzeltme sayısı, bütün kayıtların tek tek insan tarafından incelendiğini göstermez. Biçim ve dosya testleri, anlam ve görünüm denetimlerinden ayrı değerlendirilir.

Oyuncunun ekran görüntüsünde Türkçe gövde metni doğrulandı; bir başlıkta eksik harfler görüldü. Font incelemesi, oyunun İngilizce başlık yazı tiplerinin Türkçe kapsamının eksik olduğunu gösterdi. v0.1.1, aşağıdaki uyumluluk seçeneğiyle belirli başlıkları düzenler; düzeltilmiş sonucun oyun yeniden açıldıktan sonra kontrol edilmesi gerekir. Oyuna ait tam tablo ve yerel düzeltme haritası, herkese açık indirmeye eklenmiyor. Paketlenmiş Windows uygulaması başarıyla açıldı; [yerel test bilgileri](CONTRIBUTING.md#tests) ve [inceleme kapsamı](docs/QUALITY.md) belgelendi.

| Alan | Durum |
| --- | --- |
| Windows Steam 25926599 / İngilizce kaynak | Kodlayıcı doğrulandı; oyuna kurulum deneysel |
| Türkçe | Tam yerel yama kuruldu; oyuncu görüntüsünde gövde metni görüldü; v0.1.1'e başlık uyumluluğu eklendi |
| Diğer hedef diller | Sağlayıcının dil çiftine ve oyun içi yazı tipi denetimine bağlı |
| Diğer sürümler, bölgeler ve başlatıcılar | Doğrulanmadı |
| Ses, görseldeki yazı ve canlı sohbet | Bu metin yamasının kapsamı dışında |

Sağlayıcının bir dili sunmasıyla o dilin oyun içinde çalışması arasındaki fark için [dil uyumluluğu belgesine](docs/LANGUAGES.md) bakın.

[Kalite incelemesi raporu](docs/QUALITY.md); genel taramayı, seçilmiş anlam düzeltmelerini, terim tercihlerini ve tekil emir kipi düzenlemesini açıklar. Bu denetimler, bütün cümlelerin insan tarafından incelendiği veya bütün oyunun görsel olarak doğrulandığı anlamına gelmez.

## Dili seçme ve uygulama

Ana ekrandaki **Hedef dil** alanından dili seçin. Varsayılan Türkçedir; listeden başka bir dil seçebilir veya dil kodunu elle yazabilirsiniz. Bu alan oyunun çeviri hedefini belirler; ayrı Türkçe/English arayüz seçimi uygulamanın yazılarını değiştirir. Hedef listesi, seçim kolaylığı sağlar; her dilin paketinin hazır olduğu veya sağlayıcıyla oyunun listedeki bütün dilleri desteklediği anlamına gelmez.

| Düğme | İşlem |
| --- | --- |
| **Çeviriyi uygula** | Seçilen dilin uyumlu hazır paketini kurar; hazır paket yoksa o dil seçili olarak çeviri ayarlarını açar |
| **Orijinale dön** | Doğrulanmış orijinal dosyaları geri yükler; İngilizce seçildiğinde de bu işlem sunulur |
| **Başlıkları düzelt (Türkçe)** | Türkçeye özel mevcut terim ve başlık gösterimi düzeltmesini uygular; diğer dillerde kapalıdır |

**Çeviri ayarları…** sağlayıcı ve çevrimdışı harita seçeneklerini açar. **Ayrıntılar…** altında işlem günlüğü, kurulum kontrolü, İngilizce kaynak dışa aktarma ve hazır paket kurma bulunur. Herkese açık indirme uygulamayı içerir; oyun verisini içeren paketler kendi kurulumunuzdan yerel olarak üretilir.

Biçim, sayı, değişken ve teknik kısaltma denetimleri bütün hedef diller için ortaktır. On ek dil profili, belirli alanlarda kısa arayüz etiketleri ve seçilmiş oyun terimleri sağlar. Daha geniş anlam incelemesi ve başlık uyumluluğu Türkçe için hazırlanmıştır; başka bir dilin bütün cümlelerinin, dil bilgisinin veya fontlarının doğrulandığı anlamına gelmez. Ayrıntılar [dillere göre inceleme bölümünde](docs/LANGUAGES.md#review-and-corrections-by-language).

Herhangi bir dildeki çeviriyi düzeltmek için hedefi seçip **Ayrıntılar… → Çeviriyi dışa aktar…** yolunu kullanın. Tam JSON haritasında ilgili metinleri düzenleyin ve **Çeviri ayarları… → Çevrimdışı JSON** yoluyla yeniden oluşturun. Düzenlenebilir yerel harita, Türkçe başlık harfleri sadeleştirilmeden önce saklanır. Uygulama içinde tek tek kayıt düzenleyicisi bulunmaz; [düzeltme akışını](docs/TRANSLATION.md#custom-maps) izleyebilirsiniz.

## Türkçe başlık uyumluluğu

Gövde yazı tipi Türkçeyi desteklese de bazı İngilizce başlık fontlarında Türkçe harfler yok. Türkçe paketlerde varsayılan açık **font uyumlu başlıklar** seçeneği, belirli ad/başlık alanlarında okunabilir ASCII yazımı kullanır: `Ödüller → Oduller`, `Keskin Atış → Keskin Atis`. Gövde metni `ç ğ ı İ ö ş ü` ve büyük harflerini korur. Başlıklarda okunabilirlik için Türkçe yazımından ödün verilir; oyunun fontları değiştirilmez veya yeni harf eklenmez.

v0.1.1, mevcut uyumlu Türkçe kurulumunu onarabilir; **Snipe** yeteneğinin yanlış kuş çevirisi dahil 31 ilgili yetenek adı kaydını düzeltir. Kaynak haritalar korunur; font dosyaları paylaşılmaz veya değiştirilmez. Ayrıntılar [iş akışında](docs/TRANSLATION.md#turkish-title-compatibility) ve [v0.1.1 notlarında](docs/RELEASE-v0.1.1.md).

## Başlangıç

### Windows uygulamasını indirme

[En son yayımın](https://github.com/arslanserhat/AION2-Global-Translator/releases/latest) Windows ZIP dosyasını indirip çıkarın; `AION2-Global-Translator.exe` uygulamasını çalıştırın. Uygulama dosyası yaklaşık **17,7 MB** boyutundadır. ZIP, `repak` 0.2.3 ve lisans bildirimlerini içerir; bu dağıtım için Python veya ayrıca `repak` indirmeniz gerekmez. Oyun DAT'ı ve tam çeviri tablosu içermez; çalışma dosyaları kendi kurulumunuzdan üretilir. [v0.1.1 yayım notlarını](docs/RELEASE-v0.1.1.md) inceleyebilirsiniz.

### Kaynak koddan çalıştırma

Python **3.12 veya üzerini** kurun; proje klasöründe şu komutları çalıştırın:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m aion2_global_translator
```

Örnekteki Python sürümünü, bilgisayarınızda kurulu 3.12+ sürüme göre değiştirebilirsiniz. Windows için `Start-Translator.cmd` başlatma girişi de sağlanır. Paket kurulumu, `cryptography`, `blake3` ve `lz4` dahil bağımlılıkları yükler.

Windows uygulaması PyInstaller ile paketlenir. Yukarıdaki kaynak kurulumu, geliştirme ve kod incelemesi için kullanılabilir.

### Dil paketi hazırlama ve kurma

1. Güncel, yasal bir Steam AION 2 kurulumu kullanın. Mevcut iş akışının kaynak dili **İngilizce**dir.
2. Windows yayım ZIP'i `repak` içerir. Kaynak koddan kurulum için Windows `repak` **0.2.3** uygulamasını [kendi yayımından](https://github.com/trumank/repak/releases/tag/v0.2.3) indirin; `tools/repak.exe` yoluna koyun veya `REPAK_PATH` değişkenini bulunduğu konuma ayarlayın.
3. **Ayrıntılar… → Kurulumu kontrol et** ile kaynağı doğrulayın. **Ayrıntılar… → İngilizce kaynağı dışa aktar…** yolunu kullanıp kendi kaynağınızdan tam bir çevrimdışı harita hazırlayın. Çıkarılan oyun dosyaları ve tablolar bilgisayarınızda kalır.
4. Ana ekrandan **Hedef dil** seçin; **Çeviri ayarları…** penceresini açın. Tam bir yerel JSON haritasını içe aktarın veya LibreTranslate uyumlu sunucu adresinizi, gerekiyorsa kendi API anahtarınızı girin. Sağlayıcıyla çeviride hedef, sunucunun dilleri ve İngilizce kaynak çifti üzerinden denetlenir.
5. Çeviriyi oluşturup inceleyin. Biçim hatalarını giderin; temel menüleri, yetenekleri, görev yönlendirmelerini ve bulmaca ipuçlarını kontrol edin.
6. AION 2'yi tamamen kapatın; uyumlu paket hazır olduğunda hedef dili seçip **Çeviriyi uygula** düğmesini kullanın. **Ayrıntılar… → Hazır dil paketini kur…** ile paket klasörünü ayrıca seçebilirsiniz. Orijinal yedeği saklayın. Oyunun metin dilini **English** olarak bırakıp çevrilmiş menüleri oyun içinde kontrol edin.

Uygulama ücretsizdir; harici çeviri hizmetinin kendi ücretleri, kullanım sınırları ve koşulları olabilir. LibreTranslate'i kendiniz de barındırabilirsiniz; bunun için [resmî kurulum belgesini](https://docs.libretranslate.com/guides/installation/) izleyin ve gerekli dil modellerini yükleyin.

Paket oluşturma işlemi oyuna kurulum yapmaz. Bir dili uygulamak için yerel olarak hazırlanmış uyumlu paket gerekir; herkese açık depo oyunun tam çevrilmiş tablolarını içermez. İçe aktarmadan önce [harita biçimi belgesini](docs/TRANSLATION.md#custom-maps) okuyun.

Çevrimdışı haritada değişmeden kalan dilsel metinler varsa `unchanged-review.json` raporu oluşturulur; bu kayıtları incelediğinizi açıkça onaylamadan paket hazırlanmaz. Yalnız bilerek aynı bırakılan adları veya etiketleri onaylayın; bu inceleme ve biçim doğrulaması, çevirinin bütünüyle doğru olduğunu kanıtlamaz.

## Güncellemeler ve geri yükleme

Uygulama, aynı kaynak sürümde kendi doğruladığı uyumlu paketler arasında geçiş yapabilir; orijinal yedek korunur. Paket uygulamadan önce AION 2'yi kapatın. Oyunu güncellemeden önce orijinal dosyaları geri yükleyin; mevcut yamayı başka bir araç kurduysa önce o aracın geri yükleme yolunu kullanın. Yama ve yedeği belirli bir kaynak sürüme aittir; eski yedeği güncellenmiş oyunun üzerine yazmayın. Sürüm ya da hash denetimi başarısızsa güncel resmî dosyalardan yeni kaynak hazırlayın.

İstemci dosyalarını değiştirmek, oyunun koşulları veya bütünlük denetimleriyle çelişebilir. Projenin NC onayı ya da hesap güvenliği garantisi yoktur. İstemci kullanımını [oyunun bağlantı verdiği EULA](https://store.steampowered.com/eula/3393110_eula_0) düzenler.

## Bu depoda oyun verisi paylaşılmaz

Herkese açık depo; uygulama kaynağı, belgeler ve yapay test örneklerini içerir. Oyun DAT'ları, anahtar manifestleri, çıkarılmış veya çevrilmiş tam metin tabloları, oyun yedekleri, API bilgileri ve kişisel dosya yolları eklenmez. Çalışma dosyalarını kendi kurulumunuzdan üretirsiniz.

Ağ üzerinden çeviri etkinleştirildiğinde kaynak metin seçtiğiniz sunucuya gönderilir. Sağlayıcının erişim ve metin işleme koşullarını dikkate alın; kimlik bilgilerini ve çeviri önbelleklerini depoya göndermeyin.

## Emeği geçenler

Proje kaynağı [Apache-2.0](LICENSE) lisanslıdır; uyarlanmış kod ve bağımlılıklar için birlikte verilen üçüncü taraf bildirimlerini inceleyin.

Yerelleştirme kodlayıcısı, [CUE4Parse'ın AION 2 biçim çalışmasından](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2) uyarlanmıştır. CUE4Parse [Apache-2.0](https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE) lisanslıdır. `repak`, [MIT ve Apache-2.0 lisanslarıyla](https://github.com/trumank/repak) sunulur; kendi lisans bildirimleri Windows ZIP'ine eklenir. Dil listesi, seçtiğiniz sunucunun [LibreTranslate `/languages` arayüzünden](https://docs.libretranslate.com/api/operations/languages/) alınır.

AION 2 ve oyun içeriği NC'ye ve ilgili hak sahiplerine aittir. Bu proje bağımsız bir topluluk aracıdır; resmî bağlantı veya onay anlamına gelmez.
