import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from twitchio.ext import commands
from flask import Flask, request, redirect
import re

# Configuración de Twitch
CLIENT_ID = 'tu_bot_id_token'
CLIENT_SECRET = 'tu_bot_secret_token'
TWITCH_NAME = 'tu_nombre'
REDIRECT_URI_TWITCH = 'http://localhost:5000/twitch_callback'
SCOPES_TWITCH = 'chat:read chat:edit'


# Configuración de Spotify
SPOTIFY_CLIENT_ID = '0e51b23a84eb465fb0057985443d2ecf'
SPOTIFY_CLIENT_SECRET = '9e7f5d8f371d4936a6b2d6aee0b38e1d'
REDIRECT_URI_SPOTIFY = 'http://localhost:5000/spotify_callback'
SCOPES_SPOTIFY = 'user-modify-playback-state'

# Variables para almacenar tokens
access_token_twitch = None
spotify = None

# Inicia el servidor Flask para autenticación
app = Flask(__name__)

@app.route('/')
def index():
    return '''
        <h1>Autenticación del bot</h1>
        <a href="/login_twitch">Autenticar con Twitch</a><br>
        <a href="/login_spotify">Autenticar con Spotify</a>
    '''

# Autenticación con Twitch
@app.route('/login_twitch')
def login_twitch():
    auth_url = f'https://id.twitch.tv/oauth2/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI_TWITCH}&scope={SCOPES_TWITCH}'
    return redirect(auth_url)

@app.route('/twitch_callback')
def twitch_callback():
    global access_token_twitch
    code = request.args.get('code')

    token_url = 'https://id.twitch.tv/oauth2/token'
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI_TWITCH
    }

    response = requests.post(token_url, data=data)
    response_data = response.json()

    if 'access_token' in response_data:
        access_token_twitch = response_data['access_token']
        return f'Twitch token obtenido: {access_token_twitch}'
    else:
        return 'Error obteniendo el token de Twitch.'

# Autenticación con Spotify
@app.route('/login_spotify')
def login_spotify():
    spotify_auth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                                client_secret=SPOTIFY_CLIENT_SECRET,
                                redirect_uri=REDIRECT_URI_SPOTIFY,
                                scope=SCOPES_SPOTIFY)
    auth_url = spotify_auth.get_authorize_url()
    return redirect(auth_url)

@app.route('/spotify_callback')
def spotify_callback():
    global spotify
    spotify_auth = SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                                client_secret=SPOTIFY_CLIENT_SECRET,
                                redirect_uri=REDIRECT_URI_SPOTIFY,
                                scope=SCOPES_SPOTIFY)
    code = request.args.get('code')
    token_info = spotify_auth.get_access_token(code)
    spotify = spotipy.Spotify(auth=token_info['access_token'])
    return 'Autenticación con Spotify completada!'

# Función para iniciar el bot de Twitch
class TwitchBot(commands.Bot):
    def __init__(self):
        super().__init__(token='oauth:' + access_token_twitch, prefix='!', initial_channels=[f'{TWITCH_NAME}'])

    async def event_ready(self):
        print(f'Bot conectado a Twitch como {self.nick}')

    async def event_message(self, message):
        if message.author is None:
            return  # Ignora los mensajes sin autor

        print(f'Mensaje recibido de {message.author.name}: {message.content}')
        await self.handle_commands(message)

    # Registrar el comando !sr
    @commands.command(name='sr')
    async def songrequest(self, ctx):
        song_query = ctx.message.content[4:].strip()

        if is_spotify_link(song_query):
            track_uri = song_query
        else:
            track_uri = search_song_on_spotify(song_query)

        if track_uri:
            success = add_song_to_spotify_queue(track_uri)
            if success:
                await ctx.send(f'@{ctx.author.name} tu canción ha sido añadida a la cola.')
            else:
                await ctx.send(f'@{ctx.author.name} no se pudo añadir la canción a la cola.')
        else:
            await ctx.send(f'@{ctx.author.name} no se encontró ninguna canción con ese nombre.')

# Buscar canción en Spotify
def search_song_on_spotify(query):
    if spotify:
        results = spotify.search(q=query, type='track', limit=1)
        tracks = results['tracks']['items']
        return tracks[0]['uri'] if tracks else None
    else:
        print("Spotify no está autenticado.")
        return None

# Añadir canción a la cola de Spotify
def add_song_to_spotify_queue(track_uri):
    try:
        spotify.add_to_queue(track_uri)
        return True
    except Exception as e:
        print(f"Error añadiendo la canción a la cola: {e}")
        return False

# Verificar si el enlace es de Spotify
def is_spotify_link(link):
    return re.match(r'^https?://(open|play)\.spotify\.com/.*$', link) is not None

def start_twitch_bot():
    if access_token_twitch:
        bot = TwitchBot()
        bot.run()
    else:
        print("El bot de Twitch no puede iniciar sin un token de acceso.")

if __name__ == '__main__':
    # Iniciar Flask en un hilo separado para manejar la autenticación
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(port=5000))
    flask_thread.start()

    # Espera a que el usuario obtenga los tokens y luego inicia el bot
    input("Presiona ENTER después de autenticar en Twitch y Spotify...")
    start_twitch_bot()