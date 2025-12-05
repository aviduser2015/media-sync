import requests
import urllib.parse
import xml.etree.ElementTree as ET
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

    def _extract_ids_from_guid(self, guid: str) -> Dict[str, Optional[str]]:
        """Pull TMDB/TVDB/IMDB ids plus any type hints from a Plex guid string."""
        ids: Dict[str, Optional[str]] = {"tmdb_id": None, "tvdb_id": None, "imdb_id": None, "type_hint": None}
        if not guid:
            return ids

        raw = guid.lower()
        # Type hint from known prefixes
        if raw.startswith("plex://show/") or "/show/" in raw or "/tv/" in raw:
            ids["type_hint"] = "show"
        elif raw.startswith("plex://movie/") or "/movie/" in raw:
            ids["type_hint"] = "movie"

        def _clean(val: str) -> str:
            return val.split("?")[0].split("/")[-1]

        if "tmdb://" in raw:
            ids["tmdb_id"] = _clean(guid.split("://", 1)[1])
            if "/movie/" in raw:
                ids["type_hint"] = ids["type_hint"] or "movie"
            if "/tv/" in raw:
                ids["type_hint"] = ids["type_hint"] or "show"
        if "tvdb://" in raw:
            ids["tvdb_id"] = _clean(guid.split("://", 1)[1])
            ids["type_hint"] = ids["type_hint"] or "show"
        if "imdb://" in raw:
            ids["imdb_id"] = _clean(guid.split("://", 1)[1])
            # IMDB can be movie or show; leave type hint unchanged

        return ids

    def _fetch_metadata(self, rating_key: str) -> Optional[Dict[str, Any]]:
        """Look up metadata from Plex provider to disambiguate movies vs series."""
        if not rating_key:
            return None
        try:
            endpoint = f"https://metadata.provider.plex.tv/library/metadata/{urllib.parse.quote(str(rating_key))}"
            resp = requests.get(endpoint, headers=self.headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            meta = data.get("MediaContainer", {}).get("Metadata", [])
            if not meta:
                return None
            item = meta[0]
            guid = item.get("guid", "") or ""
            ids = self._extract_ids_from_guid(guid)
            tmdb_id = ids.get("tmdb_id")
            if not tmdb_id and guid.startswith("tmdb://"):
                tmdb_id = guid.split("://", 1)[1].split("?")[0].split("/")[-1]
            return {
                "type": item.get("type"),
                "title": item.get("title"),
                "year": item.get("year"),
                "tmdb_id": tmdb_id,
                "thumb": item.get("thumb"),
                "summary": item.get("summary"),
                "rating_key": item.get("ratingKey") or rating_key,
                "guid_type_hint": ids.get("type_hint"),
            }
        except Exception:
            return None

    def _infer_media_type(self, guid: str, category: str, link: str) -> Optional[str]:
        """Best-effort type detection from guid/category/link strings."""
        for val in (guid, category, link):
            if not val:
                continue
            lower = val.lower()
            if "show" in lower or "series" in lower or "/tv/" in lower:
                return "show"
            if "movie" in lower or "film" in lower:
                return "movie"
        return None

    def _parse_rss_feed(self, url: str, source: str) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(url, headers={"Accept": "application/rss+xml"}, timeout=20)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            items: List[Dict[str, Any]] = []
            for item in root.iter("item"):
                title = item.findtext("title") or "Untitled"
                link = item.findtext("link") or ""
                guid = item.findtext("guid") or item.findtext("id") or link
                # Attempt to extract a rating key or tmdb/imdb id from the guid/link
                rating_key = ""
                if "metadata" in link:
                    parts = link.rstrip("/").split("/")
                    rating_key = parts[-1]
                elif guid:
                    rating_key = guid
                poster = ""
                thumb = item.find("{http://search.yahoo.com/mrss/}thumbnail")
                if thumb is not None:
                    poster = thumb.attrib.get("url", "")
                year = ""
                description = item.findtext("description") or ""
                # Best-effort year extraction
                for token in title.split():
                    if token.isdigit() and len(token) == 4:
                        year = token
                        break
                category = item.findtext("category") or ""
                ids = self._extract_ids_from_guid(guid)
                type_hint = ids.get("type_hint") or self._infer_media_type(guid, category, link) or "movie"

                # Fetch Plex metadata to enrich and to ensure we have the canonical rating key
                meta = self._fetch_metadata(rating_key)
                resolved_type = meta.get("type") if meta else type_hint
                tmdb_id = ids.get("tmdb_id") or (meta.get("tmdb_id") if meta else None)
                poster_final = meta.get("thumb") if meta and meta.get("thumb") else poster
                year_final = str(meta.get("year")) if meta and meta.get("year") else year
                summary_final = meta.get("summary") if meta and meta.get("summary") else description
                rating_key_final = meta.get("rating_key") if meta and meta.get("rating_key") else rating_key
                # If year still missing, try to parse from title tokens
                if not year_final:
                    for token in title.split():
                        if token.isdigit() and len(token) == 4:
                            year_final = token
                            break

                items.append({
                    "title": meta.get("title") if meta and meta.get("title") else title,
                    "rating_key": rating_key_final,
                    "type": resolved_type or "movie",
                    "year": year_final,
                    "poster": poster_final,
                    "tmdb_id": tmdb_id,
                    "source": source,
                    "summary": summary_final,
                })
            return items
        except Exception:
            return []

    def get_rss_watchlists(self, my_url: str, friend_url: str) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "mine": self._parse_rss_feed(my_url, "mine") if my_url else [],
            "friends": self._parse_rss_feed(friend_url, "friends") if friend_url else []
        }

    def remove_from_watchlist(self, rating_key: str) -> Dict[str, Any]:
        """
        Attempt to remove an item from the Plex watchlist.
        Note: Plex uses provider metadata ids; rating_key must match the Plex metadata id.
        """
        try:
            endpoint = f"https://metadata.provider.plex.tv/library/metadata/{urllib.parse.quote(str(rating_key))}/unwatchlist"
            resp = requests.put(endpoint, headers=self.headers, timeout=10)
            if resp.status_code not in (200, 201, 204):
                # Try POST fallback in case Plex expects it
                resp = requests.post(endpoint, headers=self.headers, timeout=10)
            success = resp.status_code in (200, 201, 204)
            return {"success": success, "status_code": resp.status_code, "body": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
