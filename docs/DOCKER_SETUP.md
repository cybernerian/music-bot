# MusicBrainz Docker Setup
Docker setup to access the full MusicBrainz database.

## Prerequisites

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and make sure it's running before proceeding.

## Setup

```zsh
git clone https://github.com/metabrainz/musicbrainz-docker.git
```

```zsh
cd musicbrainz-docker
```

```zsh
admin/configure with alt-db-only-mirror
docker compose build
docker compose run --rm db createdb.sh -fetch
docker compose up -d
```

That's it. The database runs on `localhost:5432` with username `musicbrainz` and password `musicbrainz`.

## Test the connection

Navigate back to the `music-recommender` project root first, then navigate to `test_musicbrainz.py` to run the file:

```zsh
cd ../music-recommender
```

It will connect to the database and print 10 random songs from a randomly selected genre. If it works, you're good to go.
