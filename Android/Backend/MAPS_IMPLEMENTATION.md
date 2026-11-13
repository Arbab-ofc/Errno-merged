# Maps and Location Architecture

Android and iOS render in-app maps with their native Google Maps SDKs. Shop jobs continue to store the exact selected latitude/longitude and human-readable address in the existing job fields; no database migration is required. Photon is temporarily used by the mobile pin picker for address search and reverse address lookup; it is not used to render maps. Reverse lookup is debounced after pin placement/drag completion and failures leave manual address editing available.

Google Maps credentials are separate per platform. See `../../docs/ENV_SETUP_GUIDE.md` for Android and iOS build injection and `../../docs/OWNER_CREDENTIALS_CHECKLIST.md` for key restrictions, quotas, and billing alerts. Do not configure Places, Geocoding, Routes, or Navigation SDK keys for this release.

Backend job responses now include the related shop name and the persisted job address alongside the existing coordinate fields. No database migration is required. PostGIS nearby discovery, worker availability filtering, foreground worker location updates, assigned-job location updates, and owner-authorized WebSocket tracking remain active. The OSRM-backed `GET /jobs/{job_id}/route` endpoint is retained for API compatibility, but the native apps no longer request road geometry or ETA. It must not be described to users as live traffic ETA.

Worker location remains foreground-only and follows the existing permission and visibility checks. Shop coordinates and the address remain available when device location permission is denied or GPS is disabled. Worker directions are opened externally using a Google Maps URL only after job acceptance; ERRNO does not provide in-app turn-by-turn guidance.
