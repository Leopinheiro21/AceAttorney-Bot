import os
import time
import tweepy
from moviepy.editor import *
from PIL import ImageFont, ImageDraw, Image
from flask import Flask
from threading import Thread

# 🔐 Variáveis de ambiente
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

# 🔐 Autenticação com Twitter
auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
api = tweepy.API(auth)
client = tweepy.Client(
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret
)
try:
    os.makedirs("temp", exist_ok=True)
    os.makedirs("gifs/phoenix", exist_ok=True)
    os.makedirs("gifs/edgeworth", exist_ok=True)
except Exception as e:
    print(f"Erro ao criar diretórios: {e}")
    raise

# 📦 Caminhos fixos
BG_PATH = "backgrounds/courtroom.png"
SOM_OBJECTION = "audio/objection.mp3"
MUSICA_FUNDO = "audio/tema.mp3"
FONT_PATH = "fonte/ace_font.ttf"

# 🎨 Função para criar uma imagem com texto (fala)
def criar_frame_com_texto(texto, output):
    bg = Image.open(BG_PATH).convert("RGBA")
    draw = ImageDraw.Draw(bg)
    fonte = ImageFont.truetype(FONT_PATH, 28)
    draw.rectangle([(30, 400), (610, 470)], fill=(255, 255, 255, 230))
    draw.text((40, 410), texto, font=fonte, fill=(0, 0, 0))
    bg.save(output)

# 🎬 Função para gerar vídeo da cena
def gerar_video(personagem, fala, output="tribunal.mp4"):
    # Cena de fundo com texto
    criar_frame_com_texto(fala, "temp/fundo_texto.png")
    fundo = ImageClip("temp/fundo_texto.png").set_duration(5)

    # GIF do personagem fazendo "Objection!"
    gif_path = f"gifs/{personagem}/objection.gif"
    gif = VideoFileClip(gif_path, has_mask=True).resize(height=400)
    gif = gif.set_position(("center", "bottom")).set_start(1).set_duration(2)

    # Áudio
    som = AudioFileClip(SOM_OBJECTION).set_start(1)
    musica = AudioFileClip(MUSICA_FUNDO).subclip(0, 5)
    audio_final = CompositeAudioClip([musica, som])

    # Composição
    video = CompositeVideoClip([fundo, gif]).set_audio(audio_final)
    video.write_videofile(output, fps=24)

# 🧠 Função para decidir personagem alternado (exemplo simples)
def extrair_personagem(index):
    return ["phoenix", "edgeworth"][index % 2]

# 🗣️ Função para processar o tweet em thread
def extrair_fala(tweet_id):
    try:
        thread = []
        tweet = api.get_status(tweet_id, tweet_mode="extended")
        while tweet:
            thread.append(tweet)
            if not tweet.in_reply_to_status_id:
                break
            tweet = api.get_status(tweet.in_reply_to_status_id, tweet_mode="extended")
        if not thread:
            return None, None
        thread.reverse()
        alvo = thread[-1]

        alvo = thread[-1]
        texto = alvo.full_text.replace('\n', ' ')
        autor = alvo.user.screen_name  # Corrigido: era "s.creen_name"
        personagem = extrair_personagem(len(thread))
        fala = f"{autor}: {texto}"
        return fala, personagem
    except Exception as e:
        print(f"Erro ao extrair fala: {e}")
        return None, None
 
 # 🔁 Processamento da menção
def processar_mention(mention):
    try:
        texto = mention["text"].lower()
        if "render" not in texto:
            print("🔕 Menção ignorada (não contém 'render').")
            return

        if mention["entities"] and "urls" in mention["entities"]:
            for url in mention["entities"]["urls"]:
                if "twitter.com" in url["expanded_url"]:
                    tweet_id = url["expanded_url"].split("/")[-1]
                    print(f"⚙️ Processando tweet referenciado: {tweet_id}")
                    fala, personagem = extrair_fala(tweet_id)
                    if fala and personagem:
                        gerar_video(personagem, fala)
                        media = api.media_upload("tribunal.mp4")
                        client.create_tweet(
                            text=f"Objection!\n@{mention['user']['screen_name']}",
                            in_reply_to_status_id=mention["id"],
                            media_ids=[media.media_id]
                        )
                        print("✅ Vídeo postado com sucesso!")
        else:
            print("⚠️ Menção não contém link de tweet.")
    except Exception as e:
        print(f"❌ Erro ao processar menção: {e}")
 
 # ▶️ Loop principal
def start_bot():
    print("Bot iniciado. Monitorando menções...")
    since_id = None
    while True:
        try:
            response = client.get_users_mentions(
                os.getenv("TWITTER_USER_ID"),
                expansions=["author_id"],
                tweet_fields=["created_at", "in_reply_to_user_id"],
                max_results=5
            )

            if response.data:
                for tweet in response.data:
                    mention = {
                        "id": tweet.id,
                        "text": tweet.text,
                        "user": {
                            "screen_name": next(u.username for u in response.includes["users"] 
                                                if u.id == tweet.author_id),
                            "id": tweet.author_id
                        },
                        "entities": {
                            "urls": []
                        }
                    }

                    if hasattr(tweet, 'in_reply_to_user_id'):
                        mention['in_reply_to_status_id'] = tweet.id

                    processar_mention(mention)
                    since_id = tweet.id

            time.sleep(15)
        except tweepy.TweepyException as e:
            print(f"Erro na API: {e}")
            time.sleep(60)
        except Exception as e:
            print(f"Erro inesperado: {e}")
            time.sleep(300)

# 🌐 Servidor Flask obrigatório para Web Service no Render gratuito
app = Flask(__name__)

@app.route('/')
def index():
    return "Ace Attorney Bot rodando com Flask."

if __name__ == '__main__':
    Thread(target=start_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
