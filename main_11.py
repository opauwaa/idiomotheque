import random

import flask.json

from data.models import StoryGen, yandex_rss, globo_rss, Story, User, text2im, load_im, delete_im, SLCT_LNG
from data import db_session
import os
import json
from flask import Flask, request


app = Flask(__name__)
@app.route("/")
def index():
    return "Привет от приложения Идиомотека"

@app.route('/post', methods=['POST'])
def main():
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False,

        }
    }

    user_id = request.json['session']['user_id']
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id= user_id,
            state=0,
            response='',
            image_id=''
        )
        db_sess.add(user)
    if request.json['request']['command'] in ['помощь', 'что ты умеешь']:
        state_101(response, request.json, user, db_sess)
    elif request.json['session']['new']:
        state_0(response, request.json, user, db_sess)
    else:
        a = json.loads(user.response)
        b = [i['title'].lower() for i in a['response']['buttons']]
        if request.json['request']['command'] in b:
            dialogue_states[user.state](response, request.json, user, db_sess)
        else:
            state_201(response, request.json, user, db_sess)
    user.response = json.dumps({'response': response['response']}, ensure_ascii=False)
    db_sess.commit()
    return json.dumps(response)

def state_101(res, req, user, db_sess):
    res['response']['text'] = """Навык Идиомотека способен представлять 
     отрывки статей из открытых новостных ресурсов на русском и португальском языках в режиме чтения и подбора спряжения глаголов.
     Выберите 'возобновить', чтобы продолжить игру либо 'в начало' для выбора режима и языка."""
    res['response']['buttons'] = [
        {
            'title': 'Выйти',
            'hide': 'True'
        },

        {
            'title': 'В начало',
            'hide': 'True'
        },

        {
            'title': 'Возобновить',
            'hide': 'True'
        }
    ]
    user.state_old = user.state
    user.response_old = user.response
    user.state = 102
    return

def state_102(res, req, user, db_sess):
    if req['request']['command'] == 'выйти':
        res['response']['text'] = 'До свидания!'
        res['response']['end_session'] = True
    elif req['request']['command'] == 'в начало':
        state_0(res, req, user, db_sess)
    else:
        a = json.loads(user.response_old)
        res['response'] = a['response']
        user.state = user.state_old
    return

def state_201(res, req, user, db_sess):
    res['response']['text'] = 'Некорректный запрос'
    a = json.loads(user.response)
    res['response']['buttons'] = a['response']['buttons']
    return

def state_0(res, req, user, db_sess):
    res['response']['text'] = '''Навык Идиомотека работает в режиме чтения новостей и спряжения
                                глаголов для ресурсов на русском и португальском языках. 
                                Выберите "Хочу спрягать" или "Хочу читать", чтобы перейти
                                в соответствующий режим.'''
    res['response']['buttons'] = [
        {
            'title': 'Хочу спрягать',
            'hide': 'True'
        },

        {
            'title': 'Хочу читать',
            'hide': 'True'
        }
    ]
    user.state = 1
    return

def state_1(res, req, user, db_sess):
    if req['request']['command'] == 'хочу спрягать':
        user.mode = 'conjugation'
    elif req['request']['command'] == 'хочу читать':
        user.mode = 'reading'
    else:
        res['response']['text'] = 'Некорректный запрос'
        return
    res['response']['text'] = 'Выберите язык'
    res['response']['buttons'] = [
        {
            'title': 'Русский',
            'hide': 'True'
        },

        {
            'title': 'Португальский',
            'hide': 'True'
        }
    ]
    user.state = 2
    return

def state_2(res, req, user, db_sess):
    if req['request']['command'] == 'русский':
        user.language = 'russian'
    elif req['request']['command'] == 'португальский':
        user.language = 'portuguese'
    if user.stories:
        for i in user.stories:
            a = json.loads(i.content)
            if a['language'] == user.language:
                res['response']['text'] = 'Обновить рассказ?'
                res['response']['buttons'] = [
                    {
                        'title': 'Да',
                        'hide': 'True'
                    },

                    {
                        'title': 'Нет',
                        'hide': 'True'
                    }
                ]
                user.state = 3
                return
    with open(SLCT_LNG[user.language][2], 'rt', encoding='utf8') as f:
        a = json.load(f)
    story = Story(
        content=json.dumps(a, ensure_ascii=False),
        user_id=request.json['session']['user_id'],
        counter= 0
    )
    db_sess.add(story)
    user.stories += [story]
    if user.mode == 'reading':
        state_4(res, req, user, db_sess)
    if user.mode == 'conjugation':
        state_6(res, req, user, db_sess)
    return

def state_3(res, req, user, db_sess):
    if req['request']['command'] == 'да':
        for i in user.stories:
            a = json.loads(i.content)
            if a['language'] == user.language:
                user.stories.remove(i)
                break
        with open(SLCT_LNG[user.language][2], 'rt', encoding='utf8') as f:
            a = json.load(f)
        story = Story(
            content = json.dumps(a, ensure_ascii=False),
            user_id = request.json['session']['user_id'],
            counter = 0
        )
        db_sess.add(story)
        user.stories += [story]
    if user.mode == 'reading':
        state_4(res, req, user, db_sess)
    elif user.mode == 'conjugation':
        state_6(res, req, user, db_sess)

def state_4(res, req, user, db_sess):
    for i in user.stories:
        a = json.loads(i.content)
        if a['language'] == user.language:
            print(i.counter)
            if i.counter < len(a['abstracts']):
                txt1 = f"{a['abstracts'][i.counter]['title']}"
                res['response']['text'] = txt1
                txt2 = f"{a['abstracts'][i.counter]['description']}"
                res['response']['text'] += txt2
                text2im(txt1, txt2, '', user.id + '.png')
                delete_im(user.image_id)
                im = load_im(user.id + '.png')
                if os.path.exists(user.id + '.png'):
                    os.remove(user.id + '.png')
                if im:
                    user.image_id = im
                    res['response']['card'] = {}
                    res['response']['card']['type'] = 'BigImage'
                    res['response']['card']['image_id'] = im
                else:
                    user.image_id = ''
                res['response']['buttons'] = [
                    {
                        'title': 'Следующий',
                        'hide': 'True'
                    }
                ]
                i.counter += 1
                user.state = 4
            else:
                res['response']['text'] = 'Рассказов больше нет'
                delete_im(user.image_id)
                res['response']['buttons'] = [
                    {
                        'title': 'Повторить',
                        'hide': 'True'
                    },

                    {
                        'title': 'Выйти',
                        'hide': 'True'
                    },
                    {
                        'title': 'В начало',
                        'hide': 'True'
                    }
                ]
                user.state = 5
    return


def state_5(res, req, user, db_sess):
    if req['request']['command'] == 'выйти':
        res['response']['text'] = 'До свидания!'
        res['response']['end_session'] = True
    elif req['request']['command'] == 'в начало':
        state_0(res, req, user, db_sess)
        return
    else:
        for i in user.stories:
            a = json.loads(i.content)
            if a['language'] == user.language:
                i.counter = 0
    if user.mode == 'reading':
        state_4(res, req, user, db_sess)
    else:
        state_6(res, req, user, db_sess)
    return


def state_6(res, req, user, db_sess):
    for i in user.stories:
        a = json.loads(i.content)
        if a['language'] == user.language:
            if i.counter < len(a['abstracts']):
                txt1 = f"{a['abstracts'][i.counter]['title']}"
                res['response']['text'] = txt1
                txt2 = f"{a['abstracts'][i.counter]['description']}"
                res['response']['text'] += txt2
                txt2 = txt2.replace(a['abstracts'][i.counter]['verb'], a['abstracts'][i.counter]['infinitive'], 1)
                txt2 = txt2.replace(a['abstracts'][i.counter]['verb'].capitalize(), a['abstracts'][i.counter]['infinitive'].capitalize(), 1)
                text2im(txt1, txt2, a['abstracts'][i.counter]['infinitive'], user.id + '.png')
                delete_im(user.image_id)
                im = load_im(user.id + '.png')
                if os.path.exists(user.id + '.png'):
                    os.remove(user.id + '.png')
                if im:
                    user.image_id = im
                    res['response']['card'] = {}
                    res['response']['card']['type'] = 'BigImage'
                    res['response']['card']['image_id'] = im
                else:
                    user.image_id = ''
                res['response']['buttons'] = []
                z = random.sample(a['abstracts'][i.counter]['conjugation'], k=5)
                z = [i for i in z if '-' not in i]
                wl = set([a['abstracts'][i.counter]['verb']] + z)
                for j in wl:
                    res['response']['buttons'] += [
                        {
                            'title': j,
                            'hide': True
                        }
                    ]
                user.state = 7
            else:
                res['response']['text'] = 'Рассказов больше нет'
                delete_im(user.image_id)
                res['response']['buttons'] = [
                    {
                        'title': 'Повторить',
                        'hide': 'True'
                    },

                    {
                        'title': 'Выйти',
                        'hide': 'True'
                    },
                    {
                        'title': 'В начало',
                        'hide': 'True'
                    }
                ]
                user.state = 5
    return

def state_7(res, req, user, db_sess):
    for i in user.stories:
        a = json.loads(i.content)
        if a['language'] == user.language:
            v = a['abstracts'][i.counter]['verb']
            if req['request']['command'] == v:
                res['response']['text'] = 'Правильно'
            else:
                res['response']['text'] = f'Ошибка, правильное слово "{v}"'
            res['response']['buttons'] = [
                {
                    'title': 'Следующий',
                    'hide': 'True'
                }
            ]
            i.counter += 1
            break
    user.state = 6
    return


dialogue_states = {
    0: state_0,
    1: state_1,
    2: state_2,
    3: state_3,
    4: state_4,
    5: state_5,
    6: state_6,
    7: state_7,
    #состояние помощи
    101: state_101,
    102: state_102,
    #состояние некорректного запроса
    201: state_201
}

import atexit
from story import russ_n_port
from apscheduler.schedulers.background import BackgroundScheduler

# подборка статей будет обновляться каждые 120 минут для этого запускается планировщик событий
scheduler = BackgroundScheduler()
scheduler.add_job(func=russ_n_port, trigger="interval", minutes=120)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    if os.path.exists('db/stories.db'):
        os.remove('db/stories.db')
    db_session.global_init("db/stories.db")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
