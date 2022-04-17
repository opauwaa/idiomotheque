import textwrap

import sqlalchemy, requests, re
import random
from .db_session import SqlAlchemyBase
from bs4 import BeautifulSoup
from PIL import Image, ImageFont, ImageDraw
from . import alice
import pt_core_news_sm, ru_core_news_sm
'''
рассказ имеет вид объекта json
{'language':'russian',
 'abstracts':[
     {
         'title':'',
         'description':'',
         'pubdate':'',
         'verb':'',
         'infinitive':'',
         'conjugation':''
     },
     ...

    {
         'title':'',
         'description':'',
         'pubdate':'',
         'verb':'',
         'infinitive':'',
         'conjugation':''
    }
 ]
}
'''


class Story(SqlAlchemyBase):
    __tablename__ = 'stories'
    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    content = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user = sqlalchemy.orm.relation('User')
    counter = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)

class User(SqlAlchemyBase):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
    state = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    # два режима: режим спряжения и режим чтения
    mode = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    language = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    #предыдущий response
    response = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    #состояние до входа в помощь
    state_old = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    response_old = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    stories = sqlalchemy.orm.relation('Story', back_populates='user')
    image_id = sqlalchemy.Column(sqlalchemy.String, nullable=True)

yandex_rss = {
    "0": "https://news.yandex.ru/index.rss",
    "1": "https://news.yandex.ru/business.rss",
    "2": "https://news.yandex.ru/energy.rss",
    "3": "https://news.yandex.ru/finances.rss",
    "4": "https://news.yandex.ru/realty.rss",
    "5": "https://news.yandex.ru/politics.rss",
    "6": "https://news.yandex.ru/society.rss",
    "7": "https://news.yandex.ru/communal.rss",
    "8": "https://news.yandex.ru/ecology.rss",
    "9": "https://news.yandex.ru/health.rss",
    "10": "https://news.yandex.ru/travels.rss",
    "11": "https://news.yandex.ru/vehicle.rss",
    "12": "https://news.yandex.ru/showbusiness.rss",
    "13": "https://news.yandex.ru/religion.rss",
    "14": "https://news.yandex.ru/world.rss",
    "15": "https://news.yandex.ru/incident.rss",
    "16": "https://news.yandex.ru/culture.rss",
    "17": "https://news.yandex.ru/movies.rss",
    "18": "https://news.yandex.ru/music.rss",
    "19": "https://news.yandex.ru/theaters.rss",
    "20": "https://news.yandex.ru/computers.rss",
    "21": "https://news.yandex.ru/internet.rss",
    "22": "https://news.yandex.ru/gadgets.rss",
    "23": "https://news.yandex.ru/games.rss",
    "24": "https://news.yandex.ru/science.rss",
    "25": "https://news.yandex.ru/cosmos.rss",
    "26": "https://news.yandex.ru/auto.rss",
    "27": "https://news.yandex.ru/sport.rss",
    "28": "https://news.yandex.ru/football.rss",
    "29": "https://news.yandex.ru/hockey.rss",
    "30": "https://news.yandex.ru/basketball.rss",
    "31": "https://news.yandex.ru/tennis.rss",
    "32": "https://news.yandex.ru/auto_racing.rss",
    "33": "https://news.yandex.ru/martial_arts.rss",
    "34": "https://news.yandex.ru/army.rss",
    "35": "https://news.yandex.ru/koronavirus.rss"
}

globo_rss = {
    "0": "http://g1.globo.com/dynamo/brasil/rss2.xml",
    "1": "http://g1.globo.com/dynamo/carros/rss2.xml",
    "2": "http://g1.globo.com/dynamo/ciencia-e-saude/rss2.xml",
    "3": "http://g1.globo.com/dynamo/concursos-e-emprego/rss2.xml",
    "4": "http://g1.globo.com/dynamo/economia/rss2.xml",
    "5": "http://g1.globo.com/dynamo/educacao/rss2.xml",
    "6": "http://g1.globo.com/dynamo/loterias/rss2.xml",
    "7": "http://g1.globo.com/dynamo/mundo/rss2.xml",
    "8": "http://g1.globo.com/dynamo/musica/rss2.xml",
    "9": "http://g1.globo.com/dynamo/natureza/rss2.xml",
    "10": "http://g1.globo.com/dynamo/planeta-bizarro/rss2.xml",
    "11": "http://g1.globo.com/dynamo/politica/mensalao/rss2.xml",
    "12": "http://g1.globo.com/dynamo/pop-arte/rss2.xml",
    "13": "http://g1.globo.com/dynamo/tecnologia/rss2.xml",
    "14": "http://g1.globo.com/dynamo/turismo-e-viagem/rss2.xml"
}

class StoryGen:
    def __init__(self, url, lang='russian', sz=500):
        self.sz = sz
        self.url = url
        self.lang = lang

    def basic(self, n=-1):
        html = requests.get(self.url).content.decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')
        with open ('./extras/soup_extract.html', 'wt', encoding='utf-8') as f:
            f.write(str(soup))
        content = {
            'language' : self.lang,
            'abstracts' : []
        }
        if n == 0:
            return content
        a = soup.find_all('item')
        if n == -1 or n > len(a):
            n = len(a)

        def remove_nbsp(t):
            tt = re.sub(' +', ' ', t.replace('\xa0', ' ').strip())
            for j in re.findall(r'(?<=\<img)(.*)(?=\<br \/\>)', tt):
                tt = tt.replace('<img' + j + '<br />', '').strip()
            return tt

        for i in a:
            description = remove_nbsp(i.find('description').text)
            if len(description) > self.sz:
                fs = max([m.start() for m in re.finditer('\.', description) if m.start() < self.sz])
                description = description[0:fs+1]
            content['abstracts'] += [{
                'title': remove_nbsp(i.find('title').text),
                'description': description,
                'pubdate': i.find('pubdate').text,
                'verb': '',
                'infinitive':'',
                'conjugation':[]
            }]
            n -= 1
            if n == 0:
                return content

SLCT_LNG = {
    'portuguese' : [
        'https://conjugator.reverso.net/conjugation-portuguese-verb-',#адрес ресурса спряжения
        pt_core_news_sm, #модуль словаря
        'portuguese.json', #файл хранения обработанных данных
        globo_rss['9'],
        10
    ],
    'russian' : ['https://conjugator.reverso.net/conjugation-russian-verb-',
        ru_core_news_sm, #модуль словаря
        'russian.json', #файл хранения обработанных данных
        yandex_rss['17'],
        10
    ]
}

#поиск глаголов в отрывке текста
def spacy_proc(s, lang):
    nlp = SLCT_LNG[lang][1].load()
    doc = nlp(s)
    vb = []
    for k in [(j, w.text, w.pos_, w.lemma_ ) for j, w in enumerate(doc)]:
        if k[2] == 'VERB':
            vb += [[k[1].lower(), k[3].lower()]]
    if vb:
        v = random.choice(vb)
    else:
        v= ['','']
    return v

def reverso_proc(w, lang='russian'):
    if w=='':
        return []
    url= SLCT_LNG[lang][0]+w+'.html'
    html = requests.get(url).content.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    #with open ('soup_07.txt', 'wt', encoding='UTF-8') as f:
    #    f.write(str(soup))
    wl = []
    for i in soup.find_all('div', class_='blue-box-wrap'):
        if lang=='russian':
            k = i.find_all('div', class_=[])
        else:
            k = i.find_all('i', attrs={'h' : '1'})
        for j in k:
            a = j.find('i', class_='verbtxt')
            if a:
                a = a.text
            else:
                a = ''
            b = j.find('i', class_='verbtxt-term')
            if b:
                b = b.text
            else:
                b = ''
            c = j.find('i', class_='verbtxt-term-irr')
            if c:
                c = c.text
            else:
                c = ''
            a = a + b + c
            if a != '':
                wl +=  [a]
    return list(set(wl))

def text2im(title, description, substr, fname):
    im= Image.new('RGB', (776, 344), (240, 240, 240))
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype('./static/arialnew.ttf', 23)
    margin = offset = 5
    for line in textwrap.wrap(title, width=57):
        draw.text((margin, offset), line, font=font, fill='#000000')
        offset += font.getsize(line)[1]
    offset += 20
    for line in textwrap.wrap(description, width=57):
        if substr != '' and (line.find(substr) != -1 or line.find(substr.capitalize()) != -1):
            start = line.find(substr)
            if start == -1:
                start = line.find(substr.capitalize())
            end = start + len(substr) - 1
            margin0 = margin
            for j, i in enumerate(line):
                if j < start or j > end:
                    draw.text((margin0, offset), i, font=font, fill='#000000')
                else:
                    draw.text((margin0, offset), i, font=font, fill='#fc0303')
                margin0 += font.getsize(i)[0]
        else:
            draw.text((margin, offset), line, font = font, fill='#000000')
        offset += font.getsize(line)[1]
    im.save(fname)

def upload_im(fname, image_id=''):
    yandex = alice.YandexImages()
    yandex.set_auth_token(token=alice.TOKEN)
    yandex.skills = alice.SKILL
    if image_id !='':
        response=yandex.deleteImage(image_id)
    response = yandex.downloadImageFile(fname)
    image_id = response.get('id', None)
    return image_id

def delete_im(image_id=''):
    yandex = alice.YandexImages()
    yandex.set_auth_token(token=alice.TOKEN)
    yandex.skills = alice.SKILL
    response = None
    if image_id != '':
        response = yandex.deleteImage(image_id)
    return response

def load_im(fname):
    yandex = alice.YandexImages()
    yandex.set_auth_token(token=alice.TOKEN)
    yandex.skills = alice.SKILL
    response = yandex.downloadImageFile(fname)
    image_id = response.get('id', None)
    return image_id



