MATSYA LIBRARY ALWAR – TELEGRAM BOT
====================================

शामिल सुविधाएँ:
- Welcome menu
- Online admission (नाम, मोबाइल, membership plan)
- Admission approval by admin
- Seat information (कुल क्षमता 120; approved students के आधार पर अनुमान)
- Fee plans
- Student details
- Complaint categories and complaint forwarding to admin
- Admin commands: /admin /students /complaints /seats /approve /fee /assign /broadcast

महत्वपूर्ण:
1) BotFather token किसी को भी चैट में न भेजें। इसे अपने कंप्यूटर/होस्टिंग के environment variable में रखें।
2) अपना Telegram numeric user ID पता करके ADMIN_IDS में डालें। एक से अधिक Admin हों तो comma से अलग करें।
3) Python 3.10+ इंस्टॉल करें।
4) कमांड चलाएँ:
   pip install -r requirements.txt
   export BOT_TOKEN="आपका_token"
   export ADMIN_IDS="आपका_telegram_numeric_id"
   python bot.py

Windows PowerShell:
   $env:BOT_TOKEN="आपका_token"
   $env:ADMIN_IDS="आपका_telegram_numeric_id"
   pip install -r requirements.txt
   python bot.py

BotFather:
- /setcommands चलाकर यह commands सेट करें:
  start - मुख्य मेन्यू खोलें
  admin - Admin panel help
  students - विद्यार्थी सूची (Admin)
  complaints - शिकायतें (Admin)
  seats - सीट स्थिति (Admin)

Admin usage:
- /approve 123456789
- /fee 123456789 paid
- /assign 123456789 A-01
- /broadcast कल लाइब्रेरी सुबह 6 बजे खुलेगी

सीमाएँ/सावधानियाँ:
- यह शुरुआती production-ready foundation है; deploy और live test करना बाकी है।
- फीस भुगतान gateway/UPI auto-verification, वास्तविक live seat locking, CSV export, attendance QR और web dashboard अभी शामिल नहीं हैं।
- सीट संख्या अभी approved student count से अनुमानित है; एक साथ multiple admissions में manual seat allocation करें।
- संपर्क/पता memory में उपलब्ध Matsya Library details पर आधारित हैं; deploy से पहले verify करें।
