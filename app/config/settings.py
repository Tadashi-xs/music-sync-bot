import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class TelegramConfig:
    token: str


@dataclass(frozen=True)
class SpotifyConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: str = (
        "playlist-modify-public "
        "playlist-modify-private "
        "user-library-modify "
        "user-library-read"
    )


@dataclass(frozen=True)
class OAuthConfig:
    host: str
    port: int


@dataclass(frozen=True)
class Config:
    telegram: TelegramConfig
    spotify: SpotifyConfig
    oauth: OAuthConfig


def load_config() -> Config:
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")

    spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
    spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    spotify_redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

    oauth_host = os.getenv("OAUTH_HOST", "0.0.0.0")
    oauth_port = int(os.getenv("OAUTH_PORT", "8080"))

    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    if not spotify_client_id or not spotify_client_secret or not spotify_redirect_uri:
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET / SPOTIFY_REDIRECT_URI must be set"
        )

    return Config(
        telegram=TelegramConfig(
            token=telegram_token,
        ),
        spotify=SpotifyConfig(
            client_id=spotify_client_id,
            client_secret=spotify_client_secret,
            redirect_uri=spotify_redirect_uri,
        ),
        oauth=OAuthConfig(
            host=oauth_host,
            port=oauth_port,
        ),
    )
