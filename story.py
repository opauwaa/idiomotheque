from data.models import StoryGen,spacy_proc, reverso_proc, SLCT_LNG

import json

def story2file(lang='russian'):
    a = StoryGen(SLCT_LNG[lang][3], lang=lang).basic(SLCT_LNG[lang][4])
    to_del = []
    for n, i in enumerate(a['abstracts']):
        j = spacy_proc(i['description'], lang)
        k = reverso_proc(j[1], lang)
        print(n)
        print(j)
        print(k)
        if j and k:
            i['verb'] = j[0]
            i['infinitive'] = j[1]
            i['conjugation'] = k
        else:
            to_del += [n]
    for i in to_del:
        del a['abstracts'][i]
    print('всего отрывков' , len(a['abstracts']))
    if len(a['abstracts']):
        with open(SLCT_LNG[lang][2], 'wt', encoding='utf8') as f:
            json.dump(a, f, ensure_ascii=False, indent=2)

def russ_n_port():
    story2file(lang='portuguese')
    story2file(lang='russian')

if __name__ == '__main__':
    story2file(lang='portuguese')

