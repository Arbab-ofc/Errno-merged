# ERRNO Admin Portal

React 19 + Vite portal integrated with the shared FastAPI backend. The original bundled `src/main.js` is retained for reference; `index.html` now loads the maintainable authenticated JSX application.

## Local setup

```sh
npm ci
cp .env.example .env.local
npm run dev
```

Configure the Firebase Web client identifiers for the existing `errno-pvt-ltd` Firebase project in the ignored `.env.local`. These are public client configuration values; never put a Firebase Admin service-account key in this directory. Set `VITE_API_BASE_URL` to the local FastAPI server. Do not commit `.env.local`.

Admin sign-in requires Google Sign-In and the backend's persisted UID permission. A Firebase login alone does not grant portal access. The API server must have its reviewed migration applied and an administrator provisioned through `Android/Backend/tools/provision_admin.py`; see [backend operations](../Android/Backend/ADMIN_OPERATIONS.md).

## Verification

```sh
npm test
npm run build
```

Dashboard, shop owners, workers, jobs, and System Health use backend responses. Bookings, Categories, Attendance, Ratings, Reports/Disputes, and Notifications remain visible but unavailable pending canonical backend contracts. Settings are local-only preferences.

See [the Phase 1 + 2 implementation report](../ADMIN_PHASE_1_2_IMPLEMENTATION_REPORT.md) for API contracts, security design, test results, and deployment requirements.
