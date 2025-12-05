from sqlalchemy import Column, String, Integer, DateTime
from .database import Base
from pydantic import BaseModel
from datetime import datetime

# --- DATABASE TABLES ---
class Setting(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String)
    type = Column(String)

class SyncMap(Base):
    __tablename__ = "sync_map"
    plex_rating_key = Column(String, primary_key=True, index=True)
    arr_id = Column(Integer, index=True)
    type = Column(String)  # 'movie' or 'show'
    status = Column(String, default="added")  # added | downloaded

class JobHistory(Base):
    __tablename__ = "job_history"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    job_type = Column(String)
    status = Column(String)
    details = Column(String)

# --- API SCHEMAS ---
class RadarrConfig(BaseModel):
    url: str = "http://localhost:7878"
    api_key: str = ""
    quality_profile_id: int = 1
    root_folder_path: str = "/movies"
    enabled: bool = False

class SonarrConfig(BaseModel):
    url: str = "http://localhost:8989"
    api_key: str = ""
    quality_profile_id: int = 1
    root_folder_path: str = "/tv"
    enabled: bool = False

class PlexConfig(BaseModel):
    url: str = "http://localhost:32400"
    token: str = ""
    enable_watchlist_cleanup: bool = False

class GlobalSettings(BaseModel):
    plex: PlexConfig
    radarr: RadarrConfig
    sonarr: SonarrConfig
