@echo off
pip install flask requests twitchio spotipy
cls
start http://127.0.0.1:5000/
title ZSSR (Zais Spotify Song Request)
python main.py
exit /b