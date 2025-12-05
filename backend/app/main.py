import logging
import os
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

# --- WORKER FUNCTION ---
def background_sync_job():
    logger.info("Starting scheduled sync job...")
    db = database.SessionLocal()
    try:
        # Load Settings
        r_url = get_setting(db, "radarr.url")
        r_key = get_setting(db, "radarr.api_key")
        r_quality = int(get_setting(db, "radarr.quality_profile", "1"))
        r_root = get_setting(db, "radarr.root_folder", "/movies")
        p_token = get_setting(db, "plex.token")

        if not r_url or not r_key or not p_token:
            logger.warning("Scheduled sync skipped: Settings incomplete")
            return

        radarr = services.RadarrService(r_url, r_key)
        plex = services.PlexService("", p_token)

        logger.info("Fetching Plex Watchlist...")
        watchlist = plex.get_watchlist()
        
        if not watchlist:
            logger.info("Watchlist empty or unreachable.")
            return

        added_count = 0
        for item in watchlist:
            term = f"tmdb:{item.get('tmdb_id')}" if item.get('tmdb_id') else f"{item['title']} {item['year']}"
            lookup = radarr.lookup_movie(term)
            
            if lookup and not lookup.get("id"):
                logger.info(f"Adding movie: {item['title']}")
                radarr.add_movie(lookup, r_root, r_quality)
                added_count += 1
        
        logger.info(f"Sync complete. Added {added_count} movies.")
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
            root_folder_path=get_setting(db, "radarr.root_folder", "/movies")
        ),
        sonarr=SonarrConfig(
            url=get_setting(db, "sonarr.url", "http://sonarr:8989"),
            api_key=get_setting(db, "sonarr.api_key", "")
        )
    )

@app.put("/api/config")
def update_config(settings: GlobalSettings, db: Session = Depends(database.get_db)):
    set_setting(db, "radarr.url", settings.radarr.url)
    set_setting(db, "radarr.api_key", settings.radarr.api_key)
    set_setting(db, "radarr.quality_profile", str(settings.radarr.quality_profile_id))
    set_setting(db, "radarr.root_folder", settings.radarr.root_folder_path)
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
    elif service_type == "plex":
        return services.PlexService(url, api_key).test_connection()
    return {"success": False, "message": "Unknown service"}

@app.post("/api/sync/run")
def manual_sync_trigger():
    background_sync_job()
    return {"success": True, "message": "Sync job started in background"}

# --- FRONTEND STATIC FILES ---
# This must be at the END of the file
if os.path.isdir("static"):
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return FileResponse("static/index.html")