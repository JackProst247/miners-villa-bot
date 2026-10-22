"""Sales navigation and explicit request routing, independent of network services."""
import re
import sales
from core import has, norm

CUSTOMER_BUTTONS=[
 {'content_type':'text','title':'📧 И-мэйл бүртгүүлэх','payload':'EMAIL'},
 {'content_type':'text','title':'👷 Инженертэй уулзах','payload':'ENGINEER'},
 {'content_type':'text','title':'👤 Ажилтантай ярих','payload':'HUMAN'},
 {'content_type':'text','title':'🏠 Үндсэн цэс','payload':'GET_STARTED'},
]
DEFAULT_BUTTONS=sales.DEFAULT_BUTTONS+[
 {'content_type':'text','title':'👤 Ажилтантай ярих','payload':'HUMAN'},
 {'content_type':'text','title':'📧 И-мэйл бүртгүүлэх','payload':'EMAIL'},
]
MULT_SIZES='100.77, 116, 120.85, 125.21, 126.32, 136.42, 178.39, 189.52, 189.64, 192.25, 198.52'
TOWN_SIZES='213.33, 267.48'

def clean(text):
    text=norm(text).strip(' ?!.,😊')
    text=re.sub(r'\b(?:mulit|multi|mult)\s*(?:house|haus)?\b','мульт хаус',text)
    return text

def explicit_request(text):
    t=clean(text)
    if has(t,['и-мэйл','имэйл','email','e-mail','мэйл']): return 'email'
    if has(t,['инженер','injener','өрөөний хуваалт','хана өөрчл']): return 'engineer'
    if has(t,['гомдол','gomdol']): return 'complaint'
    if has(t,['ажилтантай','админ','менежертэй','huntei','ajiltan','admin','managertei']): return 'human'
    if has(t,['очиж','очих','очмоор','талбайтай','цаг тов','ochij','ochih','очоод','уулзалт']): return 'viewing'
    if has(t,['байраа өг','машинаа өг','бартер санал','бартерт өг','barter hi','оролцуулмаар']): return 'barter'
    if has(t,['гэрээ байгуулмаар','захиалга өг','захиалмаар']): return 'contract'
    return None

def route(text,profile=None):
    profile=profile or {}
    t=clean(text)
    buttons=DEFAULT_BUTTONS
    if t in {'сайн уу','сайн байна уу','hello','hi','snu','сну','мэнд','эхлэх','үндсэн цэс','start'}:
        return {'reply':'Сайн байна уу! 😊 Miners Villa-д тавтай морил. Доорх сонголтоос загвар, үнэ болон төслийн мэдээлэлтэй танилцаарай.', 'action':'menu','buttons':buttons}
    if not explicit_request(t) and has(t,['захиалагч байна','захиалагч бна','захиалсан байртай','гэрээтэй','танай захиалагч']):
        return {'reply':'Ойлголоо. Та захиалсан байрныхаа явц, төлбөр/гэрээ, инженерийн уулзалт эсвэл и-мэйл бүртгэлийн алийг тодруулах вэ?', 'action':'text','buttons':CUSTOMER_BUTTONS,'customer':'existing'}
    if explicit_request(t): return None
    if has(t,['шинээр сонирх','шинэ байр сонирх','хаус сонирх','шинэ худалдан авагч']) or t in {'хаус','байр','house','сонголт','загвар'}:
        return {'reply':'Таун болон мульт хаусны загваруудыг доорх картуудаас сонгон үзээрэй. Аль загвар танд илүү сонирхолтой байна вэ?', 'action':'models','buttons':sales.MODEL_BUTTONS,'customer':'prospect'}
    interest='mult' if has(t,['мульт','мулт']) else 'town' if has(t,['таун','town','taun']) else profile.get('interest')
    size_question=has(t,['мкв','м²','м2','талбай','хэмжээ','мкб','хэдэн','сонголт','m2','mkv'])
    price_question=has(t,['үнэ','үнийн','une','vne','нийт хэд','тооцоол','хэд болох','hed boloh'])
    if price_question:
        result=sales.direct_area_price_router(t)
        if not result: result=sales.direct_faq_router('үнэ')
        return {'reply':result[0]+'\nЭцсийн үнэ болон тухайн байрны үлдэгдлийг ажилтнаар баталгаажуулна.', 'action':'text','buttons':result[2] or buttons}
    if has(t,['дулаанаа','дулаан ав','дулаан ир','шатанда','шатандаа','блокийн явц','block','дотор засал']):
        return {'reply':'Бүртгэлд байгаа төлөвлөгөөгөөр 2026 оны өвөл дотоод заслын ажлыг эхлүүлэхээр ажиллаж байгаа. Тухайн блокийн дулаан болон ажлын бодит явцыг ажилтнаар тодруулна. Хүсвэл «ажилтантай холбогдох» сонголтыг дараарай.', 'action':'text','buttons':CUSTOMER_BUTTONS}
    if has(t,['төлбөрийн үлдэгдэл','миний төлбөр','гэрээний үлдэгдэл']):
        return {'reply':'Таны гэрээний төлбөрийн үлдэгдлийг ажилтан бүртгэлтэй тулгаж шалгана. «Ажилтантай ярих» сонголтоор хүсэлтээ дамжуулаарай.', 'action':'text','buttons':CUSTOMER_BUTTONS}
    if interest and (size_question or has(t,['мульт','мулт','таун','town','taun','зураг','план'])):
        label='Мульт' if interest=='mult' else 'Таун'
        sizes=MULT_SIZES if interest=='mult' else TOWN_SIZES
        keys=sales.direct_image_router(t if any(x.isdigit() for x in t) else ('мульт' if interest=='mult' else 'таун')) or []
        return {'reply':f'{label} хаусны зурагт бүртгэлтэй талбайнууд: {sizes} м². Доорх зургаас сонгон үзэж болно. Энэ жагсаалт нь борлуулагдаагүй байрны үлдэгдэл биш; та аль талбайг сонирхож байна вэ?',
                'action':'images','images':keys,'buttons':sales.MODEL_BUTTONS,'interest':interest,'customer':'prospect'}
    if size_question and not interest:
        return {'reply':f'Таун хаус: {TOWN_SIZES} м². Мульт хаусны талбайн зургуудыг «Мульт хаус» сонголтоос үзээрэй.', 'action':'models','buttons':sales.MODEL_BUTTONS}
    if has(t,['бартер','barter']):
        return {'reply':sales.PAYMENT_TEXT+' Бартерт ямар хөрөнгө санал болгохоо бичвэл ажилтанд дамжуулах хүсэлт бүртгэж болно.', 'action':'text','buttons':buttons}
    faq=sales.direct_faq_router(t)
    if faq:
        reply,action,custom=faq
        return {'reply':reply,'action':'menu' if action is True else 'models' if action=='MODEL' else 'text','buttons':custom or buttons}
    images=sales.direct_image_router(t)
    if images and (has(t,['зураг','план']) or re.fullmatch(r'\d+(?:[.,]\d+)?',t)):
        return {'reply':'Сонгосон талбайн зургуудыг доор харууллаа.','action':'images','images':images,'buttons':buttons}
    if t in {'баярлалаа','за баярлалаа','bayarlalaa','thanks'}:
        return {'reply':'Баярлалаа! Өөр тодруулах зүйл байвал бичээрэй.','action':'text','buttons':buttons}
    return None

def render(spec,sid,deliver):
    token=sales.transport.set(deliver)
    try:
        if not sales.send_fb_message(sid,spec['reply'],spec.get('buttons',DEFAULT_BUTTONS)): return
        if spec['action']=='menu': sales.send_carousel_menu(sid,DEFAULT_BUTTONS)
        elif spec['action']=='models': sales.send_model_carousel(sid,sales.MODEL_BUTTONS)
        elif spec['action']=='images': sales.send_images_by_keys(sid,spec['images'],spec.get('buttons',DEFAULT_BUTTONS))
    finally: sales.transport.reset(token)
