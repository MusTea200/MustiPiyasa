Bu proje, kendi makinalarınızda çalışan ve telegram aracılığıyla piyasa takibi yapmanıza yarayan bir programdır.
Programın özellikleri:
1) Yapay zeka tabanlı olduğundan, yazdığınız yazıları algılayıp buna göre kod çalıştırabiliyor.
2) Bildirim aracılığı ile alarmlar kurabilirsiniz. Ve bu alarmları iptal edebilirsiniz.
3) Belirttiğiniz değer, Dolar/Euro/TL olarak belirtilen sayının altında/üstünde ise sizi gerektiğinde uyarabilir.
4) Yahoo finans üzerindeki tüm hisseleri okuyabilir. (ALtın/gümüş piyasası, Dolar/Japon yeni piyasası...)
5) Süre tabanlı bildirimler kurabilirsiniz. (min 1 dakika)
6) Beklediğiniz değerin %5 ve %10 üzerinde ise 3 ve 5 kere bildirim göndererek acil durum yaratır.
7) Sahip olduğunuz değerleri belirtmeniz durumunda bunu kaydeder ve gerektiğinde bu değerlerin anlık TL/Euro/Dolar karşılığını sorabilirsiniz.
8) Takip etmek istediğiniz değerleri, Türkiye saatiyle sabah 8 de bildirim olarak mesaj atar.

Kurulum:
1) Dosyaları bilgisayarınıza veya sanal makinenize indirin.
2) Program içerisinne ".env" adında bir dosya oluşturun.
3) Bundan sonra telegram üzerinden @BotFather üzerinden botunuz için bir api key alın.
4) Google AI studio üzerinden api key alın ve dosya içerisine şu bilgileri yerleştirin:
TELEGRAM_TOKEN=123456:ABC-DEF... (Bu kısmı kendi api key ile doldurun)
GEMINI_API_KEY=AIzaSy... (Bu kısmı kendi api key ile doldurun)
5) Daha sonra bilgisayarınıza python3 kurun.
6) "requirements.txt" dosyasındaki dosyaları kurun.
7) Programı çalıştırabilirsiniz. Artık telegramdan yazdığınızda sizinle konuşan bir asistanınız var.
Not: "portfolio.json" adlı dosyayı temizleyerek, kendi alarmlarınızı ve bakiyenzi koyabileceğiniz bir alan oluşturabilirsiniz.
