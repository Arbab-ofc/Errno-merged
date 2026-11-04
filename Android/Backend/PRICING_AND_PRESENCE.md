# Pricing and presence operations

## Schema deployment

Pricing/presence are added by revision `a45d92e27c11`; `b61c4e90f2a7` corrects the lower boundary to use only `base_price`; `c42af1b73d90` adds address-keyed area overrides; `d91a2c7f4e60` stages global settings changes until activation; `e50b73a1c260` preserves raw quote precision; `f84e2d6a91b3` merges pricing with the existing job-lifecycle branch; and `3b7280d1c6a4` records each quote's component rule IDs and versions. Apply the canonical chain using `alembic_canonical/README`. The correction copies any previously-entered minimum into an unset base before dropping the redundant columns. Seeded reference maxima remain disabled drafts; production base prices are configured as proposals in the section below. Existing jobs and applications are untouched. The singleton active settings row remains unchanged until administrator activation.

## Configuration and approval

Grant the server managed permissions `pricing.read`, `pricing.write`, `pricing.activate`, and `presence.read` using `tools/provision_admin.py`. The admin must configure base, maximum, effective dates, commission rate, quote validity, rounding policy, timezone, and the combined multiplier cap before quotes can be generated. The only duration-price invariant is `base_price <= maximum_price`. Duration, time-band, demand-rule, and area changes are drafts first. Activation requires `pricing.activate`. No suggested commission, multiplier, or TTL is seeded.

Time rules use IANA timezone identifiers. Active time rules that overlap in the same zone cannot both be activated. If a different timezone already has active rules, activation is refused because exclusivity cannot be proven. Demand selection uses active open jobs / unique available online workers and requires exactly one configured rule to match. Zero workers requires a rule with `availability_thresholds.zero_available_workers=true`. An area override matches normalized address text from the existing canonical `shops.address` / `jobs.location` fields. With no matching active area override, pricing falls back to global duration and time/demand rules.

## 2026-11-01 proposed configuration (draft only)

The production administrator requested a recommendation anchored on the illustrative 1-hour ₹120 base / ₹160 maximum. Draft base recommendations use 75% of each seeded reference maximum, rounded to the nearest rupee with half-up rounding. This is a proposal method, not approved commercial policy. The 4-, 5-, and 6-hour maxima are provisional, so their derived base recommendations are provisional too. All duration rows remain disabled and `approval_status=draft`; effective start dates remain unset pending approval.

| Duration | Proposed base | Reference maximum | State |
|---:|---:|---:|---|
| 1 hour | ₹120 | ₹160 | Draft |
| 2 hours | ₹180 | ₹240 | Draft |
| 3 hours | ₹240 | ₹320 | Draft |
| 4 hours | ₹315 | ₹420 provisional | Draft |
| 5 hours | ₹383 | ₹510 provisional | Draft |
| 6 hours | ₹469 | ₹625 provisional | Draft |
| 7 hours | ₹540 | ₹720 | Draft |
| 8 hours | ₹623 | ₹830 | Draft |
| 9 hours | ₹690 | ₹920 | Draft |
| 10 hours | ₹750 | ₹1,000 | Draft |
| 11 hours | ₹825 | ₹1,100 | Draft |
| 12 hours | ₹900 | ₹1,200 | Draft |

The singleton settings draft proposes 8% commission (the original proposal), 300-second quote validity (the original five-minute example), `half_up` nearest-rupee rounding, and `Asia/Kolkata` for India service times. Surge, time adjustments, and demand adjustments are proposed disabled until their multipliers and thresholds are approved; therefore no combined surge cap or time/demand rules were invented. Existing presence heartbeat/expiry settings (60/180 seconds) are carried into the draft unchanged. None of these proposed settings is active. An administrator must review all values and set effective dates before activation.

## APIs

Mobile: `GET /api/v1/pricing/durations`, `POST /api/v1/pricing/quotes`, `GET /api/v1/pricing/quotes/{quote_id}`, `GET /api/v1/jobs/{job_id}/pricing`, `GET /api/v1/jobs/{job_id}/worker-payout`, `POST /api/v1/presence/heartbeat`, `POST /api/v1/presence/offline`, and `PATCH /api/v1/workers/me/availability`.

Admin: duration list/update and activation, settings read/update, time and demand list/create/update/activate/deactivate, area override list/create/update/activate, `POST /api/v1/admin/pricing/preview`, paginated audit and booking snapshots, and `GET /api/v1/admin/presence/summary`.

`POST /jobs` requires a server-generated quote ID; job pay is taken from the quote snapshot, never from the client amount. Legacy jobs have no reconstructed financial data and pricing reads return an explicit 404 for them.

## Presence

Sessions are keyed by user and client-generated per-device session identifier. Server heartbeat time and configurable TTL determine online status. Counts deduplicate user IDs across devices. `availability_status` starts unavailable; worker availability must be explicitly enabled. Expired rows are excluded from calculations and can be periodically purged with a database maintenance job if retention policy requires it.

## Known rollout boundary

No commercial prices or rates are auto-approved by these revisions. Android and iOS now use backend quotes for posting, display the quote before Android confirmation and the quote breakdown before iOS confirmation, and load authoritative worker payouts before application. Both apps heartbeat while foregrounded, offline on background/logout, and expose explicit worker availability. Admin overview and pricing views show live presence counts. Full end-to-end verification remains for the final project phase.
