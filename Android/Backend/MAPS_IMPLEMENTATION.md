# ERRNO maps configuration and API

The native apps load `errno-map/index.html` from their own bundle. Leaflet 1.9.4 and Leaflet.VectorGrid are bundled; vector map tiles come from OpenFreeMap and carry OpenStreetMap attribution. Tile delivery, Photon search, reverse lookup and OSRM routing need network access. Search-only mode and manual address entry remain available when services fail.

Configure service URLs per Android build with `ERRNO_PHOTON_ENDPOINT`, `ERRNO_OSRM_ENDPOINT`, and `ERRNO_TILE_ENDPOINT` Gradle properties or `Android/gradle.properties.local`. iOS reads `ERRNO_PHOTON_ENDPOINT`, `ERRNO_OSRM_ENDPOINT`, and `ERRNO_TILE_ENDPOINT` from the app Info.plist. Defaults target the public Photon and OSRM demo instances for limited development/testing; deploy a self-hosted or contracted endpoint for production. OSRM durations are approximate route estimates without live traffic.

## API

- `POST /jobs` accepts the existing address fields plus optional `latitude` and `longitude`; both must be present together.
- `PUT /api/v1/workers/me/location` accepts a foreground location pulse only while the authenticated worker has an unexpired foreground `available` presence session.
- `GET /jobs/{job_id}/nearby-workers?radius_km=5` requires the owning shopkeeper, Postgres/PostGIS, an open job coordinate, active worker user, available foreground presence, and a worker update no older than five minutes. The default radius is 5 km, maximum 50 km. Returned coordinates are rounded to two decimal places.
- `PUT /jobs/{job_id}/tracking/location` accepts worker `{latitude, longitude}` only for their assigned job while status is `assigned` or `in_progress`.
- `GET /jobs/{job_id}/route` returns OSRM GeoJSON, road distance and baseline minutes for an assigned active job; it is not a live traffic ETA.
- `GET /jobs/{job_id}/tracking/location` and `WS /ws/jobs/{job_id}/tracking` require the job-owning shopkeeper; exact position is returned only while the job is active. WebSocket clients authenticate with an Authorization Bearer header and send a text heartbeat to receive updates. `online`, `stale`, `disconnected` and `ended` states are supported.

Apply migration `eb72a31c4890` using the canonical Alembic configuration only after confirming that the database is on the canonical runtime schema at revision `a8b72c4e9d11`. The repository documents migration drift between legacy and runtime schemas. The migration requires PostGIS extension creation privileges. Do not apply it to an unverified or production database.
