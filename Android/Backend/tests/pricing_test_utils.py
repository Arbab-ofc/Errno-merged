"""Test-only helper for legacy job lifecycle cases now requiring locked quotes."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid

from models import PricingQuote


def insert_job_quote(factory, user_id, *, duration_hours=8, area_id=None,
                     service_start_at=None, final_price=Decimal("100.00"),
                     expires_in=timedelta(minutes=5)):
    now = datetime.now(timezone.utc)
    service_start_at = service_start_at or now + timedelta(days=1)
    final_price = Decimal(final_price)
    quote_id = str(uuid.uuid4())
    quote = PricingQuote(
        id=quote_id, user_id=user_id, duration_hours=duration_hours,
        service_start_at=service_start_at, area_id=area_id,
        base_price=final_price, maximum_price=final_price,
        time_multiplier=Decimal("1"), demand_multiplier=Decimal("1"),
        raw_price=final_price, final_service_charge=final_price,
        commission_rate=Decimal("0"), commission_amount=Decimal("0"),
        worker_payout_amount=final_price, pricing_rule_version=1,
        expires_at=now + expires_in, status="active",
    )
    with factory() as db:
        db.add(quote)
        db.commit()
    return quote_id, service_start_at.isoformat()
