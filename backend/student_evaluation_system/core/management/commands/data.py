"""
Seed data for Acıbadem University Computer Engineering program.

Curriculum sourced from:
https://obs.acibadem.edu.tr/oibs/bologna/index.aspx?lang=tr&curOp=showPac&curUnit=14&curSunit=6246
"""

UNIVERSITIES = [
    "Acıbadem Üniversitesi",
    "Orta Doğu Teknik Üniversitesi",
    "Boğaziçi Üniversitesi",
    "İstanbul Teknik Üniversitesi",
]

DEPARTMENTS = [
    {"name": "Mühendislik ve Doğa Bilimleri Fakültesi", "code": "ENG", "university": "Acıbadem Üniversitesi"},
    {"name": "Tıp Fakültesi", "code": "MED", "university": "Acıbadem Üniversitesi"},
]

DEGREE_LEVELS = [{"name": "Lisans", "level": 1}, {"name": "Yüksek Lisans", "level": 2}, {"name": "Doktora", "level": 3}]

PROGRAMS = [
    {"name": "Bilgisayar Mühendisliği (İngilizce)", "code": "CSE", "department": "ENG", "degree_level": 1},
    {"name": "Biyomedikal Mühendisliği (İngilizce)", "code": "BME", "department": "ENG", "degree_level": 1},
    {"name": "Biyomedikal Mühendisliği (İngilizce)", "code": "BMEMS", "department": "ENG", "degree_level": 2},
    {"name": "Biyomedikal Mühendisliği (İngilizce)", "code": "BMEDR", "department": "ENG", "degree_level": 3},
]

NAMES = [
    "Ahmet",
    "Ayşe",
    "Mustafa",
    "Fatma",
    "Mehmet",
    "Zeynep",
    "Ali",
    "Hatice",
    "Hüseyin",
    "Emine",
    "Hasan",
    "Elif",
    "İbrahim",
    "Meryem",
    "Osman",
    "Zehra",
    "Süleyman",
    "Ayşegül",
    "Yusuf",
    "Rabia",
    "Ömer",
    "Asiye",
    "Abdullah",
    "Esra",
    "Merve",
    "Murat",
    "Recep",
    "Ramazan",
    "Hediye",
    "Halil",
    "Sevim",
    "İsa",
    "Musa",
    "Yakup",
    "Mahmut",
    "İsmail",
    "Bekir",
    "Zeliha",
    "Elifnur",
    "Kemal",
    "Selin",
    "Burak",
    "Ceren",
    "Deniz",
    "Ebru",
    "Fırat",
    "Gamze",
    "Tolga",
    "Pelin",
    "Koray",
    "Seda",
    "Onur",
    "Bahar",
    "Umut",
    "İrem",
    "Caner",
    "Tuğçe",
    "Serkan",
    "Melis",
    "Volkan",
    "Derya",
    "Erdem",
    "Sinem",
    "Alper",
    "Gizem",
    "Ozan",
    "Burcu",
    "Barış",
    "Yasemin",
    "Tuna",
    "Ece",
    "Cem",
    "Leyla",
    "Ege",
    "Nazlı",
    "Mert",
    "Aylin",
    "Kaan",
    "Buse",
    "Arda",
    "İlayda",
    "Emre",
    "Sıla",
    "Berke",
    "Duru",
]

SURNAMES = [
    "Yılmaz",
    "Demir",
    "Kaya",
    "Çelik",
    "Öztürk",
    "Arslan",
    "Yıldız",
    "Aydın",
    "Özkan",
    "Şahin",
    "Yıldırım",
    "Çetin",
    "Kara",
    "Koç",
    "Kurt",
    "Doğan",
    "Yavuz",
    "Aksoy",
    "Bulut",
    "Şimşek",
    "Korkmaz",
    "Keskin",
    "Arıkan",
    "Güler",
    "Can",
    "Aslan",
    "Taş",
    "Nur",
    "Balcı",
    "Gül",
    "Çakar",
    "Tuna",
    "Deniz",
    "Şen",
    "Melek",
    "Özer",
    "Akın",
    "Tekin",
    "Erdoğan",
    "Polat",
    "Acar",
    "Sönmez",
    "Albayrak",
    "Eren",
    "Karadağ",
    "Uzun",
    "Akkaya",
    "Durmaz",
    "Küçük",
    "Büyük",
    "Bozkurt",
    "Aslan",
    "Erdem",
    "Toprak",
    "Bayraktar",
    "Ateş",
    "Kaplan",
    "Uçar",
    "Sezgin",
    "Okur",
    "Özcan",
    "Kılıç",
    "Yalçın",
    "Turan",
    "Koçoğlu",
    "Ergin",
    "Sarı",
    "Akyüz",
    "Erkan",
    "Ayhan",
    "Dağ",
    "Sönmez",
    "Güneş",
    "Tam",
    "Çetin",
    "Akgün",
    "Karaaslan",
    "Yaman",
    "Kurtuluş",
    "Baş",
    "Mutlu",
]

INSTRUCTORS = [
    {
        "username": "ahmetbulut",
        "email": "ahmet.bulut@acibadem.edu.tr",
        "first_name": "Ahmet",
        "last_name": "Bulut",
        "password": "instructor123",
        "title": "Prof. Dr.",
    },
    {
        "username": "mehmetserkanapaydin",
        "email": "mehmetserkan.apaydin@acibadem.edu.tr",
        "first_name": "Mehmet Serkan",
        "last_name": "Apaydın",
        "password": "instructor123",
        "title": "Dr. Öğr. Üyesi",
    },
    {
        "username": "mahsaziraksima",
        "email": "mahsa.ziraksima@acibadem.edu.tr",
        "first_name": "Mahsa",
        "last_name": "Ziraksima",
        "password": "instructor123",
        "title": "Öğr. Gör. Dr.",
    },
    {
        "username": "sultansütlü",
        "email": "sultan.sutlu@acibadem.edu.tr",
        "first_name": "Sultan",
        "last_name": "Sütlü",
        "password": "instructor123",
        "title": "Öğr. Gör. Dr.",
    },
    {
        "username": "cengizriva",
        "email": "cengiz.riva@acibadem.edu.tr",
        "first_name": "Cengiz",
        "last_name": "Riva",
        "password": "instructor123",
        "title": "Öğr. Gör.",
    },
]

# Full 8-semester curriculum.
# Each course: (code, name, credits, type, [learning_outcomes], [(assessment_name, weight), ...])
CURRICULUM = {
    "semester_1": [
        (
            "CSE101",
            "Programlamaya Giriş",
            6,
            "Zorunlu",
            [
                "Temel programlama yapılarını öğrenir",
                "Temel veri yapılarını öğrenir",
                "Nesne yönelimli programlamanın temellerini öğrenir",
            ],
            [("Ara Sınav", 0.20), ("Proje", 0.45), ("Final", 0.25), ("Laboratuvar", 0.10)],
        ),
        (
            "MAT111",
            "Kalkülüs I",
            6,
            "Zorunlu",
            [
                "Tek değişkenli fonksiyonlarda limit, süreklilik ve türev kavramlarını uygular",
                "Belirli ve belirsiz integral hesaplamalarını yapar",
                "Türev ve integral uygulamalarını mühendislik problemlerine uyarlar",
            ],
            [("Ara Sınav", 0.30), ("Ödev", 0.20), ("Final", 0.50)],
        ),
        (
            "PHY101",
            "Fizik I",
            6,
            "Zorunlu",
            [
                "Newton mekaniğinin temel yasalarını uygular",
                "Enerji, iş ve momentum korunum ilkelerini analiz eder",
                "Mekanik sistemlerin hareket denklemlerini çözer",
            ],
            [("Ara Sınav", 0.25), ("Laboratuvar", 0.25), ("Final", 0.50)],
        ),
    ],
    "semester_2": [
        (
            "CSE102",
            "Programlama Pratiği",
            6,
            "Zorunlu",
            [
                "Tkinter ile Python'da GUI programlamayı öğrenir",
                "Bir programdaki dosya tabanlı yapılarla etkileşim kurmayı öğrenir",
                "İşbirlikçi filtreleme, sınıflandırma, kümeleme dahil pratik veri madenciliği tekniklerini öğrenir",
            ],
            [("Ara Sınav", 0.20), ("Proje", 0.50), ("Final", 0.30)],
        ),
        (
            "MAT112",
            "Kalkülüs II",
            6,
            "Zorunlu",
            [
                "Çok değişkenli fonksiyonlarda kısmi türev ve çok katlı integral hesaplar",
                "Diziler ve serilerin yakınsaklığını analiz eder",
                "Vektör analizi ve çizgi integrallerini uygular",
            ],
            [("Ara Sınav", 0.30), ("Ödev", 0.20), ("Final", 0.50)],
        ),
        (
            "PHY102",
            "Fizik II",
            6,
            "Zorunlu",
            [
                "Elektrik ve manyetizma temel yasalarını uygular",
                "Elektrik devrelerini analiz eder",
                "Elektromanyetik dalgaların özelliklerini açıklar",
            ],
            [("Ara Sınav", 0.25), ("Laboratuvar", 0.25), ("Final", 0.50)],
        ),
    ],
    "semester_3": [
        (
            "CSE201",
            "Algoritmalar I",
            6,
            "Zorunlu",
            [
                "Temel algoritma tasarım tekniklerini (böl-ve-yönet, dinamik programlama, açgözlü) uygular",
                "Algoritmaların zaman ve alan karmaşıklığını asimptotik notasyonla analiz eder",
                "Sıralama, arama ve temel grafik algoritmalarını karşılaştırmalı olarak değerlendirir",
            ],
            [("Ara Sınav", 0.20), ("Ödev", 0.30), ("Final", 0.50)],
        ),
        (
            "MAT211",
            "Lineer Cebir",
            6,
            "Zorunlu",
            [
                "Matris işlemleri, determinant ve özdeğer problemlerini çözer",
                "Lineer denklem sistemlerini analiz eder ve çözer",
                "Vektör uzayları ve lineer dönüşüm kavramlarını mühendislik bağlamında uygular",
            ],
            [("Ara Sınav", 0.30), ("Ödev", 0.20), ("Final", 0.50)],
        ),
        (
            "MAT241",
            "Ayrık Matematik",
            6,
            "Zorunlu",
            [
                "Önermeler mantığı, kümeler ve bağıntıları kullanarak ispat tekniklerini uygular",
                "Kombinatorik ve olasılık hesaplamalarını yapar",
                "Çizge kuramı ve ağaç yapılarını bilgisayar bilimi problemlerine uygular",
            ],
            [("Ara Sınav", 0.25), ("Ödev", 0.25), ("Final", 0.50)],
        ),
    ],
    "semester_4": [
        (
            "CSE202",
            "Algoritmalar II",
            6,
            "Zorunlu",
            [
                "Gelişmiş grafik algoritmalarını (en kısa yol, akış ağları) uygular",
                "NP-tamlık kavramını açıklar ve problemleri sınıflandırır",
                "Sezgisel ve yaklaşık algoritma tekniklerini karşılaştırır",
            ],
            [("Ara Sınav", 0.20), ("Ödev", 0.30), ("Final", 0.50)],
        ),
        (
            "CSE220",
            "Web Programlama",
            6,
            "Zorunlu",
            [
                "HTML, CSS ve JavaScript ile etkileşimli web arayüzleri geliştirir",
                "İstemci-sunucu mimarisini ve HTTP protokolünü açıklar",
                "Bir web çatısı kullanarak tam yığın web uygulaması inşa eder",
            ],
            [("Ara Sınav", 0.20), ("Proje", 0.40), ("Final", 0.40)],
        ),
        (
            "MAT222",
            "Diferansiyel Denklemler",
            6,
            "Zorunlu",
            [
                "Birinci ve ikinci mertebe diferansiyel denklemleri sınıflandırır ve çözer",
                "Laplace dönüşümünü kullanarak başlangıç değer problemlerini çözer",
                "Diferansiyel denklem sistemlerini mühendislik sistemlerine uygular",
            ],
            [("Ara Sınav", 0.30), ("Ödev", 0.20), ("Final", 0.50)],
        ),
    ],
    "semester_5": [
        (
            "CSE301",
            "Bilgisayar Mimarisi",
            6,
            "Zorunlu",
            [
                "Bilgisayar organizasyonunun temel bileşenlerini (CPU, bellek, G/Ç) açıklar",
                "Komut kümesi mimarisi ve assembly programlamayı uygular",
                "Bellek hiyerarşisi ve önbellek tasarımının performansa etkisini analiz eder",
            ],
            [("Ara Sınav", 0.25), ("Proje", 0.25), ("Final", 0.50)],
        ),
        (
            "CSE311",
            "Yazılım",
            6,
            "Zorunlu",
            [
                "Yazılım geliştirme yaşam döngüsü modellerini karşılaştırır",
                "Gereksinim analizi, sistem tasarımı ve UML diyagramları oluşturur",
                "Yazılım test stratejilerini ve kalite güvence yöntemlerini uygular",
            ],
            [("Ara Sınav", 0.20), ("Proje", 0.40), ("Final", 0.40)],
        ),
        (
            "CSE321",
            "Veri Sistemleri",
            6,
            "Zorunlu",
            [
                "Varlık-ilişki modeli ile kavramsal veritabanı tasarımı oluşturur",
                "İlişkisel modele dönüşüm ve normalizasyon uygular",
                "Karmaşık SQL sorguları, indeksleme ve sorgu optimizasyonu yapar",
                "Veritabanı yönetim sistemlerinin iç mimarisini açıklar",
            ],
            [("Ara Sınav", 0.20), ("Proje", 0.30), ("Final", 0.50)],
        ),
        (
            "CSE331",
            "Keşifsel Veri Analizi",
            6,
            "Zorunlu",
            [
                "Veri temizleme, dönüştürme ve görselleştirme tekniklerini uygular",
                "İstatistiksel özetleme ve hipotez testi yöntemlerini kullanır",
                "Pandas, NumPy ve Matplotlib kütüphaneleri ile keşifsel veri analizi yapar",
            ],
            [("Ara Sınav", 0.20), ("Proje", 0.40), ("Final", 0.40)],
        ),
    ],
    "semester_6": [
        (
            "CSE302",
            "İşletim Sistemleri",
            6,
            "Zorunlu",
            [
                "Süreç yönetimi, planlama algoritmaları ve senkronizasyon mekanizmalarını açıklar",
                "Bellek yönetimi, sanal bellek ve sayfalama tekniklerini karşılaştırır",
                "Dosya sistemleri ve G/Ç yönetimi prensiplerini uygular",
            ],
            [("Ara Sınav", 0.25), ("Proje", 0.25), ("Final", 0.50)],
        ),
        (
            "CSE312",
            "Bilgisayar Ağları ve Sosyal Ağlar",
            6,
            "Zorunlu",
            [
                "OSI ve TCP/IP protokol katmanlarını karşılaştırmalı olarak açıklar",
                "IP adresleme, alt ağ oluşturma ve yönlendirme algoritmalarını uygular",
                "Sosyal ağ analizi metriklerini (merkezilik, topluluk tespiti) hesaplar",
            ],
            [("Ara Sınav", 0.20), ("Proje", 0.30), ("Final", 0.50)],
        ),
        (
            "CSE322",
            "Bulut Bilişim",
            6,
            "Zorunlu",
            [
                "Bulut hizmet modellerini (IaaS, PaaS, SaaS) ve dağıtım modellerini açıklar",
                "Apache Spark ile dağıtılmış veri işleme uygulamaları geliştirir",
                "Konteynerleştirme ve orkestrasyon teknolojilerini kullanır",
            ],
            [("Ara Sınav", 0.20), ("Proje", 0.40), ("Final", 0.40)],
        ),
        (
            "CSE332",
            "Veri Bilimi ve Yapay Zeka",
            6,
            "Zorunlu",
            [
                "Denetimli ve denetimsiz makine öğrenmesi algoritmalarını uygular",
                "Model değerlendirme, çapraz doğrulama ve aşırı öğrenmeyi yönetir",
                "Derin öğrenme modellerini bir çatı kullanarak eğitir ve değerlendirir",
            ],
            [("Ara Sınav", 0.20), ("Proje", 0.40), ("Final", 0.40)],
        ),
    ],
    "semester_7": [
        (
            "CSE403",
            "Bitirme Tasarım Projesi I",
            5,
            "Zorunlu",
            [
                "Bir mühendislik problemini tanımlar, kapsamını belirler ve çözüm planı oluşturur",
                "Literatür taraması ve gereksinim analizi yapar",
                "Proje ilerlemesini düzenli raporlar ve sunumlarla belgelendirir",
            ],
            [("Proje Teklifi", 0.30), ("Ara Rapor", 0.30), ("Final Sunum", 0.40)],
        ),
    ],
    "semester_8": [
        (
            "CSE404",
            "Bitirme Tasarım Projesi II",
            5,
            "Zorunlu",
            [
                "Tasarlanan çözümü uygular, test eder ve doğrular",
                "Proje çıktılarını teknik bir rapor halinde sunar",
                "Mühendislik etiği ve sürdürülebilirlik ilkeleri çerçevesinde değerlendirme yapar",
            ],
            [("Proje Geliştirme", 0.40), ("Final Rapor", 0.30), ("Savunma Sunumu", 0.30)],
        ),
    ],
}

PROGRAM_OUTCOME_DESCRIPTIONS = [
    (
        "Matematik, fen bilimleri ve ilgili mühendislik disiplinine özgü konularda yeterli bilgi birikimi; bu alanlardaki "
        "kuramsal ve uygulamalı bilgileri, karmaşık mühendislik problemlerinde kullanabilme becerisi."
    ),
    (
        "Karmaşık mühendislik problemlerini saptama, tanımlama, formüle etme ve çözme becerisi; bu amaçla uygun analiz ve "
        "modelleme yöntemlerini seçme ve uygulama becerisi."
    ),
    (
        "Karmaşık bir sistemi, süreci, cihazı veya ürünü gerçekçi kısıtlar ve koşullar altında, belirli gereksinimleri "
        "karşılayacak şekilde tasarlama becerisi; bu amaçla modern tasarım yöntemlerini uygulama becerisi."
    ),
    (
        "Mühendislik uygulamalarında karşılaşılan karmaşık problemlerin analizi ve çözümü için gerekli olan modern teknik ve "
        "araçları geliştirme, seçme ve kullanma becerisi; bilişim teknolojilerini etkin bir şekilde kullanma becerisi."
    ),
    (
        "Karmaşık mühendislik problemlerinin veya disipline özgü araştırma konularının incelenmesi için deney tasarlama, "
        "deney yapma, veri toplama, sonuçları analiz etme ve yorumlama becerisi."
    ),
    "Disiplin içi ve çok disiplinli takımlarda etkin biçimde çalışabilme becerisi; bireysel çalışma becerisi.",
    (
        "Türkçe sözlü ve yazılı etkin iletişim kurma becerisi; en az bir yabancı dil bilgisi; etkin rapor yazma ve yazılı "
        "raporları anlama, tasarım ve üretim raporları hazırlayabilme, etkin sunum yapabilme, açık ve anlaşılır talimat verme "
        "ve alma becerisi."
    ),
    (
        "Yaşam boyu öğrenmenin gerekliliği bilinci; bilgiye erişebilme, bilim ve teknolojideki gelişmeleri izleme ve kendini "
        "sürekli yenileme becerisi."
    ),
    (
        "Etik ilkelerine uygun davranma, mesleki ve etik sorumluluk bilinci; mühendislik uygulamalarında kullanılan "
        "standartlar hakkında bilgi"
    ),
    (
        "Proje yönetimi, risk yönetimi ve değişiklik yönetimi gibi, iş hayatındaki uygulamalar hakkında bilgi; girişimcilik, "
        "yenilikçilik hakkında farkındalık; sürdürülebilir kalkınma hakkında bilgi."
    ),
    (
        "Mühendislik uygulamalarının evrensel ve toplumsal boyutlarda sağlık, çevre ve güvenlik üzerindeki etkileri ve çağın "
        "mühendislik alanına yansıyan sorunları hakkında bilgi; mühendislik çözümlerinin hukuksal sonuçları konusunda "
        "farkındalık."
    ),
]

# ── Seed configuration ──────────────────────────────────────────────────

# Calendar year when the newest (first-year) cohort starts their first fall
# semester. All term generation and cohort offsets are derived from this.
FIRST_COHORT_START_YEAR = 2025

# Number of cohorts to generate. Cohorts are spaced one year apart; the
# oldest cohort starts (NUM_COHORTS - 1) calendar years before
# FIRST_COHORT_START_YEAR.
NUM_COHORTS = 4

STUDENTS_PER_COHORT = 20
