# Maps Configuration Audit

The native app maps require two independent Google Maps Platform credentials:

| Setting | Consumer | Restriction | Secret source |
|---|---|---|---|
| `ERRNO_GOOGLE_MAPS_ANDROID_API_KEY` | Android Maps SDK | Android application ID `com.erno.app` plus signing certificate SHA-1; Maps SDK for Android | ignored `Android/gradle.properties.local` |
| `ERRNO_GOOGLE_MAPS_IOS_API_KEY` | iOS Maps SDK | iOS bundle identifier `com.errno.app`; Maps SDK for iOS | ignored `iOS/Local.xcconfig` |

No real Maps credential is checked into this repository. Google Maps URLs used for external directions need no API key. Photon is retained for address search. The backend's existing OSRM route endpoint and configuration are retained for API compatibility; the native applications no longer request route geometry or ETA. Backend job responses expose the related shop name and persisted job address so worker screens can label existing coordinates. No database, dispatch, nearby-discovery, tracking or notification behavior changed.

Configure billing, quotas and alerts in the owner-controlled Google Cloud project. Alerts are not hard spending caps. Review current India-specific prices and eligibility before launch because pricing and terms can change.
