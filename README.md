# Errno — Android Reference + iOS Development

## Layout
- `Android/`: Original Android Kotlin / Jetpack Compose project and FastAPI backend (reference source of truth).
- `iOS/`: Existing SwiftUI Xcode project, preserved without overwriting its implementation.

## Migration strategy
Continue development inside `iOS/`. Use `Android/app/src/main/` for design, navigation and business-logic parity, and `Android/Backend/` for backend API contracts and database models. Do not replace implemented SwiftUI screens with Android source files.

## Notes
- Android and iOS are separate native projects, packaged together for cross-reference. This is not a single combined build.
- Backend `.env` is intentionally excluded because it may contain private database credentials and secrets. Configure it locally before running the backend.
- The ZIP has not been compiled or run in Xcode/Android Studio.
