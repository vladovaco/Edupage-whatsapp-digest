# Edupage → WhatsApp hlasový digest

Aplikácia na požiadanie stiahne najnovšie správy z Edupage o tvojom dieťati
(správy od učiteľov, oznamy, domáce úlohy, písomky, známky, suplovanie, akcie…),
zostaví z nich krátky slovenský súhrn a pošle ti ho na WhatsApp ako **hlasovku**
(plus voliteľne aj ako text).

Ako to funguje:

1. **Edupage** – prihlási sa cez [`edupage-api`](https://pypi.org/project/edupage-api/)
   a stiahne nové udalosti z nástenky od posledného spustenia.
2. **Digest** – text zhrnie do prirodzenej hovorenej slovenčiny. Ak nastavíš
   `ANTHROPIC_API_KEY`, zhrnutie robí Claude Opus 5.5; bez neho sa použije jednoduchá šablóna.
3. **Hlasovka** – text sa prevedie na reč cez [ElevenLabs](https://elevenlabs.io)
   (model `eleven_multilingual_v2`, zvláda slovenčinu; bez `ELEVENLABS_API_KEY`
   alebo pri chybe API sa použije gTTS) a cez `ffmpeg`
   skonvertuje do OGG/Opus, aby sa vo WhatsApp zobrazil ako skutočná hlasovka.
4. **WhatsApp** – audio sa odošle cez oficiálne WhatsApp Cloud API (Meta).

## Inštalácia

Potrebuješ Python 3.10+ a `ffmpeg`:

```bash
sudo apt install ffmpeg          # macOS: brew install ffmpeg
pip install -r requirements.txt
cp .env.example .env             # a doplň svoje údaje
```

### Čo treba nastaviť v `.env`

| Premenná | Popis |
| --- | --- |
| `EDUPAGE_USERNAME`, `EDUPAGE_PASSWORD` | prihlasovacie údaje do Edupage (rodičovské konto) |
| `EDUPAGE_SUBDOMAIN` | subdoména školy – z `https://mojaskola.edupage.org` je to `mojaskola` |
| `EDUPAGE_CHILD_ID` | voliteľné – `person_id` dieťaťa, ak máš v konte viac detí |
| `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` | prístup k [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started) |
| `WHATSAPP_RECIPIENT` | tvoje číslo v medzinárodnom formáte, napr. `421900123456` |
| `ANTHROPIC_API_KEY` | zhrnutie cez Claude Opus 5.5 (bez neho jednoduchá šablóna) |
| `ANTHROPIC_MODEL` | voliteľné – iný Claude model, predvolene `claude-opus-5-5` |
| `ELEVENLABS_API_KEY` | hlas cez ElevenLabs (bez neho gTTS) |
| `ELEVENLABS_VOICE_ID`, `ELEVENLABS_MODEL` | voliteľné – hlas (predvolene „George“) a model (`eleven_multilingual_v2`) |

WhatsApp Cloud API je oficiálna cesta od Mety: v [Meta for Developers](https://developers.facebook.com/)
si vytvoríš appku typu *Business*, pridáš produkt *WhatsApp* a dostaneš testovacie
číslo, `PHONE_NUMBER_ID` a token zadarmo. Svoje číslo pridáš medzi príjemcov.

## Použitie (na požiadanie)

```bash
# pošli mi digest teraz
python -m edupage_digest

# len vypíš, čo by sa poslalo (nič sa neodošle)
python -m edupage_digest --dry-run

# ignoruj uložený stav a zober všetko za posledné 3 dni
python -m edupage_digest --days 3
```

Aplikácia si v `.state.json` pamätá čas posledného behu, takže pri ďalšom
spustení pošle len to, čo medzičasom pribudlo. Ak nič nové nie je, nič nepošle.

Ak má tvoje Edupage konto zapnuté dvojfaktorové overenie, aplikácia počká
30 sekúnd na potvrdenie v mobilnej appke, alebo si v termináli vypýta kód.

## Voliteľné: digest cez WhatsApp správu

Ak chceš digest vyžiadať priamo z WhatsAppu (napíšeš botovi „digest" a on ti
odpovie hlasovkou), spusti webhook server:

```bash
python webhook_server.py
```

a v Meta appke nastav webhook na `https://tvoja-domena/webhook` s verify tokenom
`WEBHOOK_VERIFY_TOKEN`. Server musí byť dostupný z internetu (napr. cez
`cloudflared tunnel` alebo `ngrok http 8000`). Reaguje na slová
`digest`, `novinky`, `správy`, `edupage` – a len z čísla `WHATSAPP_RECIPIENT`,
nikto cudzí digest spustiť nemôže.

## Deploy – kde to spustiť

**Najrýchlejšie: GitHub Actions (bez servera, zadarmo).** Workflow je už v repe
(`.github/workflows/digest.yml`): v repozitári nastav Actions secrets
(`EDUPAGE_*`, `WHATSAPP_*`, `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`) a digest spustíš
tlačidlom **Actions → Edupage digest → Run workflow** – aj z mobilnej appky
GitHub. Automaticky beží aj každý pracovný deň o 17:05 (blok `schedule` vo workflow).
Pozor: ak máš na Edupage zapnuté 2FA, headless beh čaká 30 s na potvrdenie
v mobilnej appke Edupage – buď potvrď hneď po spustení, alebo 2FA vypni.

**WhatsApp bot (napíšeš „digest", príde hlasovka): Render / Railway / Fly.io.**
V repe je `Dockerfile` – na [Render](https://render.com) stačí *New → Web
Service → z tohto GitHub repa*, Render Dockerfile rozpozná sám; premenné z
`.env` vlož ako Environment Variables a výslednú URL (`https://…/webhook`)
nastav v Meta appke ako webhook. Free tier stačí (služba po nečinnosti spí,
prvá odpoveď preto môže prísť o ~minútu neskôr).

**Vlastné železo (Raspberry Pi, NAS, VPS):** `docker run --env-file .env -p
8000:8000 edupage-digest` alebo rovno `python webhook_server.py` + tunel
(`cloudflared tunnel --url http://localhost:8000`) na verejnú HTTPS adresu.

## Poznámky

- Hlasovka sa generuje ako OGG/Opus (mono) – presne to, čo WhatsApp vyžaduje,
  aby sa správa zobrazila ako hlasovka. Bez `ffmpeg` sa pošle MP3 (prehrateľné,
  ale nie ako hlasovka).
- Do digestu idú len relevantné typy udalostí – pípnutia dochádzky, výdaj
  stravy a interné systémové udalosti sa filtrujú preč.
- `.env` a `.state.json` sú v `.gitignore` – prihlasovacie údaje sa do gitu nedostanú.
