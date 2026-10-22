"""Sales catalog and Messenger cards restored from commit 42c51e9.
All outbound messages use main.send_message's persisted pause guard.
"""
import os, re, time
from pathlib import Path
from urllib.parse import quote
from typing import Dict,List,Optional,Tuple,Any
from types import SimpleNamespace
from contextvars import ContextVar
transport=ContextVar('sales_transport',default=None)
BASE_DIR=Path(__file__).resolve().parent
PHOTO_FOLDER=BASE_DIR/'photo'
PUBLIC_BASE_URL=os.getenv('PUBLIC_BASE_URL','https://miners-villa-bot.onrender.com').rstrip('/')
META_PAGE_ACCESS_TOKEN=True  # Credential handled only by the guarded transport in main.
def messenger_url(): return 'guarded-transport'
def _post(url, *, json, **kwargs):
    callback=transport.get()
    if callback is None: raise RuntimeError('Sales transport is not bound')
    ok=callback(json['message'])
    return SimpleNamespace(ok=ok,status_code=200 if ok else 409,text='Delivery blocked or failed')
requests=SimpleNamespace(post=_post)


PRICE_MIN = 5_500_000

PRICE_MAX = 5_800_000

SALES_PHONE = "9430-7017, 9431-7017, 9434-7017"

SALES_OFFICE = (
    "Эрдэнэт хот, 1/16-р байрны зүүн урд буланд, "
    "төв зам дагуу"
)

LOCATION_TEXT = (
    "Баян-Өндөр уулын зүүн энгэрт, "
    "Бүсийн оношилгооны төвийн ард, "
    "Медипас эмнэлгийн ард, "
    "30.8 га талбайд байрладаг."
)

PAYMENT_TEXT = (
    "30% урьдчилгаа, 40% явцын төлбөр, "
    "20% явцын төлбөр, 10% түлхүүр гардуулах үед. "
    "Явцын төлбөрт зөвхөн байрны бартер сонсоно."
)

PARKING_TEXT = (
    "Мульт хаусын Б1 болон 1-р давхарт "
    "нэгдсэн дулаан зогсоол байрлана. "
    "Зогсоолын үнэ 50,000,000 ₮."
)

UNKNOWN_TEXT = (
    "Уучлаарай, би энэ асуултыг сайн ойлгосонгүй. "
    "Та асуултаа арай дэлгэрэнгүй бичнэ үү, "
    f"эсвэл манай борлуулалтын албатай {SALES_PHONE} "
    "дугаараар холбогдон лавлах боломжтой 😊"
)

PROJECT_KNOWLEDGE = f"""
MINERS VILLA ТӨСЛИЙН БАТАЛГААТ МЭДЭЭЛЭЛ:

1. ТӨСЛИЙН НЭР
Miners Villa.

2. БАЙРШИЛ
{LOCATION_TEXT}

3. ТАЛБАЙ
Нийт 30.8 га талбайд байрладаг.

4. М² ҮНЭ
М² үнэ:
{PRICE_MIN:,} - {PRICE_MAX:,} ₮.
136.42 м² хүртэлх Мульт хаусны үнэ 5,800,000 ₮-аас эхэлнэ. 136.42 м² түүнээс дээш талбайн м² үнэ 5,500,000 ₮.

5. ЗАГВАРУУД
Таун хаус:
- 213.33 м²
- 267.48 м²

Мульт хаус:
- 125.21 м² - 198.52 м² хүртэл.

Сингл болон Твин загварууд дууссан.

6. ТӨЛБӨРИЙН НӨХЦӨЛ
{PAYMENT_TEXT}

7. ЗОГСООЛ
{PARKING_TEXT}

8. ДЭД БҮТЭЦ
- Төвийн дулаан
- Цахилгаан
- Цэвэр ус
- Бохирын шугам

9. ТӨСЛИЙН ОНЦЛОГ
- 24 цагийн харуул хамгаалалт
- 2.2 км хүрээлсэн хашаа
- Автомашингүй ногоон бүс
- Байгалийн гэрэлтүүлэг сайтай
- Насны онцлогт тохирсон 4 төрлийн тоглоомын талбай
- Ойролцоогоор 400 автомашины нэгдсэн дулаан зогсоол
- 30.8 га талбайн 60% нь ногоон байгууламж

10. АШИГЛАЛТАД ОРОХ
2026 оны өвөл дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна.
Яг ашиглалтад орох огноог зохиож хэлж болохгүй. Хотхон нийтээр ашиглалтад орох хугацаа 2027 оны 4 дүгээр улиралд.

11. БОРЛУУЛАЛТЫН УТАС
{SALES_PHONE}

12. БОРЛУУЛАЛТЫН ОФФИС
{SALES_OFFICE}

13. Үйлчилгээний талбай
Multi House төслийн бүх блокийн B1 давхарт урагшаа харсан, тусдаа хаалгатай үйлчилгээний талбай гарна. Одоогоор үнэ батлагдаагүй байгаа. Хэрэв хэрэглэгч асуувал "Үнэ батлагдмагц эргэн мэдээлэл өгөх тул та холбогдох дугаараа үлдээнэ үү" гэж эелдгээр асууж, дугаарыг нь авч бүртгэнэ.

14. Гадна фасад, дулаалга
Дулаан алдагдлыг бууруулах EPS хөөсөн дулаалгатай бөгөөд гадна өнгөлгөө нь чулуун гадаргуутай Fiber хавтангаар хийгдсэн. Энэ нь дулаахан, үзэмжтэйгээс гадна цаг уурын нөлөөнд маш тэсвэртэй.

15. Хотхонтой ойролцоо сургууль цэцэрлэг
Төслийн зүүн буланд 640 хүүхдийн улсын сургууль, 280 хүүхдийн улсын цэцэрлэг баригдаж байна.
Сургууль, цэцэрлэгийн бүтээн байгуулалт нь Эрдэнэт үйлдвэрийн хөрөнгө оруулалтаар хэрэгжиж байгаа бөгөөд одоогийн төлөвлөгөөгөөр 2028 онд ашиглалтад оруулахаар ажиллаж байгаа.

16. Террасны талбай
Манай хаусны айл бүр хувийн террастай тул та гэрийнхээ орон зайг зөвхөн дотор талбайгаар хязгаарлахгүй. Амрах, хооллох, хүүхдүүдтэйгээ цаг өнгөрүүлэх, зочдоо хүлээн авах гээд хүссэнээрээ тохижуулж ашиглах боломжтой.
Хамгийн таатай нь террасны талбайн м²-ийн үнийг ердөө 30%-иар тооцно. Ингэснээр та илүү том, илүү тав тухтай хувийн орон зайг илүү боломжийн нөхцөлөөр авах боломжтой.

"""

IMAGE_LIBRARY = {
    "GENERAL": "general",
    "GENERAL_PLAN": "general_plan",

    "GREEN_GARDEN": "Green_garden",
    "LANDSCAPING": "landscaping",
    "RELAXATION_AREA": "relaxation_area",

    "SPORTS_AREA_0_5": "sports_area_0-5",
    "SPORTS_AREA_9_13": "sports_area_9-13",
    "SPORTS_AREA_13_16": "sports_area_13-16",
    "SPORTS_AREA_PLAN": "sports_area_plan",

    "MULT": "mult",
    "MULT_PARKING_SPACE": "mult_parking_space",
    "MULT_PARKING_SPACE_1": "mult_parking_space_1",

    "MULT_100": "mult_100",
    "MULT_116": "mult_116",
    "MULT_120": "mult_120",
    "MULT_125": "mult_125",
    "MULT_126": "mult_126",
    "MULT_126_32": "mult_126_32",
    "MULT_136": "mult_136",
    "MULT_178": "mult_178",
    "MULT_189": "mult_189",
    "MULT_189_64": "mult_189_64",
    "MULT_192": "mult_192",
    "MULT_198": "mult_198",

    "TOWNHOUSE_212": "townhouse_212",
    "TOWNHOUSE_212_1": "townhouse_212_1",
    "TOWNHOUSE_266": "townhouse_266",
    "TOWNHOUSE_266_1": "townhouse_266_1",
}

IMAGE_KEYS = set(IMAGE_LIBRARY.keys())

def normalize_text(text: str) -> str:

    if not text:
        return ""

    text = str(text).lower().strip()

    # м² болон ² тэмдэгтийг 2 болгон хэвийн болгоно.
    # Ингэснээр "43м²" ба "43м2" ижил танигдана.
    text = text.replace("²", "2")

    # punctuation-ийг space болгоно
    text = re.sub(
        r"[^\w\s.,]",
        " ",
        text,
        flags=re.UNICODE
    )

    # Монгол үсгийн зарим түгээмэл бичлэгийн хувилбар
    replacements = {
        "ё": "е",
        "ү": "у",
        "ө": "о",
        "v": "u",
        "w": "v",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new
        )

    # Түгээмэл typo
    word_replacements = {
        "mdll": "medeelel",
        "mdlel": "medeelel",
        "mdeelel": "medeelel",
        "brshil": "bairshil",
        "tlbur": "tulbur",
        "zgsol": "zogsool",
        "uts": "utas",
        "mkv": "m2",
        "кв": "м2",
    }

    words = text.split()

    normalized_words = [
        word_replacements.get(
            word,
            word
        )
        for word in words
    ]

    return " ".join(
        normalized_words
    ).strip()

def match_any(
    keywords: List[str],
    normalized_text: str
) -> bool:

    return any(
        normalize_text(keyword) in normalized_text
        for keyword in keywords
    )

def resolve_photo_file(
    stem: str
) -> Optional[Path]:

    if not PHOTO_FOLDER.exists():
        return None

    target_stem = stem.lower()

    # exact stem
    for file in PHOTO_FOLDER.iterdir():

        if not file.is_file():
            continue

        if file.stem.lower() == target_stem:
            return file

    # exact filename fallback
    for file in PHOTO_FOLDER.iterdir():

        if not file.is_file():
            continue

        if file.name.lower() == target_stem:
            return file

    return None

def get_public_image_url(
    filename: str
) -> str:

    return (
        f"{PUBLIC_BASE_URL}/photo/"
        f"{quote(filename, safe='')}"
    )

DEFAULT_BUTTONS = [
    {
        "content_type": "text",
        "title": "🏠 Загварууд",
        "payload": "PAYLOAD_MODEL"
    },
    {
        "content_type": "text",
        "title": "💰 Үнэ",
        "payload": "PAYLOAD_PRICE"
    },
    {
        "content_type": "text",
        "title": "📍 Байршил",
        "payload": "PAYLOAD_LOCATION"
    },
    {
        "content_type": "text",
        "title": "☎️ Холбоо барих",
        "payload": "PAYLOAD_CONTACT"
    }
]

MODEL_BUTTONS = [
    {
        "content_type": "text",
        "title": "🏡 Таун хаус",
        "payload": "PAYLOAD_TOWN"
    },
    {
        "content_type": "text",
        "title": "🏢 Мульт хаус",
        "payload": "PAYLOAD_MULT"
    },
    {
        "content_type": "text",
        "title": "💰 Үнэ",
        "payload": "PAYLOAD_PRICE"
    }
]

def direct_image_router(
    user_text: str,
    sender_id: str = ""
) -> Optional[List[str]]:

    t = normalize_text(
        user_text
    )

    mult_image_map = {

        "126.32": "MULT_126_32",
        "125.21": "MULT_125",
        "120.85": "MULT_120",

        "116": "MULT_116",
        "100.77": "MULT_100",

        "136.42": "MULT_136",
        "178.39": "MULT_178",

        "189.64": "MULT_189_64",
        "189.52": "MULT_189",

        "192.25": "MULT_192",
        "198.52": "MULT_198",

        "126": "MULT_126",
        "125": "MULT_125",
        "120": "MULT_120",
        "100": "MULT_100",
        "136": "MULT_136",
        "178": "MULT_178",
        "189": "MULT_189",
        "192": "MULT_192",
        "198": "MULT_198",
        "116": "MULT_116",
    }

    # Specific м² first
    for size in sorted(
        mult_image_map.keys(),
        key=len,
        reverse=True
    ):

        escaped = re.escape(size)

        pattern = (
            rf"(?<!\d){escaped}"
            rf"(?!\d)"
        )

        if re.search(
            pattern,
            t
        ):
            return [
                "MULT",
                mult_image_map[size]
            ]

    # Townhouse sizes
    if re.search(
        r"(?<!\d)(212|213)(?!\d)",
        t
    ):

        return [
            "TOWNHOUSE_212",
            "TOWNHOUSE_212_1",
            "GENERAL_PLAN"
        ]

    if re.search(
        r"(?<!\d)(266|267)(?!\d)",
        t
    ):

        return [
            "TOWNHOUSE_266",
            "TOWNHOUSE_266_1",
            "GENERAL_PLAN"
        ]

    # Townhouse
    if match_any(
        [
            "таун хаус",
            "таунхаус",
            "таун",
            "taun",
            "townhouse"
        ],
        t
    ):

        return [
            "TOWNHOUSE_212_1",
            "TOWNHOUSE_212",
            "TOWNHOUSE_266_1",
            "TOWNHOUSE_266"
        ]

    # Multi-house
    if match_any(
        [
            "мульт хаус",
            "мультхаус",
            "мульт",
            "mult",
            "мулт"
        ],
        t
    ):

        return [
            "MULT",
            "MULT_100",
            "MULT_116",
            "MULT_120",
            "MULT_125",
            "MULT_126",
            "MULT_126_32",
            "MULT_136",
            "MULT_178",
            "MULT_189",
            "MULT_189_64",
            "MULT_192",
            "MULT_198"
        ]

    # Parking
    if match_any(
        [
            "зогсоол",
            "гараж",
            "гараш",
            "гарааш",
            "zogsool",
            "garaash",
            "garaj"
        ],
        t
    ):

        return [
            "MULT_PARKING_SPACE",
            "MULT_PARKING_SPACE_1"
        ]

    return None

def direct_faq_router(
    user_text: str,
    sender_id: str = ""
) -> Optional[
    Tuple[str, Any, Optional[List[Dict]]]
]:

    t = normalize_text(
        user_text
    )

    # -----------------------------------------------------
    # 1. Greeting
    # -----------------------------------------------------

    greetings = {
    "сайн уу",
    "сайн байна уу",
    "hello",
    "hi",
    "мэнд",
    "get started",
    "start",
    "snu",
    "сну",
    "сээноо",
    "эхлэх",
    "хай",
    "bnu",
    "hello?",
    "сн бну",
    "мэдээлэл авий"
}


    if t in greetings:

        reply = (
            "Сайн байна уу? 😊\n\n"
            "Тав тух, үнэ цэнийн илэрхийлэл болсон "
            "'Miners Villa' төслийн албан ёсны "
            "чатботод тавтай морил!\n\n"
            "Урьд нь 'Уурхайчин-3' нэртэй байсан "
            "манай төсөл илүү өргөжиж, хүн бүхэнд "
            "нээлттэй амины орон сууцны цогцолбор "
            "хотхон болсон.\n\n"
            "Танд ямар мэдээлэл хэрэгтэй вэ? 👇"
        )

        return (
            reply,
            True,
            None
        )

    # -----------------------------------------------------
    # 2. Calculation clarification
    # -----------------------------------------------------
    # Бартерын байрны мэдээллийг Miners Villa-ийн м² үнээр
    # автоматаар үнэлсэн мэт ойлголт өгөхөөс сэргийлнэ.
    calculation_question_keywords = [
        "энэ тооцооллыг хэн хийсэн",
        "тооцооллыг хэн хийсэн",
        "энэ тооцоог хэн хийсэн",
        "тооцоог хэн хийсэн",
        "энэ тооцоо зөв үү",
        "тооцоо зөв үү",
        "ene tootsоо",
        "hen hiisen",
    ]

    if match_any(calculation_question_keywords, t):
        reply = (
            "Энэ тооцоог Mina чатбот автоматаар жишээ болгон бодож үзүүлсэн юм 😊\n\n"
            "Бартерт санал болгож буй байрны бодит үнэлгээ биш тул эцсийн дүнг борлуулалтын менежер шалгаж тогтооно."
        )
        return (reply, False, DEFAULT_BUTTONS)

    # -----------------------------------------------------
    # 3. Model selection
    # -----------------------------------------------------

    # Зөвхөн загвар сонголт асуусан үед MODEL carousel ажиллана.
    # "м2", "мкв", "хэмжээ" зэрэг үгсийг энд оруулахгүй.
    # Учир нь бартерын саналд талбайн мэдээлэл маш түгээмэл ордог.
    model_keywords = [
        "сонголт",
        "загвар",
        "songolt",
        "zagvar"
    ]

    if match_any(
        model_keywords,
        t
    ):

        reply = (
            "Манай төслийн загварын сонголтууд "
            "(Таун болон Мульт хаус)-ыг доорх "
            "картуудаас үзнэ үү 👇"
        )

        return (
            reply,
            "MODEL",
            None
        )

    # -----------------------------------------------------
    # 3. Price
    # -----------------------------------------------------

    price_keywords = [
        "үнэ", "үнийн", "үнэтэй", "м2 үнэ", "une", "vne", "xed", "hed", "үнэ террас"
    ]
    if match_any(price_keywords, t):
        reply = (
            f"💰 Манай хаусны м² үнэ {PRICE_MIN:,}–{PRICE_MAX:,} ₮ байна.\n\n"
            "✨ Мөн манай хаус бүр хувийн террастай бөгөөд "
            "террасны талбайн м²-ийн үнийг ердөө 30%-иар тооцно! Энэ нь хувийн орон зайгаа "
            "боломжийн үнээр авах таатай боломж юм.\n\n"
            f"☎️ Лавлах: {SALES_PHONE}"
        )
        return (reply, False, MODEL_BUTTONS)

    # -----------------------------------------------------
    # 4. Location
    # -----------------------------------------------------

    location_keywords = [
        "байршил", "хаана байдаг", "хаана вэ", "bairshil", "haana", "байршил сургууль", "Bairshil", "байрлал", "Байрлал"
    ]
    if match_any(location_keywords, t):
        reply = (
            f"📍 Байршил: {LOCATION_TEXT}\n\n"
            "🏫 Сургууль, цэцэрлэг: Төслийн зүүн буланд 640 хүүхдийн улсын сургууль, "
            "280 хүүхдийн улсын цэцэрлэг баригдаж байгаа ба 2028 онд ашиглалтад орно.\n\n"
            f"☎️ Дэлгэрэнгүй: {SALES_PHONE}"
        )
        return (reply, False, DEFAULT_BUTTONS)
    
    # -----------------------------------------------------
    # 5. Phone
    # -----------------------------------------------------

    phone_keywords = [
        "утас",
        "дугаар",
        "холбоо барих",
        "залгах",
        "utas",
        "dugaar"
    ]

    if (
        match_any(phone_keywords, t)
        and not match_any(["оффис"], t)
    ):

        return (
            f"☎️ Манай борлуулалтын утас: "
            f"{SALES_PHONE} 😊",
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 6. General information
    # -----------------------------------------------------

    info_keywords = [
        "мэдээлэл",
        "дэлгэрэнгүй",
        "танилцуулга",
        "medeelel",
        "taniltsuulga"
    ]

    if (
        match_any(info_keywords, t)
        and len(t.split()) <= 5
    ):

        reply = (
            "🏡 Miners Villa төсөл:\n\n"
            "📍 Байршил: Баян-Өндөр уулын "
            "зүүн энгэрт.\n"
            "🏗 Дэд бүтэц: Төвийн дулаан, "
            "цахилгаан, цэвэр, бохирт холбогдсон.\n"
            "🌳 Эко орчин: 30.8 га талбай.\n"
            "🏠 Сонголт: Таун болон Мульт хаус.\n"
            f"💰 М² үнэ: {PRICE_MIN:,}–"
            f"{PRICE_MAX:,} ₮.\n\n"
            f"☎️ Дэлгэрэнгүй: {SALES_PHONE}"
        )

        return (
            reply,
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 7. Features
    # -----------------------------------------------------

    features_keywords = [
        "онцлог",
        "давуу тал",
        "ялгаа",
        "ontslog",
        "davuu tal"
    ]

    if match_any(
        features_keywords,
        t
    ):

        reply = (
            "🌳 Төслийн онцлог, давуу талууд:\n\n"
            "✅ Найдвартай дэд бүтэц\n"
            "✅ Төвийн бүрэн холболт\n"
            "✅ 24 цагийн харуул хамгаалалт\n"
            "✅ 2.2 км хүрээлсэн хашаа\n"
            "✅ Автомашингүй ногоон бүс\n"
            "✅ Байгалийн гэрэлтүүлэг сайтай\n"
            "✅ Насны онцлогт тохирсон "
            "4 төрлийн тоглоомын талбай\n"
            "✅ Ойролцоогоор 400 автомашины "
            "нэгдсэн дулаан зогсоол"
        )

        return (
            reply,
            False,
            DEFAULT_BUTTONS
        )
    
    # -----------------------------------------------------
    # 9. Payment
    # -----------------------------------------------------

    payment_keywords = [
        "төлбөр",
        "төлбөрийн нөхцөл",
        "урьдчилгаа",
        "tulbur",
        "urdchilgaa"
    ]

    if match_any(
        payment_keywords,
        t
    ):

        return (
            f"💰 {PAYMENT_TEXT}",
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 10. Parking
    # -----------------------------------------------------

    parking_keywords = [
        "зогсоол", "гарааш", "гараж", "б1", "zogsool", "garaash", "үйлчилгээ зогсоол", "үйлчилгээний", "үйлчилгээ", "Худалдаа үйлчилгээ", "Худалдаа"
    ]
    if match_any(parking_keywords, t):
        reply = (
            f"🚗 Зогсоол: {PARKING_TEXT}\n\n"
            "🏬 Үйлчилгээний талбай: Multi House төслийн бүх блокийн B1 давхарт "
            "урагшаа харсан, тусдаа хаалгатай үйлчилгээний талбай гарна. (Одоогоор үнэ батлагдаагүй байгаа)\n\n"
            "Та дугаараа үлдээвэл үнэ батлагдмагц эргэн мэдээлэл өгөх болно 😊"
        )
        return (reply, False, DEFAULT_BUTTONS)

    # -----------------------------------------------------
    # 11. Completion
    # -----------------------------------------------------

    completion_keywords = [
        "ашиглалт",
        "хэзээ орох",
        "хэзээ ашиглалтад",
        "ashiglalt",
        "hezee oroh",
        "ashiglaltand"
    ]

    if match_any(
        completion_keywords,
        t
    ):

        reply = (
            "2026 оны өвөл гэхэд дотоод заслын "
            "ажлыг эхлүүлэхээр ажиллаж байна.\n\n"
            "Одоогийн төлөвлөгөө ёсоор Miners Villa хотхон нийтээр ашиглалтад орох хугацаа 2027 оны 4 дүгээр улиралд.\n\n"
            "Шинэчлэгдсэн мэдээллийг "
            f"{SALES_PHONE} дугаараас лавлаарай 😊"
        )

        return (
            reply,
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 12. Visit / Office
    # -----------------------------------------------------

    visit_keywords = [
        "очиж",
        "үзэх",
        "узэх",
        "харж болох",
        "харах",
        "уулзах",
        "оффис",
        "очиж харах"
    ]

    if match_any(
        visit_keywords,
        t
    ):

        reply = (
            "Мэдээж 😊 Та манай борлуулалтын "
            "оффист хүрэлцэн ирж төслийн "
            "дэлгэрэнгүй мэдээлэл болон "
            "загвартай танилцах боломжтой.\n\n"
            f"📍 Хаяг: {SALES_OFFICE}\n"
            f"☎️ Утас: {SALES_PHONE}\n\n"
            f"Хэрэв та төслийн талбайтай танилцахыг хүсвэл манай борлуулалтын албатай {SALES_PHONE} дугаараар холбогдон цаг товлон очиж үзэх боломжтой."
        )

        return (
            reply,
            False,
            DEFAULT_BUTTONS
        )
    # 13. SINGLE / TWIN HOUSE - SOLD OUT
    sold_out_keywords = [
        "сингл",
        "сингл хаус",
        "single",
        "single house",
        "твин",
        "твин хаус",
        "twin",
        "twin house",
    ]

    if match_any(sold_out_keywords, t):
        reply = (
            "🏡 Сингл болон Твин хаусны борлуулалт дууссан байна.\n\n"
            "Одоогоор Miners Villa төслөөс:\n"
            "🏠 Таун хаус\n"
            "🏢 Мульт хаус\n"
            "сонголтууд үлдсэн байгаа. 😊\n\n"
            f"☎️ Дэлгэрэнгүй мэдээлэл: {SALES_PHONE}"
        )
        return (
            reply, 
            False, 
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 14. Return nothing
    # -----------------------------------------------------

    return None

def send_fb_message(
    recipient_id: str,
    text: str,
    quick_replies: Optional[List[Dict]] = None
) -> bool:

    if not META_PAGE_ACCESS_TOKEN:
        print(
            "⚠️ META_PAGE_ACCESS_TOKEN байхгүй."
        )
        return False

    if not recipient_id:
        return False

    if not text:
        text = UNKNOWN_TEXT

    message_data = {
        "text": str(text)
    }

    if quick_replies:
        message_data[
            "quick_replies"
        ] = quick_replies

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": message_data
    }

    try:

        response = requests.post(
            messenger_url(),
            json=payload,
            headers={
                "Content-Type":
                    "application/json"
            },
            timeout=15
        )

        if not response.ok:

            print(
                "❌ Facebook text API error:",
                response.status_code,
                response.text
            )

            return False

        print(
            "✅ Facebook text sent:",
            response.status_code
        )

        return True

    except Exception as exc:

        print(
            "❌ Error sending text:",
            repr(exc)
        )

        return False

def send_carousel_menu(
    recipient_id: str,
    quick_replies: Optional[List[Dict]] = None
) -> bool:

    if not META_PAGE_ACCESS_TOKEN:
        return False

    # Зургуудын URL
    card1_url = f"{PUBLIC_BASE_URL}/photo/general.png?v=3"
    card2_url = f"{PUBLIC_BASE_URL}/photo/townhouse_266.png?v=1" 
    card3_url = f"{PUBLIC_BASE_URL}/photo/general_plan.png?v=4"

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        # --- КАРТ 1 ---
                        {
                            "title": "🌳 Miners Villa - Цогцолбор хотхон",
                            "subtitle": "30.8 га талбайд сүндэрлэх, 60% ногоон байгууламж бүхий эко орчин.",
                            "image_url": card1_url,
                            "buttons": [
                                {"type": "postback", "title": "📍 Байршил & Сургууль", "payload": "PAYLOAD_LOCATION_SCHOOL"},
                                {"type": "postback", "title": "✨ Хотхоны онцлог", "payload": "PAYLOAD_FEATURES"},
                                {"type": "postback", "title": "🏢 Үйлчилгээ & Зогсоол", "payload": "PAYLOAD_SERVICES"}
                            ]
                        },
                        # --- КАРТ 2 ---
                        {
                            "title": "🏠 Загварын сонголт & Үнэ",
                            "subtitle": "Таун болон Мульт хаусны сонголтууд, хувийн террасны гайхалтай шийдэлтэй.",
                            "image_url": card2_url,
                            "buttons": [
                                {"type": "postback", "title": "🏡 Таун хаус үзэх", "payload": "PAYLOAD_TOWN"},
                                {"type": "postback", "title": "🏢 Мульт хаус үзэх", "payload": "PAYLOAD_MULT"},
                                {"type": "postback", "title": "💰 Үнэ & Террас", "payload": "PAYLOAD_PRICE_TERRACE"}
                            ]
                        },
                        # --- КАРТ 3 ---
                        {
                            "title": "🤝 Худалдан авах нөхцөл",
                            "subtitle": "Төлбөрийн нөхцөл болон ашиглалтад орох төлөвлөгөөтэй танилцах.",
                            "image_url": card3_url,
                            "buttons": [
                                {"type": "postback", "title": "💳 Төлбөрийн нөхцөл", "payload": "PAYLOAD_PAYMENT"},
                                {"type": "postback", "title": "⏳ Хэзээ ашиглалтад орох?", "payload": "PAYLOAD_COMPLETION"},
                                {"type": "postback", "title": "☎️ Утас & Оффис", "payload": "PAYLOAD_CONTACT"}
                            ]
                        }
                    ]
                }
            }
        }
    }

    if quick_replies:
        payload["message"]["quick_replies"] = quick_replies

    try:
        response = requests.post(
            messenger_url(),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )

        if not response.ok:
            print("❌ General carousel error:", response.status_code, response.text)
            return False

        print("✅ General carousel sent:", response.status_code)
        return True

    except Exception as exc:
        print("❌ Error sending general carousel:", repr(exc))
        return False

def send_model_carousel(
    recipient_id: str,
    quick_replies: Optional[List[Dict]] = None
) -> bool:

    if not META_PAGE_ACCESS_TOKEN:
        return False

    town_url = (
        f"{PUBLIC_BASE_URL}/photo/"
        "townhouse_266.png?v=1"
    )

    mult_url = (
        f"{PUBLIC_BASE_URL}/photo/"
        "mult.png?v=1"
    )

    payload = {
        "recipient": {
            "id": recipient_id
        },

        "message": {
            "attachment": {

                "type": "template",

                "payload": {

                    "template_type": "generic",

                    "elements": [

                        {
                            "title":
                                "🏡 ТАУН ХАУС (Townhouse)",

                            "subtitle":
                                "Сонголт: 213.33 м², "
                                "267.48 м²\n"
                                "Үнэ: м² нь 5.5М - "
                                "5.8М ₮",

                            "image_url":
                                town_url,

                            "buttons": [

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "🏡 Таун хаус үзэх",

                                    "payload":
                                        "PAYLOAD_TOWN"
                                },

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "💰 Үнэ харах",

                                    "payload":
                                        "PAYLOAD_PRICE"
                                }
                            ]
                        },

                        {
                            "title":
                                "🏢 МУЛЬТ ХАУС (Multi-family)",

                            "subtitle":
                                "Сонголт: 125 м² - "
                                "198 м² хүртэл\n"
                                "Үнэ: м² нь 5.5М - "
                                "5.8М ₮",

                            "image_url":
                                mult_url,

                            "buttons": [

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "🏢 Мульт хаус үзэх",

                                    "payload":
                                        "PAYLOAD_MULT"
                                },

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "☎️ Холбоо барих",

                                    "payload":
                                        "PAYLOAD_CONTACT"
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }

    if quick_replies:
        payload[
            "message"
        ][
            "quick_replies"
        ] = quick_replies

    try:

        response = requests.post(
            messenger_url(),
            json=payload,
            headers={
                "Content-Type":
                    "application/json"
            },
            timeout=15
        )

        if not response.ok:

            print(
                "❌ Model carousel error:",
                response.status_code,
                response.text
            )

            return False

        print(
            "✅ Model carousel sent:",
            response.status_code
        )

        return True

    except Exception as exc:

        print(
            "❌ Error sending model carousel:",
            repr(exc)
        )

        return False

def send_images_by_keys(
    recipient_id: str,
    image_keys: List[str],
    quick_replies: Optional[List[Dict]] = None
) -> bool:

    if not image_keys:
        return False

    if not META_PAGE_ACCESS_TOKEN:
        print(
            "⚠️ META_PAGE_ACCESS_TOKEN байхгүй."
        )
        return False

    elements = []
    seen = set()

    for key in image_keys:

        if key in seen:
            continue

        if key not in IMAGE_LIBRARY:
            print(
                f"⚠️ Unknown image key: {key}"
            )
            continue

        seen.add(key)

        stem = IMAGE_LIBRARY[key]

        local_path = resolve_photo_file(
            stem
        )

        if not local_path:
            print(
                "⚠️ Зураг олдсонгүй:",
                key,
                stem
            )
            continue

        public_url = get_public_image_url(
            local_path.name
        )

        print(
            f"📸 Зураг олдлоо: "
            f"{key} -> {public_url}"
        )

        elements.append({

            "title":
                "Miners Villa - "
                + key.replace("_", " "),

            "image_url":
                public_url,

            "buttons": [

                {
                    "type":
                        "web_url",

                    "url":
                        public_url,

                    "title":
                        "🔍 Томруулж харах"
                }
            ]
        })

    if not elements:

        print(
            "❌ Илгээх боломжтой зураг олдсонгүй."
        )

        send_fb_message(
            recipient_id,
            "⚠️ Уучлаарай, одоогоор "
            "энэ загварын зургууд "
            "системд оруулаагүй байна.",
            quick_replies
        )

        return False

    # Messenger generic template нэг message-д
    # хамгийн ихдээ 10 элемент явуулахад найдвартай.
    chunks = [
        elements[i:i + 10]
        for i in range(
            0,
            len(elements),
            10
        )
    ]

    success = True

    for index, chunk in enumerate(chunks):

        payload = {

            "recipient": {
                "id": recipient_id
            },

            "message": {

                "attachment": {

                    "type":
                        "template",

                    "payload": {

                        "template_type":
                            "generic",

                        "elements":
                            chunk
                    }
                }
            }
        }

        if (
            quick_replies
            and index == len(chunks) - 1
        ):

            payload[
                "message"
            ][
                "quick_replies"
            ] = quick_replies

        try:

            response = requests.post(
                messenger_url(),
                json=payload,
                headers={
                    "Content-Type":
                        "application/json"
                },
                timeout=15
            )

            print(
                f"📡 Facebook image API "
                f"[{index + 1}/{len(chunks)}]: "
                f"{response.status_code}"
            )

            if not response.ok:

                success = False

                print(
                    "❌ Image API error:",
                    response.text
                )

        except Exception as exc:

            success = False

            print(
                "❌ Зураг илгээхэд алдаа:",
                repr(exc)
            )

        time.sleep(0.05)

    return success

def direct_area_price_router(
    user_text: str,
    sender_id: str = ""
) -> Optional[Tuple[str, Any, Optional[List[Dict]]]]:
    """Талбай + үнэ асуусан мессежийг зурагнаас өмнө шууд бодож хариулна."""

    t = normalize_text(user_text)

    if not t:
        return None

    # 198 м² / 198м2 / 198мкв / 198 мкв / 198m2 гэх мэт талбайг танина.
    area_match = re.search(
        r"(?<![0-9])\d+(?:[.,]\d+)?\s*(?:м2|мкв|m\s*2|mkv)\b",
        t
    )

    if not area_match:
        return None

    # Зөвхөн талбай бичсэн мессежийг үнэ гэж автоматаар үзэхгүй.
    # "хэд болох", "үнэ", "орчим", "тооц", "hed", "boloh" гэх мэт асуултын хэллэг хэрэгтэй.
    price_question_keywords = [
        "үнэ",
        "үнийн",
        "хэд болох",
        "хэд орчим",
        "хэд вэ",
        "болох вэ",
        "нийт хэд",
        "тооцоол",
        "тооцох",
        "тооцвол",
        "үнэлгээ",
        "une",
        "vne",
        "hed",
        "boloh",
        "orjim",
        "orchoom",
        "toos",
        "tootsool",
        "tootsvol",
    ]

    if not match_any(price_question_keywords, t):
        return None

    raw_area = area_match.group(0)
    number_match = re.search(r"\d+(?:[.,]\d+)?", raw_area)
    if not number_match:
        return None

    try:
        area = float(number_match.group(0).replace(",", "."))
    except ValueError:
        return None

    if area <= 0 or area > 1000:
        return None

    # Төслийн баталгаатай мэдээлэл:
    # 136.42 м² хүртэлх Multi House: 5.8 сая ₮/м²
    # 136.42 м²-ээс дээш: 5.5 сая ₮/м²
    # Хэрэглэгч Multi House гэж тодорхойлсон бол яг энэ дүрмийг хэрэглэнэ.
    is_multi = match_any(
        [
            "мульт",
            "мульт хаус",
            "мультхаус",
            "mult",
        ],
        t
    )

    if is_multi:
        price_per_m2 = 5_800_000 if area <= 136.42 else 5_500_000
        total = area * price_per_m2

        reply = (
            f"🏢 {area:,.2f} м² Мульт хаусыг манай м² үнээр "
            f"ойролцоогоор {total:,.0f} ₮ гэж тооцно.\n\n"
            f"М² үнэ: {price_per_m2:,.0f} ₮. "
            "Эцсийн үнэ нь тухайн сонголтын нөхцөлөөс шалтгаалж баталгаажна."
        )
        return (reply, False, MODEL_BUTTONS)

    # Таун болон загвар тодорхойгүй үед яг нэг м² үнэ зохиохгүй.
    # Харин одоогийн баталгаатай хүрээгээр ойролцоолно.
    if match_any(
        [
            "таун",
            "таун хаус",
            "таунхаус",
            "townhouse",
        ],
        t
    ):
        min_total = area * PRICE_MIN
        max_total = area * PRICE_MAX

        reply = (
            f"🏡 {area:,.2f} м² Таун хаус нь одоогийн м² үнийн хүрээгээр "
            f"ойролцоогоор {min_total:,.0f}–{max_total:,.0f} ₮ байна.\n\n"
            f"Манай хаусны м² үнэ {PRICE_MIN:,.0f}–{PRICE_MAX:,.0f} ₮. "
            f"Эцсийн үнийг борлуулалтын менежер баталгаажуулна."
        )
        return (reply, False, MODEL_BUTTONS)

    # "198 м² хэд вэ?" гэх мэт загвар нь тодорхойгүй үед хүрээгээр бодно.
    min_total = area * PRICE_MIN
    max_total = area * PRICE_MAX

    reply = (
        f"🏠 {area:,.2f} м² талбайг одоогийн м² үнийн хүрээгээр "
        f"ойролцоогоор {min_total:,.0f}–{max_total:,.0f} ₮ гэж тооцож болно.\n\n"
        f"Манай хаусны м² үнэ {PRICE_MIN:,.0f}–{PRICE_MAX:,.0f} ₮."
    )
    return (reply, False, MODEL_BUTTONS)

PAYLOAD_MAP = {
    "GET_STARTED": "сайн уу",
    "PAYLOAD_PRICE": "үнэ",
    "PAYLOAD_INFO": "танилцуулга",
    "PAYLOAD_MODEL": "сонголт",
    "PAYLOAD_LOCATION": "байршил",
    "PAYLOAD_FEATURES": "онцлог",
    "PAYLOAD_CONTACT": "утас",
    "PAYLOAD_TOWN": "таун хаус",
    "PAYLOAD_MULT": "мульт хаус",
    
    # --- ШИНЭЭР НЭМЭГДСЭН ТОВЧЛУУРУУДЫН УТГА ---
    "PAYLOAD_LOCATION_SCHOOL": "байршил сургууль",
    "PAYLOAD_SERVICES": "үйлчилгээ зогсоол",
    "PAYLOAD_PRICE_TERRACE": "үнэ террас",
    "PAYLOAD_PAYMENT": "төлбөр нөхцөл",
    "PAYLOAD_COMPLETION": "ашиглалт"
}
