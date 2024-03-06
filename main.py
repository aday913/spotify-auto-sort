import logging
import sys

import spotipy
from yaml import load, Loader

log = logging.getLogger(__name__)


def get_liked_songs(sp: spotipy.Spotify):
    results = sp.current_user_saved_tracks()
    tracks = results["items"]
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])
    return tracks


def get_playlist_tracks(sp: spotipy.Spotify, playlist_id: str):
    results = sp.playlist_tracks(playlist_id)
    tracks = results["items"]
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])
    return tracks


def get_spotipy_client(client_id, client_secret, redirect) -> spotipy.Spotify:
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
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect,
            scope=SCOPES,
            open_browser=False,
        )
    )

    return sp


def sort_tracks(
    sp: spotipy.Spotify,
    tracks,
    genre_config: dict,
    track_ids: list,
    genres: list,
    artists: dict,
    fallback_playlist: str,
):
    for track in tracks:
        if track["track"]["id"] in track_ids:
            continue

        artist_id = track["track"]["artists"][0]["id"]
        if artist_id not in list(artists.keys()):
            artist = sp.artist(artist_id)
            artists[artist_id] = [i for i in artist["genres"]]
        single_word_genres = [i for i in artists[artist_id] if " " not in i]

        added_to_playlist = False
        for config in genre_config:
            for keyword in genre_config[config]["keywords"]:
                if keyword not in single_word_genres:
                    continue
                else:
                    log.info(
                        f' Adding track {track["track"]["name"]} to {config} playlist'
                    )
                    sp.playlist_add_items(
                        playlist_id=genre_config[config]["playlist_id"],
                        items=[track["track"]["uri"]],
                    )
                    added_to_playlist = True
                    break
        if not added_to_playlist:
            log.info(
                f' Could not find genre for {track["track"]["name"]}, adding to misc...'
            )
            sp.playlist_add_items(
                playlist_id=fallback_playlist, items=[track["track"]["uri"]]
            )

        track_ids.append(track["track"]["id"])

    return track_ids, genres, artists


def main(config):
    spotify_ci = config["spotify"]["client_id"]
    spotify_cs = config["spotify"]["client_secret"]
    spotify_redirect = config["spotify"]["redirect_url"]
    source_playlists = config["spotify"]["source_playlists"]
    sorted_genres = {}
    for genre in config["spotify"]["genres"]:
        sorted_genres[genre] = {
            "playlist_id": config["spotify"]["genres"][genre]["playlist_id"],
            "keywords": config["spotify"]["genres"][genre].get("keywords"),
        }
    fallback_playlist = config["spotify"]["fallback_playlist"]
    log.info(f"Using the following genre configuration: \n{sorted_genres}")

    log.info("Connecting to spotipy client...")
    sp = get_spotipy_client(spotify_ci, spotify_cs, spotify_redirect)
    log.info("Connected successfully")

    all_track_ids = []
    log.info("Getting all track ids already added to playlists")
    with open("added_tracks.txt", "r") as f:
        for i in f:
            all_track_ids.append(i.strip())
    log.info(
        f"Got the track ids of {len(all_track_ids)} tracks that have already been added"
    )

    all_genres_identified = []
    all_artists = {}

    log.info("Getting all songs from liked songs playlist")
    tracks = get_liked_songs(sp=sp)
    log.info(f"Number of tracks returned: {len(tracks)}")

    all_track_ids, all_genres_identified, all_artists = sort_tracks(
        sp=sp,
        tracks=tracks,
        genre_config=sorted_genres,
        track_ids=all_track_ids,
        genres=all_genres_identified,
        artists=all_artists,
        fallback_playlist=fallback_playlist,
    )

    for playlist in source_playlists:
        log.info(f"Grabbing all tracks from playlist {playlist}")
        tracks = get_playlist_tracks(sp=sp, playlist_id=playlist)
        log.info(f"Total tracks from playlist {playlist}: {len(tracks)}")
        all_track_ids, all_genres_identified, all_artists = sort_tracks(
            sp=sp,
            tracks=tracks,
            genre_config=sorted_genres,
            track_ids=all_track_ids,
            genres=all_genres_identified,
            artists=all_artists,
            fallback_playlist=fallback_playlist,
        )

    with open("added_tracks.txt", "w") as f:
        for i in all_track_ids:
            f.write(f"{i}\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s-%(levelname)s: %(message)s"
    )

    log = logging.getLogger(__name__)

    log.debug("Attempting to read configuration yaml file")
    try:
        with open("config.yaml", "r") as yml:
            config = load(yml, Loader=Loader)
        log.debug("Successfully read in config.yaml file as yaml dict")
    except Exception as error:
        log.error(f"Could not load configuration file: {error}")
        sys.exit(1)
    main(config)
