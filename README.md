# hotspot
Windows 10 Mobil Etkin Nokta Otomasyonu

Windows 10 açıldığında veya kullanıcı oturum açtığında **Mobil Etkin Nokta** özelliğini otomatik olarak açan Python betiği.

Betik, Windows Runtime API ve PowerShell kullanarak mobil etkin noktayı başlatır, gerçek durumun `On` olduğunu doğrular ve başarısız olursa yeniden dener.

## Özellikler

* Windows 10 Mobil Etkin Nokta özelliğini otomatik açar
* Ethernet bağlantısını Wi-Fi üzerinden paylaşabilir
* Etkin noktanın gerçekten açıldığını doğrular
* Gerekli Windows servislerini kontrol eder
* Başarısız olursa otomatik olarak yeniden dener
* Kullanıcı oturum açtığında zamanlanmış görev olarak çalışabilir
* Siyah konsol penceresi göstermeden arka planda çalışabilir
* Cihaz bağlı değilken otomatik kapanmayı devre dışı bırakmayı dener
* Aylık log dosyası oluşturur
* Eski aylara ait logları otomatik siler
* Log dosyası 1 MB’ı aşarsa eski kayıtları temizler

## Gereksinimler

* Windows 10
* Python 3.10 veya üzeri
* Wi-Fi adaptörü
* Windows Mobil Etkin Nokta özelliğinin çalışır durumda olması
* İnternet bağlantısı
* Zamanlanmış görev kurulumu için yönetici yetkisi

Python’ın kurulu olduğunu kontrol etmek için:

```bat
py --version
```

veya:

```bat
python --version
```

## Kurulum

Dosyayı istediğiniz bir klasöre kopyalayın.

Örnek:

```text
C:\pyton\wifi_hotspot_on.py
```

> Klasör adı farklı olabilir. Komutlarda gerçek dosya yolunu kullanın.

Windows’ta önce şu bölümü bir kez manuel olarak yapılandırın:

```text
Ayarlar → Ağ ve İnternet → Mobil etkin nokta
```

Buradan paylaşılacak internet bağlantısını, ağ adını, Wi-Fi parolasını ve paylaşım seçeneğini ayarlayın.

## Elle çalıştırma

Komut İstemi veya PowerShell açın:

```bat
py "C:\pyton\wifi_hotspot_on.py"
```

Başarılı çalışmada mobil etkin nokta birkaç saniye içinde açılır.

## Windows açılışında otomatik çalıştırma

Komut İstemi’ni **Yönetici olarak çalıştırın** ve şu komutu girin:

```bat
py "C:\pyton\wifi_hotspot_on.py" --install
```

Betik, kullanıcı oturum açtıktan yaklaşık 45 saniye sonra çalışacak bir Windows zamanlanmış görevi oluşturur.

Görev adı:

```text
WiFi_Mobil_Etkin_Nokta_Ac
```

## Otomatik görevi kaldırma

Komut İstemi’ni yönetici olarak açın:

```bat
py "C:\pyton\wifi_hotspot_on.py" --remove
```

## Log dosyaları

Loglar şu klasörde tutulur:

```text
%LOCALAPPDATA%\WiFiHotspotAuto
```

Dosya adı aylık olarak oluşturulur:

```text
hotspot-2026-07.log
```

Log yönetimi:

* Yalnızca içinde bulunulan aya ait log tutulur
* Önceki aylara ait loglar otomatik silinir
* Eski `hotspot.log` dosyası otomatik kaldırılır
* Log 1 MB’ı aşarsa en yeni yaklaşık 500 KB korunur

Başarılı bir çalışmada logun sonunda şu satırlar görülür:

```text
DOGRULANDI: Mobil etkin nokta acik.
SONUC: Mobil etkin nokta gerçek On durumunda doğrulandı.
```

Etkin nokta zaten açıksa:

```text
DOGRULANDI: Mobil etkin nokta zaten acik.
```

## Nasıl çalışır?

Betik şu işlemleri uygular:

1. `icssvc` ve `SharedAccess` servislerini kontrol eder
2. Aktif internet profilini bulur
3. Tethering desteğini kontrol eder
4. Mobil etkin noktanın mevcut durumunu okur
5. Gerekirse yarım kalmış paylaşım oturumunu durdurur
6. `StartTetheringAsync()` çağrısını başlatır
7. Durumu yarım saniyelik aralıklarla kontrol eder
8. Gerçek durum `On` olduğunda işlemi başarılı kabul eder
9. Başarısız olursa yeniden dener

## Sorun giderme

### Mobil etkin nokta manuel olarak da açılmıyor

Önce Windows ayarlarından manuel olarak test edin:

```text
Ayarlar → Ağ ve İnternet → Mobil etkin nokta
```

Manuel olarak da açılmıyorsa sorun Python betiğinden kaynaklanmayabilir.

Şunları kontrol edin:

* Wi-Fi adaptörü etkin mi?
* Uçak modu kapalı mı?
* İnternet bağlantısı aktif mi?
* Mobil etkin nokta ayarları daha önce yapılandırılmış mı?
* Ağ sürücüleri güncel mi?

### `Tethering yetenegi: Disabled` hatası

Aktif internet profili paylaşımı desteklemiyor olabilir.

Ethernet veya Wi-Fi bağlantınızı kontrol edin ve Mobil Etkin Nokta’yı Windows ayarlarından bir kez manuel açmayı deneyin.

### Görev oluşturulamıyor

Komut İstemi’nin yönetici olarak açıldığından emin olun:

```bat
py "C:\pyton\wifi_hotspot_on.py" --install
```

### Bilgisayar açıldığında çalışmıyor

Görev Zamanlayıcı’yı açın:

```text
Win + R → taskschd.msc
```

Şu görevi bulun:

```text
WiFi_Mobil_Etkin_Nokta_Ac
```

Ayrıca log klasörünü kontrol edin:

```text
%LOCALAPPDATA%\WiFiHotspotAuto
```

### Python yolu değişti

Python kaldırılır, yeniden kurulur veya farklı sürüme geçilirse zamanlanmış görevi yeniden oluşturun:

```bat
py "C:\pyton\wifi_hotspot_on.py" --remove
py "C:\pyton\wifi_hotspot_on.py" --install
```

## Güvenlik

Betik:

* Wi-Fi ağ adını değiştirmez
* Wi-Fi parolasını değiştirmez
* Parolayı log dosyasına yazmaz
* Harici bir sunucuya veri göndermez
* İnternet üzerinden herhangi bir dosya indirmez

Mobil etkin nokta adı ve parolası Windows ayarlarından yönetilir.

## Bilinen sınırlamalar

* Windows 11 üzerinde çalışabilir ancak bu sürüm Windows 10 için hazırlanmıştır
* Bazı eski Windows 10 derlemelerinde otomatik kapanmayı devre dışı bırakan API bulunmayabilir
* Mobil etkin nokta özelliği donanım veya sürücü tarafından desteklenmiyorsa betik bunu açamaz
* Kurumsal grup ilkeleri tethering kullanımını engelleyebilir
* Kullanıcı oturum açmadan önce çalışacak bir sistem servisi değildir

## Dosya

Ana betik:

```text
wifi_hotspot_on.py
```

## Katkı

Hata bildirirken şu bilgileri eklemek yararlı olur:

* Windows sürümü
* Python sürümü
* İnternet bağlantı türü
* Log dosyasının ilgili bölümü

Parola, kullanıcı adı veya kişisel ağ bilgilerini paylaşmayın.

## Sorumluluk reddi

Bu proje kişisel kullanım ve otomasyon amacıyla hazırlanmıştır. Kullanım sırasında oluşabilecek ağ, bağlantı veya sistem sorunlarından kullanıcı sorumludur.
