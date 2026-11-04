"""Booking-bound location APIs. Precise worker coordinates are only visible to the job owner."""
import asyncio, hashlib, json, logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from firebase_auth import authenticated_user, require_role, verify_firebase_token
from models import Job, Shop, User, WorkerLocation, PresenceSession, BackendAuthSession

router=APIRouter(tags=["Maps and tracking"])
logger=logging.getLogger(__name__)

class TrackingHub:
    """In-process WebSocket fanout. Each ASGI worker owns its connected sockets."""
    def __init__(self):
        self._clients: dict[str, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, job_id: str, ws: WebSocket):
        self._loop=asyncio.get_running_loop()
        await ws.accept()
        self._clients.setdefault(job_id,set()).add(ws)

    async def disconnect(self, job_id: str, ws: WebSocket):
        clients=self._clients.get(job_id)
        if clients:
            clients.discard(ws)
            if not clients: self._clients.pop(job_id,None)

    async def _broadcast(self, job_id: str, payload: dict, close: bool=False):
        clients=list(self._clients.get(job_id,set()))
        for ws in clients:
            try:
                await ws.send_json(payload)
                if close:
                    await ws.close(code=1000)
                    await self.disconnect(job_id,ws)
            except Exception:
                await self.disconnect(job_id,ws)

    def publish(self, job_id: str, payload: dict, close: bool=False):
        loop=self._loop
        if loop and loop.is_running():
            loop.call_soon_threadsafe(lambda: asyncio.create_task(self._broadcast(job_id,payload,close)))

tracking_hub=TrackingHub()

class LocationUpdate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    latitude: float=Field(ge=-90,le=90)
    longitude: float=Field(ge=-180,le=180)

@router.put("/api/v1/workers/me/location")
def update_available_worker_location(body:LocationUpdate,user:User=Depends(authenticated_user),db:Session=Depends(get_db)):
    """Foreground, explicitly permitted location pulse for coarse pre-assignment discovery."""
    require_role(user,"worker")
    now=datetime.now(timezone.utc)
    available=db.query(PresenceSession.id).filter(PresenceSession.user_id==user.id,PresenceSession.expires_at>now,PresenceSession.is_foreground.is_(True),PresenceSession.availability_status=="available").first()
    if not available: raise HTTPException(409,"Set availability and keep the app foregrounded before sharing location")
    if db.bind.dialect.name!="postgresql": raise HTTPException(503,"Location discovery requires PostgreSQL with PostGIS enabled")
    db.execute(text("""INSERT INTO worker_live_locations(user_id,job_id,latitude,longitude,location,updated_at) VALUES(:uid,NULL,:lat,:lng,ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography,:now) ON CONFLICT(user_id) DO UPDATE SET job_id=NULL,latitude=EXCLUDED.latitude,longitude=EXCLUDED.longitude,location=EXCLUDED.location,updated_at=EXCLUDED.updated_at"""),{"uid":user.id,"lat":body.latitude,"lng":body.longitude,"now":now})
    db.commit(); return {"accepted":True,"updated_at":now}

@router.get("/jobs/{job_id}/nearby-workers")
def nearby_workers(job_id:str, radius_km:float=Query(5,gt=0,le=50), user:User=Depends(authenticated_user), db:Session=Depends(get_db)):
    require_role(user,"shop_owner","shopkeeper")
    job=db.query(Job).filter(Job.id==job_id).first()
    if job is None: raise HTTPException(404,"Job not found")
    if not job.shop_id or not db.query(Shop.id).filter(Shop.id==job.shop_id,Shop.owner_id==user.id).first(): raise HTTPException(403,"You do not own this job")
    if job.latitude is None or job.longitude is None: raise HTTPException(409,"Job has no selected map coordinates")
    if db.bind.dialect.name!="postgresql": raise HTTPException(503,"Nearby workers requires PostgreSQL with PostGIS enabled")
    # EXISTS avoids duplicate workers when an account has multiple live sessions,
    # while retaining the GiST-backed geography radius filter.
    rows=db.execute(text("""SELECT u.id, round(w.latitude::numeric,2)::float AS latitude, round(w.longitude::numeric,2)::float AS longitude, round((ST_Distance(w.location, ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography)/1000)::numeric,1)::float AS distance_km, w.updated_at FROM worker_live_locations w JOIN users u ON u.id=w.user_id WHERE u.role='worker' AND u.is_active=true AND EXISTS (SELECT 1 FROM user_presence_sessions p WHERE p.user_id=u.id AND p.expires_at>:now AND p.is_foreground=true AND p.availability_status='available') AND w.updated_at>:fresh AND ST_DWithin(w.location,ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography,:radius) ORDER BY distance_km LIMIT 100"""),{"lat":job.latitude,"lng":job.longitude,"now":datetime.now(timezone.utc),"fresh":datetime.now(timezone.utc)-timedelta(minutes=5),"radius":radius_km*1000}).mappings().all()
    return {"radius_km":radius_km,"workers":[{"id":r["id"],"latitude":r["latitude"],"longitude":r["longitude"],"distance_km":r["distance_km"],"updated_at":r["updated_at"]} for r in rows]}

@router.put("/jobs/{job_id}/tracking/location")
def update_location(job_id:str, body:LocationUpdate, user:User=Depends(authenticated_user), db:Session=Depends(get_db)):
    require_role(user,"worker")
    job=db.query(Job).filter(Job.id==job_id,Job.assigned_worker_id==user.id).with_for_update().first()
    if job is None: raise HTTPException(404,"Active assignment not found")
    if job.status not in ("assigned","in_progress"): raise HTTPException(409,"Location updates are allowed only during an active assignment")
    now=datetime.now(timezone.utc)
    if db.bind.dialect.name!="postgresql": raise HTTPException(503,"Live tracking requires PostgreSQL with PostGIS enabled")
    db.execute(text("""INSERT INTO worker_live_locations(user_id,job_id,latitude,longitude,location,updated_at) VALUES(:uid,:job,:lat,:lng,ST_SetSRID(ST_MakePoint(:lng,:lat),4326)::geography,:now) ON CONFLICT(user_id) DO UPDATE SET job_id=EXCLUDED.job_id,latitude=EXCLUDED.latitude,longitude=EXCLUDED.longitude,location=EXCLUDED.location,updated_at=EXCLUDED.updated_at"""),{"uid":user.id,"job":job.id,"lat":body.latitude,"lng":body.longitude,"now":now})
    db.commit()
    tracking_hub.publish(job.id,{"state":"online","latitude":body.latitude,"longitude":body.longitude,"updated_at":now.isoformat()})
    return {"accepted":True,"updated_at":now}

@router.get("/jobs/{job_id}/tracking/location")
def assigned_location(job_id:str,user:User=Depends(authenticated_user),db:Session=Depends(get_db)):
    job=db.query(Job).filter(Job.id==job_id).first()
    if job is None: raise HTTPException(404,"Job not found")
    if not job.shop_id or not db.query(Shop.id).filter(Shop.id==job.shop_id,Shop.owner_id==user.id).first(): raise HTTPException(403,"Only the assigned shopkeeper can view this location")
    if not job.assigned_worker_id or job.status not in ("assigned","in_progress"): raise HTTPException(410,"Tracking session has ended")
    row=db.query(WorkerLocation).filter_by(user_id=job.assigned_worker_id,job_id=job.id).first()
    if row is None: return {"state":"disconnected","location":None}
    age=(datetime.now(timezone.utc)-row.updated_at.replace(tzinfo=timezone.utc) if row.updated_at.tzinfo is None else datetime.now(timezone.utc)-row.updated_at)
    return {"state":"stale" if age>timedelta(minutes=2) else "online","location":{"latitude":row.latitude,"longitude":row.longitude,"updated_at":row.updated_at}}

async def _socket_user(ws:WebSocket, db:Session):
    value=ws.headers.get("authorization",""); scheme,_,token=value.partition(" "); token=token.strip() if scheme.lower()=="bearer" else ""
    if not token: return None
    if token.startswith("errno_"):
        session=db.query(BackendAuthSession).filter(BackendAuthSession.token_digest==hashlib.sha256(token.encode()).hexdigest(),BackendAuthSession.revoked_at.is_(None),BackendAuthSession.expires_at>datetime.now(timezone.utc)).first()
        return db.query(User).filter_by(id=session.user_id,is_active=True).first() if session else None
    try: claims=verify_firebase_token(token); return db.query(User).filter_by(firebase_uid=claims["uid"],is_active=True).first()
    except HTTPException: return None

@router.websocket("/ws/jobs/{job_id}/tracking")
async def tracking_socket(ws:WebSocket,job_id:str):
    db=SessionLocal(); auth_scheme,_,socket_token=ws.headers.get("authorization","").partition(" ")
    socket_token=socket_token.strip() if auth_scheme.lower()=="bearer" else ""
    user=await _socket_user(ws,db)
    job=db.query(Job).filter_by(id=job_id).first()
    allowed=bool(user and job and job.status in ("assigned","in_progress") and (user.id==job.assigned_worker_id or (job.shop_id and db.query(Shop.id).filter_by(id=job.shop_id,owner_id=user.id).first())))
    if not allowed:
        await ws.close(code=4403); db.close(); return
    await tracking_hub.connect(job_id,ws)
    try:
        row=db.query(WorkerLocation).filter_by(user_id=job.assigned_worker_id,job_id=job.id).first()
        if user.id==job.assigned_worker_id:
            await ws.send_json({"state":"connected","role":"worker"})
        elif row:
            age=datetime.now(timezone.utc)-(row.updated_at.replace(tzinfo=timezone.utc) if row.updated_at.tzinfo is None else row.updated_at)
            await ws.send_json({"state":"stale" if age>timedelta(minutes=2) else "online","latitude":row.latitude,"longitude":row.longitude,"updated_at":row.updated_at.isoformat()})
        else: await ws.send_json({"state":"disconnected"})
        while True:
            db.expire_all()
            job=db.query(Job).filter_by(id=job_id).first()
            if not job or job.status not in ("assigned","in_progress"):
                await ws.send_json({"state":"ended"}); break
            try:
                message=await asyncio.wait_for(ws.receive_text(),timeout=25)
                db.expire_all()
                job=db.query(Job).filter_by(id=job_id).first()
                if not job or job.status not in ("assigned","in_progress"):
                    await ws.send_json({"state":"ended"}); break
                if message.lower() not in ("ping","heartbeat","{}"): continue
                if message.lower() in ("ping","heartbeat"): await ws.send_json({"type":"heartbeat_ack"})
            except asyncio.TimeoutError:
                await ws.send_json({"type":"heartbeat_ping"})
            # Revalidate opaque session revocation and Firebase token validity while the socket is open.
            try:
                if socket_token.startswith("errno_"):
                    valid=db.query(BackendAuthSession.id).filter(BackendAuthSession.token_digest==hashlib.sha256(socket_token.encode()).hexdigest(),BackendAuthSession.revoked_at.is_(None),BackendAuthSession.expires_at>datetime.now(timezone.utc)).first()
                else:
                    claims=verify_firebase_token(socket_token)
                    valid=db.query(User.id).filter_by(firebase_uid=claims["uid"],is_active=True).first()
            except HTTPException:
                valid=None
            if user is None or not user.is_active or not valid:
                await ws.close(code=4401); break
    except WebSocketDisconnect: pass
    except Exception:
        logger.debug("tracking websocket closed",exc_info=True)
    finally:
        await tracking_hub.disconnect(job_id,ws); db.close()

@router.get("/jobs/{job_id}/route")
def assigned_route(job_id:str,user:User=Depends(authenticated_user),db:Session=Depends(get_db)):
    """Return assigned worker route geometry and baseline OSRM duration (not traffic ETA)."""
    job=db.query(Job).filter_by(id=job_id).first()
    if job is None: raise HTTPException(404,"Job not found")
    if not job.shop_id or not db.query(Shop.id).filter_by(id=job.shop_id,owner_id=user.id).first(): raise HTTPException(403,"Only the job owner can view this route")
    if job.status not in ("assigned","in_progress") or not job.assigned_worker_id: raise HTTPException(409,"Route is available only for an assigned active job")
    worker=db.query(WorkerLocation).filter_by(user_id=job.assigned_worker_id,job_id=job.id).first()
    if worker is None or job.latitude is None or job.longitude is None: raise HTTPException(409,"Worker or job location is unavailable")
    import os, requests
    endpoint=os.getenv("ERRNO_OSRM_ENDPOINT","https://router.project-osrm.org/route/v1/driving").rstrip("/")
    try:
        response=requests.get(f"{endpoint}/{worker.longitude},{worker.latitude};{job.longitude},{job.latitude}",params={"overview":"full","geometries":"geojson"},timeout=8)
        if response.status_code==429: raise HTTPException(503,"Routing service rate limited; try later")
        response.raise_for_status(); data=response.json(); routes=data.get("routes",[])
        if not routes: raise HTTPException(503,"No drivable route is available")
        route=routes[0]
        return {"geometry":route["geometry"],"distance_km":round(route["distance"]/1000,1),"duration_minutes":round(route["duration"]/60),"label":"Approximate route duration; no live traffic"}
    except HTTPException: raise
    except Exception: raise HTTPException(503,"Routing service unavailable") from None
