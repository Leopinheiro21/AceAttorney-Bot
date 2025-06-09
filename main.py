import os
import time
import tweepy
from moviepy.editor import *
from PIL import ImageFont, ImageDraw, Image

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

# 📦 Caminhos fixos
BG_PATH = "backgrounds/courtroom.png"
SOM_OBJECTION = "audio/objection.mp3"
MUSICA_FUNDO = "audio/tema.mp3"
FONT_PATH = "fonte/ace_font.ttf"  # Ou use Arial caso não tenha

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
        thread.reverse()

        alvo = thread[-1]
        texto = alvo.full_text.replace('\n', ' ')
        autor = alvo.user.screen_name
        personagem = extrair_personagem(len(thread))
        fala = f"{autor}: {texto}"
        return fala, personagem
    except Exception as e:
         print(f"Erro ao extrair fala: {e}")
         return None, None
 
 # 🔁 Processamento da menção
 def processar_mention(mention):
     try:
         if mention.entities and "urls" in mention.entities:
             for url in mention.entities["urls"]:
                 if "twitter.com" in url["expanded_url"]:
                     tweet_id = url["expanded_url"].split("/")[-1]
                     print(f"Processando tweet: {tweet_id}")
                     fala, personagem = extrair_fala(tweet_id)
                     if fala and personagem:
                         gerar_video(personagem, fala)
                         media = api.media_upload("tribunal.mp4")
                         client.create_tweet(
                             text=f"Objection!\n@{mention.user.screen_name}",
                             in_reply_to_status_id=mention.id,
                             media_ids=[media.media_id]
                         )
                         print("Vídeo postado com sucesso!")
     except Exception as e:
         print(f"Erro ao processar menção: {e}")
 
 # ▶️ Loop principal
 print("Bot iniciado. Monitorando menções...")
 since_id = None
 
 while True:
     try:
         mentions = api.mentions_timeline(since_id=since_id, tweet_mode="extended")
         for mention in reversed(mentions):
             since_id = max(mention.id, since_id or 0)
             processar_mention(mention)
         time.sleep(15)
     except Exception as e:
         print(f"Erro no loop principal: {e}")
         time.sleep(15)
