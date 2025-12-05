import requests
import urllib.parse
from typing import Dict, Any, List, Optional

class BaseArrService:
    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {"X-Api-Key": api_key}

    def test_connection(self) -> Dict[str, Any]:
        try:
            endpoint = f"{self.url}/api/v3/system/status"
            resp = requests.get(endpoint, headers=self.headers, timeout=5)
            resp.raise_for_status()
            return {"success": True, "version": resp.json().get("version"), "message": "Connection successful"}
        except Exception as e:
            return {"success": False, "message": str(e)}

class RadarrService(BaseArrService):
    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.url}/api/v3/movie/{item_id}", headers=self.headers, timeout=10)
            if resp.status_code == 404:
                return None
            return resp.json()
        except:
            return None

    def has_file(self, item_id: int) -> bool:
        movie = self.get_item(item_id)
        return bool(movie and movie.get("hasFile"))

    def lookup_movie(self, term: str) -> Optional[Dict]:
        safe_term = urllib.parse.quote(term)
        try:
            resp = requests.get(f"{self.url}/api/v3/movie/lookup?term={safe_term}", headers=self.headers, timeout=15)
            results = resp.json()
            return results[0] if results else None
        except:
            return None

    def add_movie(self, movie_json: Dict, root_folder: str, quality_profile: int) -> Dict:
        payload = movie_json.copy()
        payload["rootFolderPath"] = root_folder
        payload["qualityProfileId"] = quality_profile
        payload["monitored"] = True
        payload["addOptions"] = {"searchForMovie": True}
        payload.setdefault("tmdbId", movie_json.get("tmdbId"))
        payload.setdefault("title", movie_json.get("title"))
        payload.setdefault("year", movie_json.get("year"))
        try:
            resp = requests.post(f"{self.url}/api/v3/movie", json=payload, headers=self.headers, timeout=20)
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

class SonarrService(BaseArrService):
    def get_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.url}/api/v3/series/{item_id}", headers=self.headers, timeout=10)
            if resp.status_code == 404:
                return None
            return resp.json()
        except:
            return None

    def has_file(self, item_id: int) -> bool:
        series = self.get_item(item_id)
        if not series:
            return False
        if series.get("statistics", {}).get("episodeFileCount", 0) > 0:
            return True
        for season in series.get("seasons", []):
            stats = season.get("statistics", {})
            if stats.get("episodeFileCount", 0) > 0:
                return True
        return False

    def lookup_series(self, term: str) -> Optional[Dict]:
        safe_term = urllib.parse.quote(term)
        try:
            resp = requests.get(f"{self.url}/api/v3/series/lookup?term={safe_term}", headers=self.headers, timeout=15)
            results = resp.json()
            return results[0] if results else None
        except:
            return None

    def add_series(self, series_json: Dict, root_folder: str, quality_profile: int) -> Dict:
        payload = series_json.copy()
        payload["rootFolderPath"] = root_folder
        payload["qualityProfileId"] = quality_profile
        payload["monitored"] = True
        payload["addOptions"] = {"searchForMissingEpisodes": True}
        payload.setdefault("title", series_json.get("title"))
        payload.setdefault("tvdbId", series_json.get("tvdbId"))
        try:
            resp = requests.post(f"{self.url}/api/v3/series", json=payload, headers=self.headers, timeout=20)
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

class PlexService:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.token = token
        self.headers = {"X-Plex-Token": token, "Accept": "application/json"}

    def test_connection(self) -> Dict[str, Any]:
        try:
            resp = requests.get("https://plex.tv/api/v2/user", headers=self.headers, timeout=5)
            resp.raise_for_status()
            return {"success": True, "message": "Plex Token Valid"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_watchlist(self) -> List[Dict]:
        try:
            url = "https://metadata.provider.plex.tv/library/sections/watchlist/all"
            resp = requests.get(url, headers=self.headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            items: List[Dict[str, Any]] = []
            if "MediaContainer" in data and "Metadata" in data["MediaContainer"]:
                for item in data["MediaContainer"]["Metadata"]:
                    item_type = item.get("type")
                    if item_type not in ("movie", "show"):
                        continue
                    guid = item.get("guid", "") or ""
                    tmdb_id = None
                    if guid.startswith("tmdb://"):
                        tmdb_id = guid.split("://", 1)[1].split("?")[0]
                    items.append({
                        "rating_key": str(item.get("ratingKey")),
                        "type": item_type,
                        "title": item.get("title"),
                        "year": item.get("year"),
                        "tmdb_id": tmdb_id,
                    })
            return items
        except Exception:
            return []
