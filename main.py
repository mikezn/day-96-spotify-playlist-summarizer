import os
import spotlib
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import re

# Spotify API credentials and settings
APP_CLIENT_ID = os.environ.get("APP_CLIENT_ID")
APP_CLIENT_SECRET = os.environ.get("APP_CLIENT_SECRET")
APP_REDIRECT_URI = "http://127.0.0.1:8080/callback"
SCOPE = "playlist-modify-public playlist-modify-private"

playlist_data = {}

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", playlists=playlist_data)

@app.route("/playlist/<playlist_id>")
def playlist_view(playlist_id):
    playlist = None
    playlist_name = None

    for name, data in playlist_data.items():
        if data["id"] == playlist_id:
            playlist = data
            playlist_name = name
            break

    if not playlist:
        return "Playlist not found", 404

    # Build list of playlists sorted by date
    dated_playlists = []
    for name, details in playlist_data.items():
        match = re.search(r"\d{2}/\d{2}/\d{4}", name)
        if match:
            date_str = match.group()
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            dated_playlists.append((name, date_obj, details["id"]))

    dated_playlists.sort(key=lambda x: x[1])

    # Build timeline data
    timeline_data = []
    for track in playlist["tracks"]:
        track_entry = {
            "track": f"{track['name']} - {track['artist']}",
            "presence": []
        }
        for pl_name, _, _ in dated_playlists:
            appeared = any(t["id"] == track["id"] for t in playlist_data[pl_name]["tracks"])
            match = re.search(r"\d{2}/\d{2}/\d{4}", pl_name)
            date_str = match.group() if match else "Unknown"
            track_entry["presence"].append({
                "date": date_str,
                "present": appeared
            })
        timeline_data.append(track_entry)

    return render_template(
        "playlist_view.html",
        playlist_name=playlist_name,
        songs=timeline_data,
        playlists=playlist_data
    )


@app.route("/refresh", methods=["POST"])
def refresh_data():
    global playlist_data
    playlist_data = load_spotify_data()
    return redirect(url_for('home'))


def load_spotify_data() -> dict:
    data = {}
    sp = spotlib.authenticate_spotify(app_client_id=APP_CLIENT_ID,
                                      app_client_secret=APP_CLIENT_SECRET,
                                      app_redirect_uri=APP_REDIRECT_URI,
                                      scope=SCOPE)

    playlists = spotlib.get_all_playlists(sp)
    data = spotlib.build_playlist_data(playlists, sp)

    with open('spotify_data.txt', "w", encoding="utf-8") as f:
        f.write(str(data))
    print(f"Saved")

    return data



def load_local_data() -> dict:
    try:
        with open("spotify_data.txt", "r", encoding="utf-8") as f:
            return eval(f.read())

    except FileNotFoundError:
        print(f"File not found")
        return load_spotify_data()

    except PermissionError:
        print(f"Permission denied when trying to open")
        return load_spotify_data()

    except UnicodeDecodeError:
        print(f"Encoding issue reading file")
        return load_spotify_data()

    except Exception as e:
        print(f"Unexpected error opening file")
        return load_spotify_data()

def get_song_timeline(song_id, all_playlists):
    appearances = []
    for name, data in all_playlists.items():
        for track in data["tracks"]:
            if track["id"] == song_id:
                # Extract date from playlist name
                match = re.search(r"\d{2}/\d{2}/\d{4}", name)
                if match:
                    date_str = match.group()
                    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                    appearances.append(date_obj)
    return sorted(appearances)

def main():
    global playlist_data
    # playlist_data = load_spotify_data()
    playlist_data = load_local_data()
    print('Hello! Spotify data loaded.')
    app.run(debug=True)

if __name__ == "__main__":
    main()
