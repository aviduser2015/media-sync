import logging
import os
from typing import Dict, Any, List
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager

from . import models, database, services
from .models import GlobalSettings, RadarrConfig, SonarrConfig, PlexConfig

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- DATABASE SETUP ---
models.Base.metadata.create_all(bind=database.engine)

# --- HELPERS ---
def get_setting(db: Session, key: str, default: str = ""):
    item = db.query(models.Setting).filter(models.Setting.key == key).first()
    return item.value if item else default

def set_setting(db: Session, key: str, value: str):
    item = db.query(models.Setting).filter(models.Setting.key == key).first()
    if not item:
        item = models.Setting(key=key, value=value, type="str")
        db.add(item)
    else:
        item.value = value
    db.commit()

def upsert_sync_map(db: Session, rating_key: str, arr_id: int, media_type: str, status: str):
    record = db.query(models.SyncMap).filter(models.SyncMap.plex_rating_key == rating_key).first()
    if not record:
        record = models.SyncMap(plex_rating_key=rating_key, arr_id=arr_id, type=media_type, status=status)
        db.add(record)
    else:
        record.arr_id = arr_id
        record.type = media_type
        record.status = status
    db.commit()

# --- SYNC LOGIC ---
def process_items(db: Session, service, items: List[Dict[str, Any]], root: str, quality: int, media_type: str):
    added, skipped, errors = [], [], []

    for item in items:
        title = item.get("title") or "Unknown"
        rating_key = str(item.get("rating_key") or title)
        tmdb_id = item.get("tmdb_id")
        year = item.get("year") or ""

        search_term = f"tmdb:{tmdb_id}" if tmdb_id else f"{title} {year}".strip()
        lookup = service.lookup_movie(search_term) if media_type == "movie" else service.lookup_series(search_term)

        if not lookup:
            skipped.append({"title": title, "reason": "Not found in Arr lookup"})
            continue

        existing_id = lookup.get("id")
        if existing_id:
            has_file = service.has_file(existing_id)
            status = "downloaded" if has_file else "added"
            upsert_sync_map(db, rating_key, existing_id, media_type, status)
            skipped.append({"title": title, "reason": "Already in library" if has_file else "Already monitored"})
            continue

        resp = service.add_movie(lookup, root, quality) if media_type == "movie" else service.add_series(lookup, root, quality)
        if resp.get("success"):
            arr_id = resp["data"].get("id")
            upsert_sync_map(db, rating_key, arr_id, media_type, "added")
            added.append({"title": title, "arr_id": arr_id})
        else:
            errors.append({"title": title, "error": resp.get("error", "Unknown error")})

    return {"added": added, "skipped": skipped, "errors": errors}

def run_sync(db: Session) -> Dict[str, Any]:
    logger.info("Starting sync job...")
    r_url = get_setting(db, "radarr.url")
    r_key = get_setting(db, "radarr.api_key")
    r_quality = int(get_setting(db, "radarr.quality_profile", "1"))
    r_root = get_setting(db, "radarr.root_folder", "/movies")

    s_url = get_setting(db, "sonarr.url")
    s_key = get_setting(db, "sonarr.api_key")
    s_quality = int(get_setting(db, "sonarr.quality_profile", "1"))
    s_root = get_setting(db, "sonarr.root_folder", "/tv")

    p_token = get_setting(db, "plex.token")

    if not p_token:
        raise HTTPException(status_code=400, detail="Plex token not configured")

    plex = services.PlexService("", p_token)
    watchlist = plex.get_watchlist()
    if not watchlist:
        logger.info("Watchlist empty or unreachable.")
        return {"movies": {"added": [], "skipped": [], "errors": []}, "shows": {"added": [], "skipped": [], "errors": []}}

    movies = [item for item in watchlist if item.get("type") == "movie"]
    shows = [item for item in watchlist if item.get("type") == "show"]

    stats = {"movies": {"added": [], "skipped": [], "errors": []}, "shows": {"added": [], "skipped": [], "errors": []}}

    if r_url and r_key:
        radarr = services.RadarrService(r_url, r_key)
        stats["movies"] = process_items(db, radarr, movies, r_root, r_quality, "movie")
    else:
        logger.warning("Radarr not configured; skipping movies.")

    if s_url and s_key:
        sonarr = services.SonarrService(s_url, s_key)
        stats["shows"] = process_items(db, sonarr, shows, s_root, s_quality, "show")
    else:
        logger.info("Sonarr not configured; skipping shows.")

    # Mark downloads as completed where applicable
    for entry in db.query(models.SyncMap).all():
        if not entry.arr_id:
            continue
        if entry.type == "movie" and r_url and r_key:
            radarr = services.RadarrService(r_url, r_key)
            if radarr.has_file(entry.arr_id):
                entry.status = "downloaded"
        if entry.type == "show" and s_url and s_key:
            sonarr = services.SonarrService(s_url, s_key)
            if sonarr.has_file(entry.arr_id):
                entry.status = "downloaded"
    db.commit()

    return stats

# --- WORKER FUNCTION ---
def background_sync_job():
    db = database.SessionLocal()
    try:
        stats = run_sync(db)
        logger.info(f"Sync complete. Movies added: {len(stats['movies']['added'])}, Shows added: {len(stats['shows']['added'])}")
    except Exception as e:
        logger.error(f"Sync job failed: {e}")
    finally:
        db.close()

# --- LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(background_sync_job, IntervalTrigger(minutes=60), id="sync_job", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started.")
    yield
    scheduler.shutdown()

app = FastAPI(title="Media Sync Manager", version="1.0.0", lifespan=lifespan)

# --- API ROUTES ---

@app.get("/api/config", response_model=GlobalSettings)
def get_config(db: Session = Depends(database.get_db)):
    return GlobalSettings(
        plex=PlexConfig(
            url=get_setting(db, "plex.url", "http://localhost:32400"),
            token=get_setting(db, "plex.token", "")
        ),
        radarr=RadarrConfig(
            url=get_setting(db, "radarr.url", "http://radarr:7878"),
            api_key=get_setting(db, "radarr.api_key", ""),
            quality_profile_id=int(get_setting(db, "radarr.quality_profile", "1")),
            root_folder_path=get_setting(db, "radarr.root_folder", "/movies"),
            enabled=bool(get_setting(db, "radarr.api_key", ""))
        ),
        sonarr=SonarrConfig(
            url=get_setting(db, "sonarr.url", "http://sonarr:8989"),
            api_key=get_setting(db, "sonarr.api_key", ""),
            quality_profile_id=int(get_setting(db, "sonarr.quality_profile", "1")),
            root_folder_path=get_setting(db, "sonarr.root_folder", "/tv"),
            enabled=bool(get_setting(db, "sonarr.api_key", ""))
        )
    )

@app.put("/api/config")
def update_config(settings: GlobalSettings, db: Session = Depends(database.get_db)):
    set_setting(db, "radarr.url", settings.radarr.url)
    set_setting(db, "radarr.api_key", settings.radarr.api_key)
    set_setting(db, "radarr.quality_profile", str(settings.radarr.quality_profile_id))
    set_setting(db, "radarr.root_folder", settings.radarr.root_folder_path)

    set_setting(db, "sonarr.url", settings.sonarr.url)
    set_setting(db, "sonarr.api_key", settings.sonarr.api_key)
    set_setting(db, "sonarr.quality_profile", str(settings.sonarr.quality_profile_id))
    set_setting(db, "sonarr.root_folder", settings.sonarr.root_folder_path)

    set_setting(db, "plex.url", settings.plex.url)
    set_setting(db, "plex.token", settings.plex.token)
    return {"message": "Configuration saved"}

@app.post("/api/services/test")
def test_service(payload: dict = Body(...)):
    service_type = payload.get("service_type")
    url = payload.get("url")
    api_key = payload.get("api_key")
    if service_type == "radarr":
        return services.RadarrService(url, api_key).test_connection()
    elif service_type == "sonarr":
        return services.SonarrService(url, api_key).test_connection()
    elif service_type == "plex":
        return services.PlexService(url, api_key).test_connection()
    return {"success": False, "message": "Unknown service"}

@app.post("/api/sync/run")
def manual_sync_trigger(db: Session = Depends(database.get_db)):
    stats = run_sync(db)
    combined_added = stats["movies"]["added"] + stats["shows"]["added"]
    combined_skipped = stats["movies"]["skipped"] + stats["shows"]["skipped"]
    return {
        "success": True,
        "message": "Sync complete",
        "stats": {
            "added": combined_added,
            "skipped": combined_skipped,
            "details": stats
        }
    }

# --- FRONTEND STATIC FILES ---
# This must be at the END of the file
if os.path.isdir("static"):
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return FileResponse("static/index.html")
