import logging
import sys

import spotipy
from yaml import load, Loader

log = logging.getLogger(__name__)

# Function to get liked songs
def get_liked_songs(sp):
    results = sp.current_user_saved_tracks()
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

def main(config):
    spotify_ci          = config['spotify']['client_id']
    spotify_cs          = config['spotify']['client_secret']
    spotify_redirect    = config['spotify']['redirect_url']

    SCOPES = [
            "user-library-modify",
            "user-library-read",
            "user-top-read", 
            "user-read-recently-played",
            "playlist-read-private",
            "playlist-read-collaborative",
            "playlist-modify-private",
            "playlist-modify-public",
    ]

    sp = spotipy.Spotify(
        auth_manager=spotipy.SpotifyOAuth(
            client_id=spotify_ci, 
            client_secret=spotify_cs, 
            redirect_uri=spotify_redirect,
            scope=SCOPES,
            open_browser=False
        )
    )

    tracks = get_liked_songs(sp=sp)
    log.info(f'Number of tracks returned: {len(tracks)}')
    log.info(f'First index of tracks: {tracks[0]}')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s-%(levelname)s: %(message)s')

    log = logging.getLogger(__name__)

    log.debug('Attempting to read configuration yaml file')
    try:
        with open('config.yaml', 'r') as yml:
            config = load(yml, Loader=Loader)
        log.debug('Successfully read in config.yaml file as yaml dict')
    except Exception as error:
        log.error(f'Could not load configuration file: {error}')
        sys.exit(1)
    main(config)
