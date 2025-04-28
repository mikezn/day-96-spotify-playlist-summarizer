import spotipy
from spotipy import SpotifyOAuth
import re
from datetime import datetime

def authenticate_spotify(app_client_id, app_client_secret, app_redirect_uri, scope):
    """
    Authenticates with Spotify and returns a Spotipy client instance.
    """
    sp_oauth = SpotifyOAuth(
        client_id=app_client_id,
        client_secret=app_client_secret,
        redirect_uri=app_redirect_uri,
        scope=scope,
        cache_path=".cache"
    )
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    return sp



# Function to fetch all user playlists
def get_all_playlists(sp):
    playlists = []
    offset = 0
    while True:
        batch = sp.current_user_playlists(limit=50, offset=offset)
        playlists.extend(batch['items'])
        if batch['next']:
            offset += 50
        else:
            break
    return playlists


def build_playlist_data(pl_data, sp):
    playlist_data = {}
    user_id = sp.me()['id']
    playlists = pl_data

    for pl in playlists:
        if pl['owner']['id'] != user_id or not 'DD' in pl['name']:
            continue  # only include your own playlists

        pl_id = pl['id']
        pl_name = pl['name']
        print(f"Loading: {pl_name}")
        tracks = []
        offset = 0

        while True:
            results = sp.playlist_items(pl_id, offset=offset,
                                        fields='items.track.id,items.track.name,items.track.artists,next')
            for item in results['items']:
                track = item['track']
                if track and track['id']:  # skip local or unavailable tracks
                    tracks.append({
                        "id": track['id'],
                        "name": track['name'],
                        "artist": track['artists'][0]['name']
                    })
            if results['next']:
                offset += 100
            else:
                break

        playlist_data[pl_name] = {
            "id": pl_id,
            "tracks": tracks
        }

    return playlist_data





def format_month_abbr(month_str):
    """Take the first 3 letters and capitalize for datetime compatibility."""
    return month_str.strip()[:3].capitalize()

def update_dd_playlist_names(sp):
    playlists = get_all_playlists(sp)
    user_id = sp.me()['id']
    rename_log = {}

    for pl in playlists:
        name = pl['name']
        pl_id = pl['id']

        if name.startswith("DD"):
            # Match: DD <day> <month> <year> <rest of title (optional)>
            match = re.match(r"DD\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})(.*)", name)
            if match:
                day, month_raw, year, rest = match.groups()
                month_abbr = format_month_abbr(month_raw)

                try:
                    formatted_date = datetime.strptime(f"{day} {month_abbr} {year}", "%d %b %Y").strftime("%d/%m/%Y")
                    new_name = f"DD {formatted_date}{rest}"
                    rename_log[pl_id] = {"old_name": name, "new_name": new_name}

                    if name != new_name:
                        sp.user_playlist_change_details(user=user_id, playlist_id=pl_id, name=new_name)
                except ValueError:
                    rename_log[pl_id] = {"old_name": name, "new_name": "SKIPPED - Invalid date"}
            else:
                rename_log[pl_id] = {"old_name": name, "new_name": "SKIPPED - No date pattern"}

    # Show all changes and skips
    for pid, entry in rename_log.items():
        print(f"{pid}: {entry['old_name']} → {entry['new_name']}")

    return rename_log