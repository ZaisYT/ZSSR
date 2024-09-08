const tmi = require('tmi.js');
const axios = require('axios');
const express = require('express');
const app = express();

const SPOTIFY_CLIENT_ID = '0e51b23a84eb465fb0057985443d2ecf';
const SPOTIFY_CLIENT_SECRET = '9e7f5d8f371d4936a6b2d6aee0b38e1d';
const REDIRECT_URI = 'http://localhost:3000/callback'; // Cambia esto si usas un entorno de producción

let spotifyAccessToken = '';
let spotifyRefreshToken = '';

// Configura el bot de Twitch
const twitchClient = new tmi.Client({
    identity: {
        username: 'ZaisBot',
        password: 'oauth:l8xnhvm6qic340rabkqqhwcgjids3b'
    },
    channels: ['ZaisYT']
});

// Conéctate al chat de Twitch
twitchClient.connect();

// Escucha comandos en el chat
twitchClient.on('message', async (channel, tags, message, self) => {
    if (self) return;

    if (message.startsWith('!sr ')) {
        const songQuery = message.slice(13); // Extrae la consulta de la canción
        const trackUri = await searchSongOnSpotify(songQuery);

        if (trackUri) {
            const success = await addSongToSpotifyQueue(trackUri);
            if (success) {
                twitchClient.say(channel, `@${tags.username} tu canción ha sido añadida a la cola.`);
            } else {
                twitchClient.say(channel, `@${tags.username} tu canción ha sido añadida a la cola.`);
            }
        } else {
            twitchClient.say(channel, `@${tags.username} no se encontró ninguna canción con ese nombre.`);
        }
    }
});

// Autenticar con Spotify y obtener el token de acceso
async function authenticateWithSpotify() {
    const response = await axios.post('https://accounts.spotify.com/api/token', new URLSearchParams({
        grant_type: 'client_credentials'
    }), {
        headers: {
            'Authorization': 'Basic ' + Buffer.from(`${SPOTIFY_CLIENT_ID}:${SPOTIFY_CLIENT_SECRET}`).toString('base64'),
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    });

    spotifyAccessToken = response.data.access_token;
}

// Buscar canción en Spotify
async function searchSongOnSpotify(query) {
    if (!spotifyAccessToken) await authenticateWithSpotify();

    const response = await axios.get('https://api.spotify.com/v1/search', {
        params: {
            q: query,
            type: 'track',
            limit: 1
        },
        headers: {
            'Authorization': `Bearer ${spotifyAccessToken}`
        }
    });

    const track = response.data.tracks.items[0];
    return track ? track.uri : null;
}

// Añadir canción a la cola de reproducción de Spotify
async function addSongToSpotifyQueue(trackUri) {
    try {
        const response = await axios.post('https://api.spotify.com/v1/me/player/queue', null, {
            params: {
                uri: trackUri
            },
            headers: {
                'Authorization': `Bearer ${spotifyAccessToken}`
            }
        });

        return response.status === 204;
    } catch (error) {
        console.error('Error añadiendo la canción a la cola:', error);
        return false;
    }
}

// Servidor Express para manejar la autenticación de Spotify
app.get('/login', (req, res) => {
    const scope = 'user-modify-playback-state';
    res.redirect('https://accounts.spotify.com/authorize?' +
        new URLSearchParams({
            response_type: 'code',
            client_id: SPOTIFY_CLIENT_ID,
            scope: scope,
            redirect_uri: REDIRECT_URI
        }).toString());
});

app.get('/callback', async (req, res) => {
    const code = req.query.code || null;
    const response = await axios.post('https://accounts.spotify.com/api/token', new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: REDIRECT_URI,
        client_id: SPOTIFY_CLIENT_ID,
        client_secret: SPOTIFY_CLIENT_SECRET
    }), {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    });

    spotifyAccessToken = response.data.access_token;
    spotifyRefreshToken = response.data.refresh_token;
    res.send('Autenticación completada! Ahora puedes usar el bot.');
});

// Refrescar el token de acceso si expira
async function refreshSpotifyToken() {
    const response = await axios.post('https://accounts.spotify.com/api/token', new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: spotifyRefreshToken,
        client_id: SPOTIFY_CLIENT_ID,
        client_secret: SPOTIFY_CLIENT_SECRET
    }), {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    });

    spotifyAccessToken = response.data.access_token;
}

app.listen(3000, () => {
    console.log('Servidor de autenticación de Spotify corriendo en http://localhost:3000');
});

(async () => {
    const open = await import('open');
  
    // Abre una nueva ventana en el navegador predeterminado
    await open.default('http://localhost:3000/login', { arguments: ['--new-window'] });
})();

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});
