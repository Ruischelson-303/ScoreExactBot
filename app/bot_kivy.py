from kivy.app import App from kivy.lang import Builder from kivy.uix.boxlayout import BoxLayout import requests import numpy as np from scipy.stats import poisson from statistics import mean

KV = ''' <FootWidget>: orientation: 'vertical' padding: dp(10) spacing: dp(10)

TextInput:
    id: api_key
    hint_text: 'Clé API-Football'
    multiline: False
    size_hint_y: None
    height: dp(40)

TextInput:
    id: team1
    hint_text: 'Équipe Domicile'
    multiline: False
    size_hint_y: None
    height: dp(40)

TextInput:
    id: team2
    hint_text: 'Équipe Extérieur'
    multiline: False
    size_hint_y: None
    height: dp(40)

TextInput:
    id: recent_scores
    hint_text: '5 Scores récents (ex:2-1,3-0,...)'
    multiline: False
    size_hint_y: None
    height: dp(40)

BoxLayout:
    size_hint_y: None
    height: dp(40)
    spacing: dp(10)

    Button:
        text: 'Prédire'
        on_press: root.predict_scores()
    Button:
        text: 'Effacer'
        on_press: root.clear_fields()

Label:
    id: result
    text: ''
    halign: 'center'
    valign: 'middle'
    text_size: self.width, None
    size_hint_y: None
    height: dp(140)

'''

class FootWidget(BoxLayout): def init(self, **kwargs): super().init(**kwargs)

def get_team_id(self, api_key, name):
    url = 'https://v3.football.api-football.com/teams'
    r = requests.get(url, headers={'x-apisports-key': api_key}, params={'search': name})
    data = r.json().get('response', [])
    if not data:
        raise ValueError(f"Équipe '{name}' non trouvée.")
    return data[0]['team']['id']

def fetch_h2h(self, api_key, id1, id2, last=5):
    url = 'https://v3.football.api-football.com/fixtures'
    r = requests.get(url, headers={'x-apisports-key': api_key}, params={'h2h': f"{id1}-{id2}", 'last': last})
    data = r.json().get('response', [])
    return [(m['goals']['home'], m['goals']['away']) for m in data if m['goals']['home'] is not None]

def predict_scores(self):
    self.ids.result.text = 'Calcul en cours...'
    try:
        key = self.ids.api_key.text.strip()
        t1  = self.ids.team1.text.strip()
        t2  = self.ids.team2.text.strip()
        recent = [s.strip() for s in self.ids.recent_scores.text.split(',')]
        if len(recent) != 5:
            raise ValueError('Il faut 5 scores récents.')

        id1 = self.get_team_id(key, t1)
        id2 = self.get_team_id(key, t2)
        h2h = self.fetch_h2h(key, id1, id2)
        if not h2h:
            raise ValueError('Pas d\'historique H2H trouvé.')

        h1 = [x[0] for x in h2h]; h2 = [x[1] for x in h2h]
        r1 = [int(s.split('-')[0]) for s in recent]; r2 = [int(s.split('-')[1]) for s in recent]

        mu1 = mean(h1 + r1); mu2 = mean(h2 + r2)

        size = 6
        mat = np.zeros((size, size))
        for i in range(size):
            for j in range(size):
                mat[i, j] = poisson.pmf(i, mu1) * poisson.pmf(j, mu2)

        flat = mat.flatten(); idx = np.argsort(flat)[-2:][::-1]
        preds = [(i//size, i%size) for i in idx]
        probs = [flat[i] for i in idx]

        # Calculs supplémentaires
        prob_over_2_5 = sum([mat[i, j] for i in range(size) for j in range(size) if i + j > 2.5])
        prob_btts = sum([mat[i, j] for i in range(1, size) for j in range(1, size)])

        self.ids.result.text = (
            f"1️⃣ {t1} {preds[0][0]}-{preds[0][1]} {t2} ({probs[0]*100:.1f}%)\n"
            f"2️⃣ {t1} {preds[1][0]}-{preds[1][1]} {t2} ({probs[1]*100:.1f}%)\n\n"
            f"➕ Plus de 2.5 buts : {prob_over_2_5*100:.1f}%\n"
            f"🔁 Les deux équipes marquent : {prob_btts*100:.1f}%"
        )
    except Exception as e:
        self.ids.result.text = f"⚠️ Erreur: {e}"

def clear_fields(self):
    for field in ('api_key', 'team1', 'team2', 'recent_scores'):
        self.ids[field].text = ''
    self.ids.result.text = ''

class ScoreExactBotApp(App): def build(self): Builder.load_string(KV) return FootWidget()

if name == 'main': ScoreExactBotApp().run()

