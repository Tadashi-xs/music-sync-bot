import time
import requests


class SpotifyAPIError(Exception):
    pass


class SpotifyUserClient:
    def __init__(self, access_token: str):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, **kwargs):
        response = requests.request(
            method,
            url,
            headers=self.headers,
            timeout=15,
            **kwargs,
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            time.sleep(retry_after + 0.5)
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=15,
                **kwargs,
            )

        response.raise_for_status()

        if response.status_code == 204 or not response.text:
            return None

        return response.json()


    def get_me(self):
        return self._request("GET", "https://api.spotify.com/v1/me")

    def search_track_full(self, query: str):
        data = self._request(
            "GET",
            "https://api.spotify.com/v1/search",
            params={
                "q": query,
                "type": "track",
                "limit": 1,
            },
        )
        items = data.get("tracks", {}).get("items", []) if data else []
        return items[0] if items else None

    def is_track_saved(self, track_id: str) -> bool:
        result = self._request(
            "GET",
            "https://api.spotify.com/v1/me/tracks/contains",
            params={"ids": track_id},
        )
        return bool(result and result[0])

    def save_tracks(self, ids: list[str]):
        for i in range(0, len(ids), 50):
            self._request(
                "PUT",
                "https://api.spotify.com/v1/me/tracks",
                json={"ids": ids[i:i + 50]},
            )

    def remove_saved_tracks(self, ids: list[str]):
        for i in range(0, len(ids), 50):
            self._request(
                "DELETE",
                "https://api.spotify.com/v1/me/tracks",
                json={"ids": ids[i:i + 50]},
            )

    def get_saved_tracks(self, limit: int = 20, offset: int = 0):
        return self._request(
            "GET",
            "https://api.spotify.com/v1/me/tracks",
            params={
                "limit": limit,
                "offset": offset,
            },
        )
