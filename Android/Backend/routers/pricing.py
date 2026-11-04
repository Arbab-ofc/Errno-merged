"""Backend-owned, database-configured pricing quotes and administration."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING, ROUND_FLOOR
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import uuid
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from firebase_auth import authenticated_user, require_admin, require_role
from models import (DurationPricing, PricingSettings, PricingSettingsDraft, TimePricingRule, DemandPricingRule, AreaPricingRule,
                    PricingQuote, PricingAudit, Job, Shop, PresenceSession, User, WorkerLocation)

router = APIRouter(prefix="/api/v1", tags=["Pricing and presence"])
D = Decimal


def _settings(db):
    row = db.query(PricingSettings).with_for_update().first()
    if row is None or row.commission_rate is None or row.quote_ttl_seconds is None or not row.default_timezone or not row.rounding_policy:
        raise HTTPException(503, "Pricing configuration is incomplete; ask an administrator to configure pricing settings")
    if not D("0") <= D(row.commission_rate) <= D("1"):
        raise HTTPException(503, "Configured commission rate is invalid")
    if row.quote_ttl_seconds <= 0:
        raise HTTPException(503, "Configured quote validity is invalid")
    return row


def _within_effective_dates(row, when):
    start = row.effective_from.replace(tzinfo=timezone.utc) if row.effective_from and row.effective_from.tzinfo is None else row.effective_from
    end = row.effective_until.replace(tzinfo=timezone.utc) if row.effective_until and row.effective_until.tzinfo is None else row.effective_until
    return (start is None or start <= when) and (end is None or end > when)


def _active(row, when):
    return row.enabled and _within_effective_dates(row, when)


def _time_rule(db, when, tz_name, rule_id=None, include_drafts=False):
    if rule_id is not None:
        selected = db.query(TimePricingRule).filter(TimePricingRule.id == rule_id).first()
        if selected is None: raise HTTPException(503, "Configured area time rule is missing")
        tz_name = selected.timezone
    try:
        local = when.astimezone(ZoneInfo(tz_name))
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(503, "Configured pricing timezone is invalid") from None
    matches = []
    query = db.query(TimePricingRule)
    if not include_drafts:
        query = query.filter(TimePricingRule.enabled.is_(True))
    if rule_id is not None: query = query.filter(TimePricingRule.id == rule_id)
    for rule in query.all():
        if (not _within_effective_dates(rule, when)
                or (not include_drafts and not rule.enabled)):
            continue
        t = local.timetz().replace(tzinfo=None)
        start, end = rule.start_time, rule.end_time
        inside = start <= t < end if start < end else (t >= start or t < end)
        if inside:
            matches.append(rule)
    if rule_id is not None and len(matches) != 1:
        raise HTTPException(503, "Configured area time rule is inactive or does not cover this service time")
    if len(matches) > 1:
        raise HTTPException(503, "Active time pricing rules overlap for the selected service time")
    if matches:
        rule = matches[0]
        return (rule.name, D(rule.multiplier), {"id": rule.id, "version": rule.version, "name": rule.name})
    return (None, D("1"), None)


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_hours: int = Field(ge=1, le=12)
    service_start_at: datetime
    area_id: str | None = Field(default=None, max_length=160)


class AdminPreviewRequest(QuoteRequest):
    use_draft_configuration: bool = False
    scenario_time_multiplier: Decimal | None = Field(default=None, gt=0, le=10)
    scenario_demand_multiplier: Decimal | None = Field(default=None, gt=0, le=10)


def _build_quote(db, user_id, duration_hours, service_start_at, area_id, persist=True,
                 include_drafts=False, scenario_time_multiplier=None,
                 scenario_demand_multiplier=None):
    now = datetime.now(timezone.utc)
    if service_start_at.tzinfo is None:
        raise HTTPException(422, "service_start_at must include a timezone")
    if include_drafts:
        active_settings = db.query(PricingSettings).first()
        settings_draft = db.query(PricingSettingsDraft).filter_by(id="singleton").first()
        if active_settings is None or settings_draft is None:
            raise HTTPException(409, "There is no global pricing settings draft to preview")
        active_values = {key: getattr(active_settings, key) for key in (
            "surge_enabled", "time_pricing_enabled", "demand_pricing_enabled", "combined_multiplier_cap",
            "commission_rate", "quote_ttl_seconds", "rounding_policy", "default_timezone",
            "heartbeat_interval_seconds", "presence_ttl_seconds")}
        values = {**active_values, **(settings_draft.values or {})}
        if any(values.get(key) is None for key in ("commission_rate", "quote_ttl_seconds", "rounding_policy", "default_timezone")):
            raise HTTPException(503, "Pricing draft is incomplete; configure commission, quote validity, rounding and timezone")
        settings = SimpleNamespace(id=active_settings.id, version=settings_draft.version, **values)
        if not D("0") <= D(str(settings.commission_rate)) <= D("1"):
            raise HTTPException(503, "Draft commission rate is invalid")
        try: ZoneInfo(settings.default_timezone)
        except (ZoneInfoNotFoundError, ValueError): raise HTTPException(503, "Draft pricing timezone is invalid") from None
    else:
        settings = _settings(db)
    duration = db.query(DurationPricing).filter(DurationPricing.duration_hours == duration_hours).first()
    duration_valid = duration is not None and (
        (_within_effective_dates(duration, service_start_at) and duration.enabled and duration.approval_status == "approved")
        if not include_drafts else _within_effective_dates(duration, service_start_at))
    if not duration_valid:
        raise HTTPException(503, f"No approved active price is configured for {duration_hours} hours")
    if duration.base_price is None or duration.maximum_price is None:
        raise HTTPException(503, "Active duration pricing is incomplete")
    base, maximum = map(D, (duration.base_price, duration.maximum_price))
    normalized_area = " ".join((area_id or "").split()).casefold() or None
    area_rule = None
    if normalized_area:
        candidates = [r for r in db.query(AreaPricingRule).filter(AreaPricingRule.duration_hours == duration_hours).all()
                     if " ".join(r.area_key.split()).casefold() == normalized_area
                     and (_active(r, service_start_at) and r.approval_status == "approved" if not include_drafts
                          else _within_effective_dates(r, service_start_at))]
        if len(candidates) > 1:
            raise HTTPException(503, "Multiple active area pricing overrides match this address and duration")
        if candidates:
            area_rule = candidates[0]
            if area_rule.base_price is not None: base = D(area_rule.base_price)
            if area_rule.maximum_price is not None: maximum = D(area_rule.maximum_price)
    if not (D(0) <= base <= maximum):
        raise HTTPException(503, "Active duration pricing violates base <= maximum")
    selected_time_rule = area_rule.time_rule_id if area_rule else None
    time_name, time_multiplier, time_snapshot = (None, D("1"), None)
    if scenario_time_multiplier is not None:
        time_name, time_multiplier = "Admin preview scenario", D(scenario_time_multiplier)
        time_snapshot = {"scenario": True, "multiplier": str(time_multiplier)}
    elif settings.time_pricing_enabled and settings.surge_enabled:
        time_name, time_multiplier, time_snapshot = _time_rule(
            db, service_start_at, settings.default_timezone, selected_time_rule, include_drafts)
    demand_multiplier, demand_level = D("1"), None
    demand_snapshot = None
    if scenario_demand_multiplier is not None:
        demand_level, demand_multiplier = "admin_preview_scenario", D(scenario_demand_multiplier)
        demand_snapshot = {"scenario": True, "multiplier": str(demand_multiplier)}
    elif settings.demand_pricing_enabled and settings.surge_enabled:
        available = db.query(PresenceSession.user_id).join(User, User.id == PresenceSession.user_id).filter(
            User.role == "worker", User.is_active.is_(True), PresenceSession.expires_at > now,
            PresenceSession.availability_status == "available").distinct().count()
        open_jobs = db.query(Job.id).filter(Job.status == "open").count()
        if available == 0:
            ratio = None
        else:
            ratio = D(open_jobs) / D(available)
        rules = [r for r in db.query(DemandPricingRule).all()
                 if _within_effective_dates(r, service_start_at) and (include_drafts or r.enabled)]
        selected_demand_rule = area_rule.demand_rule_id if area_rule else None
        if selected_demand_rule:
            rules = [r for r in rules if r.id == selected_demand_rule]
        if not rules:
            raise HTTPException(503, "Demand pricing is enabled but no active demand rule is configured")
        if available == 0:
            # A zero supply condition is explicit and matches a rule that declares a zero threshold.
            candidates = [r for r in rules if (r.availability_thresholds or {}).get("zero_available_workers") is True]
        else:
            candidates = [r for r in rules if (r.minimum_demand_ratio is None or ratio >= D(r.minimum_demand_ratio)) and (r.maximum_demand_ratio is None or ratio < D(r.maximum_demand_ratio))]
        if len(candidates) != 1:
            raise HTTPException(503, "Demand inputs do not map to exactly one configured active demand rule")
        demand_rule = candidates[0]
        demand_level, demand_multiplier = demand_rule.demand_level, D(demand_rule.multiplier)
        demand_snapshot = {"id": demand_rule.id, "version": demand_rule.version,
                           "name": demand_rule.name, "demand_level": demand_rule.demand_level}
    combined = time_multiplier * demand_multiplier
    if combined < 0:
        raise HTTPException(503, "Configured multiplier cannot be negative")
    if settings.surge_enabled and settings.combined_multiplier_cap is not None:
        combined = min(combined, D(settings.combined_multiplier_cap))
    raw = base * combined
    bounded = min(maximum, max(base, raw))
    policy = settings.rounding_policy
    rounding = {"half_up": ROUND_HALF_UP, "up": ROUND_CEILING, "down": ROUND_FLOOR}.get(policy)
    if rounding is None:
        raise HTTPException(503, "Configured rounding policy is unsupported")
    final = bounded.quantize(D("1"), rounding=rounding)
    lower = base.quantize(D("1"), rounding=ROUND_CEILING)
    upper = maximum.quantize(D("1"), rounding=ROUND_FLOOR)
    if lower > upper:
        raise HTTPException(503, "Configured base and maximum do not contain a whole-rupee price")
    final = min(upper, max(lower, final))
    commission = (final * D(settings.commission_rate)).quantize(D("0.01"), rounding=ROUND_HALF_UP)
    payout = final - commission
    if commission + payout != final or payout < 0:
        raise HTTPException(503, "Configured financial rules produce an invalid payout split")
    rule_snapshot = {
        "global_settings": {"id": settings.id, "version": settings.version},
        "duration": {"duration_hours": duration.duration_hours, "version": duration.version},
        "area": {"id": area_rule.id, "version": area_rule.version} if area_rule else None,
        "time_rule": time_snapshot,
        "demand_rule": demand_snapshot,
    }
    pricing_version = max([settings.version, duration.version]
                          + ([area_rule.version] if area_rule else [])
                          + ([time_snapshot["version"]] if time_snapshot and "version" in time_snapshot else [])
                          + ([demand_snapshot["version"]] if demand_snapshot and "version" in demand_snapshot else []))
    quote = PricingQuote(id=str(uuid.uuid4()), user_id=user_id, duration_hours=duration_hours,
        service_start_at=service_start_at, area_id=normalized_area, base_price=base, maximum_price=maximum,
        time_band=time_name, time_multiplier=time_multiplier, demand_level=demand_level, demand_multiplier=demand_multiplier,
        raw_price=raw, final_service_charge=final, commission_rate=settings.commission_rate, commission_amount=commission,
        worker_payout_amount=payout, pricing_rule_version=pricing_version,
        pricing_rule_snapshot=rule_snapshot, created_at=now,
        expires_at=now + timedelta(seconds=settings.quote_ttl_seconds), status="active")
    if persist:
        db.add(quote)
    return quote


def _quote_json(q):
    return {"quote_id": q.id, "duration_hours": q.duration_hours, "service_start_at": q.service_start_at,
        "area_id": q.area_id, "base_price": q.base_price, "maximum_price": q.maximum_price,
        "time_band": q.time_band, "time_multiplier": q.time_multiplier, "demand_level": q.demand_level,
        "demand_multiplier": q.demand_multiplier, "raw_price": q.raw_price, "final_service_charge": q.final_service_charge,
        "commission_rate": q.commission_rate, "commission_amount": q.commission_amount, "worker_payout_amount": q.worker_payout_amount,
        "pricing_version": q.pricing_rule_version, "pricing_rule_snapshot": q.pricing_rule_snapshot,
        "created_at": q.created_at, "expires_at": q.expires_at, "status": q.status}


@router.get("/pricing/durations")
def durations(db: Session = Depends(get_db), user: User = Depends(authenticated_user)):
    now = datetime.now(timezone.utc)
    return [{"duration_hours": r.duration_hours, "base_price": r.base_price,
             "maximum_price": r.maximum_price, "currency": r.currency, "enabled": r.enabled,
             "approval_status": r.approval_status, "effective_from": r.effective_from, "effective_until": r.effective_until,
             "version": r.version} for r in db.query(DurationPricing).order_by(DurationPricing.duration_hours).all()]


@router.post("/pricing/quotes")
def create_quote(body: QuoteRequest, db: Session = Depends(get_db), user: User = Depends(authenticated_user)):
    require_role(user, "shop_owner", "shopkeeper")
    quote = _build_quote(db, user.id, body.duration_hours, body.service_start_at, body.area_id)
    db.commit()
    return _quote_json(quote)


@router.post("/admin/pricing/preview")
def admin_pricing_preview(body: AdminPreviewRequest, _: object = Depends(require_admin("pricing.read")), db: Session = Depends(get_db)):
    # Uses the production calculation function, but can preview saved drafts
    # and administrator-selected multiplier scenarios without persisting a quote.
    quote = _build_quote(db, None, body.duration_hours, body.service_start_at, body.area_id,
        persist=False, include_drafts=body.use_draft_configuration,
        scenario_time_multiplier=body.scenario_time_multiplier,
        scenario_demand_multiplier=body.scenario_demand_multiplier)
    return {**_quote_json(quote), "preview_only": True,
            "configuration_source": "draft" if body.use_draft_configuration else "active"}


@router.get("/pricing/quotes/{quote_id}")
def get_quote(quote_id: str, db: Session = Depends(get_db), user: User = Depends(authenticated_user)):
    q = db.query(PricingQuote).filter(PricingQuote.id == quote_id, PricingQuote.user_id == user.id).first()
    if q is None:
        raise HTTPException(404, "Pricing quote not found")
    return _quote_json(q)


@router.get("/jobs/{job_id}/pricing")
def job_pricing(job_id: str, db: Session = Depends(get_db), user: User = Depends(authenticated_user)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None: raise HTTPException(404, "Job not found")
    q = db.query(PricingQuote).filter(PricingQuote.job_id == job.id).first()
    if q is None: raise HTTPException(404, "This legacy job has no pricing snapshot")
    return _quote_json(q)


@router.get("/jobs/{job_id}/worker-payout")
def job_worker_payout(job_id: str, db: Session = Depends(get_db), user: User = Depends(authenticated_user)):
    require_role(user, "worker", "shop_owner", "shopkeeper")
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None: raise HTTPException(404, "Job not found")
    q = db.query(PricingQuote).filter(PricingQuote.job_id == job.id).first()
    if q is None: raise HTTPException(404, "This legacy job has no pricing snapshot")
    return {"job_id": job.id, "duration_hours": q.duration_hours,
            "worker_payout_amount": q.worker_payout_amount, "currency": "INR", "pricing_version": q.pricing_rule_version}


class DurationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_price: Decimal | None = Field(default=None, ge=0)
    maximum_price: Decimal | None = Field(default=None, ge=0)
    enabled: bool = False
    effective_from: datetime | None = None
    effective_until: datetime | None = None


@router.get("/admin/pricing/durations")
def admin_durations(_: object = Depends(require_admin("pricing.read")), db: Session = Depends(get_db)):
    return durations_admin_list(db)


def durations_admin_list(db):
    return [{"duration_hours": r.duration_hours, "base_price": r.base_price, "maximum_price": r.maximum_price,
             "enabled": r.enabled, "approval_status": r.approval_status, "effective_from": r.effective_from, "effective_until": r.effective_until,
             "version": r.version, "updated_at": r.updated_at} for r in db.query(DurationPricing).order_by(DurationPricing.duration_hours).all()]


@router.put("/admin/pricing/durations/{duration_hours}")
def update_duration(duration_hours: int, body: DurationPatch, admin=Depends(require_admin("pricing.write")), db: Session = Depends(get_db)):
    if not 1 <= duration_hours <= 12: raise HTTPException(422, "Duration must be between 1 and 12 hours")
    row = db.query(DurationPricing).filter(DurationPricing.duration_hours == duration_hours).with_for_update().first()
    if row is None: raise HTTPException(404, "Duration configuration not found")
    old = {k: str(getattr(row, k)) if getattr(row, k) is not None else None for k in ("base_price", "maximum_price", "enabled", "approval_status", "version")}
    data = body.model_dump()
    for key, value in data.items(): setattr(row, key, value)
    row.approval_status = "draft"
    row.enabled = False
    row.updated_by = admin.firebase_uid
    row.version += 1
    if row.base_price is not None and row.maximum_price is not None and row.base_price > row.maximum_price:
        db.rollback(); raise HTTPException(422, "Pricing must satisfy base <= maximum")
    audit_value = body.model_dump(mode="json")
    db.add(PricingAudit(admin_user_id=admin.firebase_uid, entity_type="duration", entity_id=str(duration_hours), action="draft_updated", previous_value=old, new_value={**audit_value, "approval_status":"draft"}, pricing_version=row.version))
    db.commit(); return durations_admin_list(db)


class ActivateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_hours: int = Field(ge=1, le=12)


@router.post("/admin/pricing/activate")
def activate_duration(body: ActivateBody, admin=Depends(require_admin("pricing.activate")), db: Session = Depends(get_db)):
    row = db.query(DurationPricing).filter(DurationPricing.duration_hours == body.duration_hours).with_for_update().first()
    now = datetime.now(timezone.utc)
    if row is None or row.base_price is None or row.maximum_price is None or not row.effective_from:
        raise HTTPException(422, "Complete pricing and an effective start date are required before activation")
    if row.base_price > row.maximum_price: raise HTTPException(422, "Pricing must satisfy base <= maximum")
    if row.effective_until and row.effective_until <= row.effective_from: raise HTTPException(422, "Effective end must follow effective start")
    row.approval_status, row.enabled = "approved", True
    row.updated_by, row.updated_at = admin.firebase_uid, now
    db.add(PricingAudit(admin_user_id=admin.firebase_uid, entity_type="duration", entity_id=str(row.duration_hours), action="activated", new_value={"version":row.version}, pricing_version=row.version))
    db.commit()
    return {"duration_hours": row.duration_hours, "approval_status": row.approval_status, "enabled": row.enabled, "version": row.version}


class AreaPricingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    area_key: str = Field(min_length=1, max_length=500)
    duration_hours: int = Field(ge=1, le=12)
    base_price: Decimal | None = Field(default=None, ge=0)
    maximum_price: Decimal | None = Field(default=None, ge=0)
    time_rule_id: str | None = None
    demand_rule_id: str | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None


class AreaPricingPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    area_key: str | None = Field(default=None, min_length=1, max_length=500)
    base_price: Decimal | None = Field(default=None, ge=0)
    maximum_price: Decimal | None = Field(default=None, ge=0)
    time_rule_id: str | None = None
    demand_rule_id: str | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None


def _area_json(r):
    return {c.name: getattr(r, c.name) for c in r.__table__.columns}


@router.get("/admin/pricing/areas")
def list_area_pricing(_: object = Depends(require_admin("pricing.read")), db: Session = Depends(get_db)):
    return [_area_json(r) for r in db.query(AreaPricingRule).order_by(AreaPricingRule.area_key, AreaPricingRule.duration_hours).all()]


@router.post("/admin/pricing/areas")
def create_area_pricing(body: AreaPricingCreate, admin=Depends(require_admin("pricing.write")), db: Session = Depends(get_db)):
    row = AreaPricingRule(id=str(uuid.uuid4()), area_key=" ".join(body.area_key.split()).casefold(),
        duration_hours=body.duration_hours, base_price=body.base_price, maximum_price=body.maximum_price,
        time_rule_id=body.time_rule_id, demand_rule_id=body.demand_rule_id,
        effective_from=body.effective_from, effective_until=body.effective_until)
    if row.base_price is not None and row.maximum_price is not None and row.base_price > row.maximum_price:
        raise HTTPException(422, "Area pricing must satisfy base <= maximum")
    db.add(row)
    db.add(PricingAudit(admin_user_id=admin.firebase_uid, entity_type="area_pricing", entity_id=row.id,
        action="draft_created", new_value=body.model_dump(mode="json"), pricing_version=row.version))
    db.commit(); return _area_json(row)


@router.patch("/admin/pricing/areas/{rule_id}")
def patch_area_pricing(rule_id: str, body: AreaPricingPatch, admin=Depends(require_admin("pricing.write")), db: Session = Depends(get_db)):
    row=db.query(AreaPricingRule).filter(AreaPricingRule.id==rule_id).with_for_update().first()
    if row is None: raise HTTPException(404,"Area pricing rule not found")
    previous=_area_json(row)
    values=body.model_dump(exclude_unset=True)
    for key,value in values.items():
        setattr(row,key," ".join(value.split()).casefold() if key=="area_key" and value else value)
    row.enabled=False; row.approval_status="draft"; row.version+=1; row.updated_by=admin.firebase_uid
    global_row=db.query(DurationPricing).filter(DurationPricing.duration_hours==row.duration_hours).first()
    base=D(row.base_price) if row.base_price is not None else D(global_row.base_price) if global_row and global_row.base_price is not None else None
    maximum=D(row.maximum_price) if row.maximum_price is not None else D(global_row.maximum_price) if global_row and global_row.maximum_price is not None else None
    if base is None or maximum is None or base>maximum: db.rollback(); raise HTTPException(422,"Area pricing must resolve to valid base <= maximum")
    db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="area_pricing",entity_id=row.id,action="draft_updated",previous_value=jsonable_encoder(previous),new_value=body.model_dump(mode="json"),pricing_version=row.version))
    db.commit(); return _area_json(row)


@router.post("/admin/pricing/areas/{rule_id}/activate")
def activate_area_pricing(rule_id:str,admin=Depends(require_admin("pricing.activate")),db:Session=Depends(get_db)):
    row=db.query(AreaPricingRule).filter(AreaPricingRule.id==rule_id).with_for_update().first()
    if row is None: raise HTTPException(404,"Area pricing rule not found")
    if row.effective_from is None: raise HTTPException(422,"An effective start date is required")
    global_row=db.query(DurationPricing).filter(DurationPricing.duration_hours==row.duration_hours).first()
    base=D(row.base_price) if row.base_price is not None else D(global_row.base_price) if global_row and global_row.base_price is not None else None
    maximum=D(row.maximum_price) if row.maximum_price is not None else D(global_row.maximum_price) if global_row and global_row.maximum_price is not None else None
    if base is None or maximum is None or base>maximum: raise HTTPException(422,"Area pricing must resolve to valid base <= maximum")
    if row.effective_until and row.effective_until<=row.effective_from: raise HTTPException(422,"Effective end must follow effective start")
    for other in db.query(AreaPricingRule).filter(AreaPricingRule.enabled.is_(True),AreaPricingRule.duration_hours==row.duration_hours,AreaPricingRule.id!=row.id).all():
        if " ".join(other.area_key.split()).casefold()!=row.area_key: continue
        begin=max(x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x for x in (row.effective_from,other.effective_from) if x is not None)
        ends=[x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x for x in (row.effective_until,other.effective_until) if x is not None]
        if not ends or begin<min(ends): raise HTTPException(409,"Area pricing rule overlaps another active rule for this address and duration")
    row.enabled=True; row.approval_status="approved"; row.version+=1; row.updated_by=admin.firebase_uid
    db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="area_pricing",entity_id=row.id,action="activated",new_value={"area_key":row.area_key,"duration_hours":row.duration_hours},pricing_version=row.version))
    db.commit(); return {"id":row.id,"enabled":row.enabled,"approval_status":row.approval_status,"version":row.version}


class SettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surge_enabled: bool | None = None
    time_pricing_enabled: bool | None = None
    demand_pricing_enabled: bool | None = None
    combined_multiplier_cap: Decimal | None = Field(default=None, gt=0)
    commission_rate: Decimal | None = Field(default=None, ge=0, le=1)
    quote_ttl_seconds: int | None = Field(default=None, gt=0, le=86400)
    rounding_policy: str | None = Field(default=None, pattern="^(half_up|up|down)$")
    default_timezone: str | None = Field(default=None, min_length=1, max_length=80)
    heartbeat_interval_seconds: int | None = Field(default=None, ge=15, le=3600)
    presence_ttl_seconds: int | None = Field(default=None, ge=30, le=86400)


@router.get("/admin/pricing/settings")
def get_settings(_: object = Depends(require_admin("pricing.read")), db: Session = Depends(get_db)):
    s = db.query(PricingSettings).first()
    if s is None: return {}
    result = {c.name: getattr(s, c.name) for c in s.__table__.columns}
    draft = db.query(PricingSettingsDraft).filter(PricingSettingsDraft.id=="singleton").first()
    result["draft"] = {"values": draft.values, "version": draft.version, "updated_by": draft.updated_by, "updated_at": draft.updated_at} if draft else None
    return result


@router.patch("/admin/pricing/settings")
def patch_settings(body: SettingsPatch, admin=Depends(require_admin("pricing.write")), db: Session = Depends(get_db)):
    s = db.query(PricingSettings).with_for_update().first()
    if s is None: raise HTTPException(503, "Pricing settings row is missing")
    draft = db.query(PricingSettingsDraft).filter(PricingSettingsDraft.id=="singleton").with_for_update().first()
    active_keys = ("surge_enabled","time_pricing_enabled","demand_pricing_enabled","combined_multiplier_cap","commission_rate","quote_ttl_seconds","rounding_policy","default_timezone","heartbeat_interval_seconds","presence_ttl_seconds")
    current = draft.values if draft else {key: str(getattr(s,key)) if isinstance(getattr(s,key),Decimal) else getattr(s,key) for key in active_keys}
    updated = {**current, **body.model_dump(mode="json", exclude_unset=True)}
    if updated.get("default_timezone"):
        try: ZoneInfo(updated["default_timezone"])
        except (ZoneInfoNotFoundError, ValueError): raise HTTPException(422,"Unknown timezone") from None
    if draft is None:
        draft=PricingSettingsDraft(id="singleton",values=updated,version=s.version+1,updated_by=admin.firebase_uid); db.add(draft)
    else:
        draft.values=updated; draft.version=s.version+1; draft.updated_by=admin.firebase_uid; draft.updated_at=datetime.now(timezone.utc)
    db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="settings",action="draft_updated",previous_value=current,new_value=updated,pricing_version=draft.version))
    db.commit(); return get_settings(None,db)


@router.post("/admin/pricing/settings/activate")
def activate_settings(admin=Depends(require_admin("pricing.activate")),db:Session=Depends(get_db)):
    s=db.query(PricingSettings).with_for_update().first()
    draft=db.query(PricingSettingsDraft).filter(PricingSettingsDraft.id=="singleton").with_for_update().first()
    if s is None or draft is None: raise HTTPException(409,"There is no global pricing settings draft to activate")
    values=draft.values
    required=("commission_rate","quote_ttl_seconds","rounding_policy","default_timezone")
    if any(values.get(key) is None for key in required): raise HTTPException(422,"Commission, quote validity, rounding policy, and timezone are required")
    if values.get("surge_enabled") and values.get("combined_multiplier_cap") is None: raise HTTPException(422,"A combined multiplier cap is required when surge pricing is enabled")
    if not D(0)<=D(str(values["commission_rate"]))<=D(1): raise HTTPException(422,"Commission rate must be between 0 and 1")
    if int(values["quote_ttl_seconds"])<=0: raise HTTPException(422,"Quote validity must be positive")
    try: ZoneInfo(values["default_timezone"])
    except (ZoneInfoNotFoundError,ValueError): raise HTTPException(422,"Unknown pricing timezone") from None
    duration_rows=db.query(DurationPricing).order_by(DurationPricing.duration_hours).all()
    by_duration={row.duration_hours:row for row in duration_rows}
    incomplete=[]
    for hours in range(1,13):
        row=by_duration.get(hours)
        if (row is None or row.base_price is None or row.maximum_price is None
                or row.base_price < 0 or row.base_price > row.maximum_price
                or not row.enabled or row.approval_status != "approved"
                or row.effective_from is None
                or (row.effective_until is not None and row.effective_until <= row.effective_from)):
            incomplete.append(hours)
    if incomplete:
        raise HTTPException(422,"Pricing activation requires complete, valid, approved duration prices for all 1–12 hours; unresolved durations: " + ", ".join(map(str,incomplete)))
    if values.get("time_pricing_enabled") and not db.query(TimePricingRule.id).filter(TimePricingRule.enabled.is_(True)).first(): raise HTTPException(422,"Enable time pricing only after activating at least one time rule")
    if values.get("demand_pricing_enabled") and not db.query(DemandPricingRule.id).filter(DemandPricingRule.enabled.is_(True)).first(): raise HTTPException(422,"Enable demand pricing only after activating at least one demand rule")
    active_keys=("surge_enabled","time_pricing_enabled","demand_pricing_enabled","combined_multiplier_cap","commission_rate","quote_ttl_seconds","rounding_policy","default_timezone","heartbeat_interval_seconds","presence_ttl_seconds")
    previous={key:str(getattr(s,key)) if isinstance(getattr(s,key),Decimal) else getattr(s,key) for key in values}
    for key,value in values.items():
        if key in active_keys: setattr(s,key,value)
    s.version=draft.version; s.updated_by=admin.firebase_uid; s.updated_at=datetime.now(timezone.utc)
    db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="settings",action="activated",previous_value=previous,new_value=values,pricing_version=s.version))
    db.delete(draft); db.commit(); return get_settings(None,db)


@router.get("/admin/pricing/time-rules")
def list_time_rules(_: object = Depends(require_admin("pricing.read")), db: Session = Depends(get_db)):
    return [{c.name:getattr(r,c.name) for c in r.__table__.columns} for r in db.query(TimePricingRule).all()]


class TimeRuleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1,max_length=120); start_time: str; end_time: str; timezone: str
    multiplier: Decimal = Field(gt=0,le=10); enabled: bool = False; effective_from: datetime | None = None; effective_until: datetime | None = None


@router.post("/admin/pricing/time-rules")
def create_time_rule(body: TimeRuleBody, admin=Depends(require_admin("pricing.write")), db: Session=Depends(get_db)):
    from datetime import time
    try: ZoneInfo(body.timezone); start=time.fromisoformat(body.start_time); end=time.fromisoformat(body.end_time)
    except Exception: raise HTTPException(422,"Invalid time or timezone") from None
    if body.enabled: raise HTTPException(422,"Create rule as draft, then activate with a reviewed configuration")
    row=TimePricingRule(id=str(uuid.uuid4()),name=body.name,start_time=start,end_time=end,timezone=body.timezone,multiplier=body.multiplier,enabled=False,effective_from=body.effective_from,effective_until=body.effective_until)
    db.add(row); db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="time_rule",entity_id=row.id,action="created",new_value=body.model_dump(mode="json"),pricing_version=row.version)); db.commit()
    return {c.name:getattr(row,c.name) for c in row.__table__.columns}


@router.patch("/admin/pricing/time-rules/{rule_id}")
def patch_time_rule(rule_id: str, body: dict, admin=Depends(require_admin("pricing.write")), db: Session=Depends(get_db)):
    allowed={"name","start_time","end_time","timezone","multiplier","enabled","effective_from","effective_until"}
    if not body or set(body)-allowed: raise HTTPException(422,"Invalid time-rule fields")
    row=db.query(TimePricingRule).filter(TimePricingRule.id==rule_id).with_for_update().first()
    if row is None: raise HTTPException(404,"Time pricing rule not found")
    if body.get("enabled") is True: raise HTTPException(422,"Rule activation requires the reviewed pricing activation workflow")
    previous={k:str(getattr(row,k)) if getattr(row,k) is not None else None for k in body}
    from datetime import time
    for key,value in body.items():
        if key in ("start_time","end_time"):
            try: value=time.fromisoformat(value)
            except Exception: raise HTTPException(422,"Invalid time value") from None
        if key=="timezone":
            try: ZoneInfo(value)
            except Exception: raise HTTPException(422,"Invalid timezone") from None
        setattr(row,key,value)
    row.enabled=False; row.version+=1
    db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="time_rule",entity_id=row.id,action="draft_updated",previous_value=previous,new_value=body,pricing_version=row.version))
    db.commit(); return {c.name:getattr(row,c.name) for c in row.__table__.columns}


@router.post("/admin/pricing/time-rules/{rule_id}/activate")
def activate_time_rule(rule_id:str,admin=Depends(require_admin("pricing.activate")),db:Session=Depends(get_db)):
    row=db.query(TimePricingRule).filter(TimePricingRule.id==rule_id).with_for_update().first()
    if row is None: raise HTTPException(404,"Time pricing rule not found")
    if row.effective_from is None: raise HTTPException(422,"An effective start date is required")
    def covers(rule, minute):
        begin=rule.start_time.hour*60+rule.start_time.minute; end=rule.end_time.hour*60+rule.end_time.minute
        return begin<=minute<end if begin<end else minute>=begin or minute<end
    for other in db.query(TimePricingRule).filter(TimePricingRule.enabled.is_(True),TimePricingRule.id!=row.id).all():
        if other.timezone != row.timezone:
            raise HTTPException(409,"Cannot prove time-band exclusivity across different active timezones")
        starts=max(x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x for x in (row.effective_from,other.effective_from) if x is not None)
        ends=[x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x for x in (row.effective_until,other.effective_until) if x is not None]
        if ends and starts>=min(ends): continue
        if any(covers(row,m) and covers(other,m) for m in range(1440)):
            raise HTTPException(409,"Time rule overlaps another active rule")
    row.enabled=True; row.version+=1
    db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="time_rule",entity_id=row.id,action="activated",pricing_version=row.version,new_value={"enabled":True}))
    db.commit(); return {"id":row.id,"enabled":row.enabled,"version":row.version}


@router.get("/admin/pricing/demand-rules")
def list_demand_rules(_: object = Depends(require_admin("pricing.read")), db: Session = Depends(get_db)):
    return [{c.name:getattr(r,c.name) for c in r.__table__.columns} for r in db.query(DemandPricingRule).all()]


class DemandRuleBody(BaseModel):
    model_config=ConfigDict(extra="forbid")
    name:str=Field(min_length=1,max_length=120); demand_level:str=Field(min_length=1,max_length=40)
    minimum_demand_ratio:Decimal|None=None; maximum_demand_ratio:Decimal|None=None
    availability_thresholds:dict=Field(default_factory=dict); multiplier:Decimal=Field(gt=0,le=10)
    enabled:bool=False; effective_from:datetime|None=None; effective_until:datetime|None=None


@router.post("/admin/pricing/demand-rules")
def create_demand_rule(body:DemandRuleBody,admin=Depends(require_admin("pricing.write")),db:Session=Depends(get_db)):
    if body.minimum_demand_ratio is not None and body.maximum_demand_ratio is not None and body.minimum_demand_ratio>=body.maximum_demand_ratio:
        raise HTTPException(422,"Demand ratio minimum must be lower than maximum")
    if body.enabled: raise HTTPException(422,"Create rule as draft, then activate after review")
    row=DemandPricingRule(id=str(uuid.uuid4()),**body.model_dump(exclude={"enabled"}))
    db.add(row); db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="demand_rule",entity_id=row.id,action="created",new_value=body.model_dump(mode="json"),pricing_version=row.version)); db.commit()
    return {c.name:getattr(row,c.name) for c in row.__table__.columns}


@router.patch("/admin/pricing/demand-rules/{rule_id}")
def patch_demand_rule(rule_id:str,body:dict,admin=Depends(require_admin("pricing.write")),db:Session=Depends(get_db)):
    allowed={"name","demand_level","minimum_demand_ratio","maximum_demand_ratio","availability_thresholds","multiplier","enabled","effective_from","effective_until"}
    if not body or set(body)-allowed: raise HTTPException(422,"Invalid demand-rule fields")
    row=db.query(DemandPricingRule).filter(DemandPricingRule.id==rule_id).with_for_update().first()
    if row is None: raise HTTPException(404,"Demand pricing rule not found")
    if body.get("enabled") is True: raise HTTPException(422,"Rule activation requires the reviewed pricing activation workflow")
    previous={k:str(getattr(row,k)) if getattr(row,k) is not None else None for k in body}
    for key,value in body.items(): setattr(row,key,value)
    row.enabled=False; row.version+=1
    db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="demand_rule",entity_id=row.id,action="draft_updated",previous_value=previous,new_value=body,pricing_version=row.version)); db.commit()
    return {c.name:getattr(row,c.name) for c in row.__table__.columns}


@router.post("/admin/pricing/demand-rules/{rule_id}/activate")
def activate_demand_rule(rule_id:str,admin=Depends(require_admin("pricing.activate")),db:Session=Depends(get_db)):
    row=db.query(DemandPricingRule).filter(DemandPricingRule.id==rule_id).with_for_update().first()
    if row is None: raise HTTPException(404,"Demand pricing rule not found")
    if row.effective_from is None: raise HTTPException(422,"An effective start date is required")
    if row.minimum_demand_ratio is not None and row.maximum_demand_ratio is not None and row.minimum_demand_ratio>=row.maximum_demand_ratio:
        raise HTTPException(422,"Demand ratio minimum must be lower than maximum")
    # Prevent ambiguous matching bands for rules with overlapping effective dates.
    for other in db.query(DemandPricingRule).filter(DemandPricingRule.enabled.is_(True),DemandPricingRule.id!=row.id,DemandPricingRule.demand_level==row.demand_level).all():
        begins=max(x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x for x in (row.effective_from,other.effective_from) if x is not None)
        ends=[x.replace(tzinfo=timezone.utc) if x.tzinfo is None else x for x in (row.effective_until,other.effective_until) if x is not None]
        if ends and begins>=min(ends): continue
        lo1=row.minimum_demand_ratio if row.minimum_demand_ratio is not None else D("-Infinity")
        hi1=row.maximum_demand_ratio if row.maximum_demand_ratio is not None else D("Infinity")
        lo2=other.minimum_demand_ratio if other.minimum_demand_ratio is not None else D("-Infinity")
        hi2=other.maximum_demand_ratio if other.maximum_demand_ratio is not None else D("Infinity")
        if max(lo1,lo2)<min(hi1,hi2): raise HTTPException(409,"Demand rule overlaps another active rule")
    row.enabled=True; row.version+=1
    db.add(PricingAudit(admin_user_id=admin.firebase_uid,entity_type="demand_rule",entity_id=row.id,action="activated",pricing_version=row.version,new_value={"enabled":True}))
    db.commit(); return {"id":row.id,"enabled":row.enabled,"version":row.version}


@router.get("/admin/pricing/audit")
def audit(limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),_:object=Depends(require_admin("pricing.read")),db:Session=Depends(get_db)):
    rows=db.query(PricingAudit).order_by(PricingAudit.created_at.desc()).offset(offset).limit(limit).all()
    return {"items":[{c.name:getattr(r,c.name) for c in r.__table__.columns} for r in rows],"limit":limit,"offset":offset}


@router.get("/admin/pricing/bookings")
def pricing_bookings(limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),_:object=Depends(require_admin("pricing.read")),db:Session=Depends(get_db)):
    q=db.query(PricingQuote).filter(PricingQuote.job_id.is_not(None)).order_by(PricingQuote.created_at.desc())
    total=q.count(); rows=q.offset(offset).limit(limit).all()
    return {"items":[{"job_id":r.job_id,**_quote_json(r),"confirmed_at":r.consumed_at} for r in rows],"total":total,"limit":limit,"offset":offset}


class HeartbeatBody(BaseModel):
    model_config=ConfigDict(extra="forbid")
    session_identifier: str = Field(min_length=8,max_length=160)
    device_platform: str | None = Field(default=None,max_length=30)
    is_foreground: bool = True


@router.post("/presence/heartbeat")
def heartbeat(body:HeartbeatBody,user:User=Depends(authenticated_user),db:Session=Depends(get_db)):
    now=datetime.now(timezone.utc); settings=db.query(PricingSettings).first()
    if settings is None: raise HTTPException(503,"Presence operational settings are unavailable")
    ttl=settings.presence_ttl_seconds
    if user.role not in ("worker","shop_owner","shopkeeper"): raise HTTPException(403,"Unsupported user role")
    row=db.query(PresenceSession).filter(PresenceSession.user_id==user.id,PresenceSession.session_identifier==body.session_identifier).with_for_update().first()
    if row is None: row=PresenceSession(user_id=user.id,session_identifier=body.session_identifier,availability_status="unavailable"); db.add(row)
    row.device_platform=body.device_platform; row.is_foreground=body.is_foreground; row.last_heartbeat_at=now; row.expires_at=now+timedelta(seconds=ttl); row.updated_at=now
    db.commit(); return {"online":body.is_foreground,"expires_at":row.expires_at,"server_time":now,"heartbeat_interval_seconds":settings.heartbeat_interval_seconds}


@router.post("/presence/offline")
def offline(body:HeartbeatBody,user:User=Depends(authenticated_user),db:Session=Depends(get_db)):
    row=db.query(PresenceSession).filter(PresenceSession.user_id==user.id,PresenceSession.session_identifier==body.session_identifier).first()
    if row: row.is_foreground=False; row.availability_status="unavailable"; row.expires_at=datetime.now(timezone.utc)
    if user.role == "worker": db.query(WorkerLocation).filter(WorkerLocation.user_id==user.id, WorkerLocation.job_id.is_(None)).delete(synchronize_session=False)
    db.commit()
    return {"online":False}


class AvailabilityBody(BaseModel):
    model_config=ConfigDict(extra="forbid")
    available: bool


@router.patch("/workers/me/availability")
def availability(body:AvailabilityBody,user:User=Depends(authenticated_user),db:Session=Depends(get_db)):
    require_role(user,"worker")
    db.query(PresenceSession).filter(PresenceSession.user_id==user.id,PresenceSession.expires_at>datetime.now(timezone.utc)).update({PresenceSession.availability_status:"available" if body.available else "unavailable"})
    db.commit(); return {"available":body.available}


@router.get("/workers/me/availability")
def get_availability(user:User=Depends(authenticated_user),db:Session=Depends(get_db)):
    require_role(user,"worker")
    now=datetime.now(timezone.utc)
    value=db.query(PresenceSession.id).filter(PresenceSession.user_id==user.id,PresenceSession.expires_at>now,
        PresenceSession.availability_status=="available").first() is not None
    return {"available":value}


@router.get("/admin/presence/summary")
def presence_summary(_:object=Depends(require_admin("presence.read")),db:Session=Depends(get_db)):
    now=datetime.now(timezone.utc)
    rows=db.query(PresenceSession,User.role).join(User,User.id==PresenceSession.user_id).filter(PresenceSession.expires_at>now,User.is_active.is_(True)).all()
    online_workers={s.user_id for s,role in rows if role=="worker"}; online_recruiters={s.user_id for s,role in rows if role in ("shop_owner","shopkeeper")}
    available={s.user_id for s,role in rows if role=="worker" and s.availability_status=="available"}
    return {"online_workers":len(online_workers),"online_recruiters":len(online_recruiters),"available_workers":len(available),
        "registered_workers":db.query(User.id).filter(User.role=="worker").count(),
        "registered_recruiters":db.query(User.id).filter(User.role.in_(("shop_owner","shopkeeper"))).count(),"last_updated_at":now}
