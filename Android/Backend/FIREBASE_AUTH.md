# Firebase Google authentication configuration

The backend expects Firebase project `errno-pvt-ltd`. It uses Firebase Admin ID-token verification and never accepts a client-supplied UID as identity.

## Backend credentials

For local development, set `FIREBASE_PROJECT_ID=errno-pvt-ltd` and either `GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json` or configure Google Application Default Credentials. Attach a least-privilege runtime identity in production. Do not put the service-account file in this repository or either mobile app.

The repository has schema drift that must be resolved before migration: Alembic's legacy user model uses integer IDs and normalized/legacy tables, while the FastAPI runtime model in `models/__init__.py` uses UUID string IDs and different table definitions. The additive migration is not safe to apply until the deployed schema and runtime mapping are reconciled. Production startup no longer runs `create_all`; PostgreSQL changes must be migration-only.

### Safe schema reconciliation plan

1. Read the actual deployed schema with read-only queries and capture a schema-only backup. Record `alembic current`, `alembic heads`, the users table primary-key type, all foreign keys to users, and whether deployed tables match `models/__init__.py` or the legacy Alembic models.
2. Select the canonical schema that preserves deployed user IDs and relationships. Do not convert IDs or merge accounts by email as part of this phase. Update ORM mappings and the migration environment to represent that schema consistently; retain Firebase UID as nullable and unique for legacy accounts.
3. Create a forward-only migration for the verified schema. Exercise upgrade and downgrade behavior on an anonymized clone, including nullable phone/role rows, duplicate UID races, and existing shop/job foreign keys. Confirm legacy OTP records and user IDs remain intact.
4. Run backend and mobile contract tests against that clone, then obtain a reviewed deployment window and backup before any production migration. No production migration has been run for Phase 2.

Until those checks pass, do not apply the migration to production. A disposable SQLite smoke test may use the runtime model, but it does not validate the PostgreSQL migration.

```sh
cd Android/Backend
alembic upgrade head
```

The Firebase login creates a profile with no role. The authenticated client may set its selected role once (`worker` or `shop_owner`) during onboarding; later role changes return 409. Existing email matches are never linked automatically.

## Android

Set Gradle property `ERRNO_API_BASE_URL` to the backend origin (HTTPS outside local emulator builds). The app uses `default_web_client_id` generated from `google-services.json`.

The current JSON contains an Android OAuth client for `com.erno.app` and a web OAuth client. The local debug SHA-1 must match the Android OAuth client's `certificate_hash`; register the debug and release SHA-1 and SHA-256 fingerprints in Firebase Console. Retrieve local fingerprints with:

```sh
cd Android
./gradlew signingReport
```

## iOS

The current plist contains `CLIENT_ID` and `REVERSED_CLIENT_ID`. `ErrnoApp-Info.plist` registers the reversed ID as the app URL scheme. Configure `ERRNO_API_BASE_URL` in the Xcode build settings for each environment.

## API behavior

- `POST /api/v1/auth/firebase`: verifies the bearer token and creates or retrieves the PostgreSQL profile.
- `GET` and `PATCH /api/v1/users/me`: access the authenticated profile; role can only be selected once during onboarding.
- `POST /api/v1/auth/logout`: compatibility acknowledgement; Firebase ID tokens remain valid until expiry/revocation, so clients clear Firebase local state.

Job creation, applications, job status updates, shop access, and the legacy phone-based profile route require Firebase authentication. Public job browsing remains public. Legacy OTP routes are retained and their fabricated tokens are not accepted by protected routes.
