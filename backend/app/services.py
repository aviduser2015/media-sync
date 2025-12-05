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
    def get_movies(self) -> List[int]:
        try:
            resp = requests.get(f"{self.url}/api/v3/movie", headers=self.headers)
            return [m.get("tmdbId") for m in resp.json() if m.get("tmdbId")]
        except:
            return []

    def lookup_movie(self, term: str) -> Optional[Dict]:
        safe_term = urllib.parse.quote(term)
        try:
            resp = requests.get(f"{self.url}/api/v3/movie/lookup?term={safe_term}", headers=self.headers)
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
        try:
            resp = requests.post(f"{self.url}/api/v3/movie", json=payload, headers=self.headers)
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
            resp = requests.get(url, headers=self.headers)
            data = resp.json()
            items = []
            if "MediaContainer" in data and "Metadata" in data["MediaContainer"]:
                for item in data["MediaContainer"]["Metadata"]:
                    if item.get("type") == "movie":
                        items.append({"title": item.get("title"), "year": item.get("year"), "tmdb_id": None}) 
            return items
        except:
            return []