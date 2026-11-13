# Google Maps Environment Setup

The Android and iOS Maps SDK keys are distinct application credentials. Do not paste either key into the root `.env` and expect the apps to load it automatically.

## Android

Copy `Android/gradle.properties.local.example` to the ignored `Android/gradle.properties.local` and set `ERRNO_GOOGLE_MAPS_ANDROID_API_KEY`. The Gradle build injects it into the Maps SDK manifest metadata. Restrict it to Android package `com.erno.app`, the relevant signing certificate SHA-1 fingerprint(s), and Maps SDK for Android.

## iOS

The Xcode target loads `iOS/Local.xcconfig.example` as its base configuration. Copy it to the ignored `iOS/Local.xcconfig` and set `ERRNO_GOOGLE_MAPS_IOS_API_KEY` there; the example optionally includes that private file so it overrides the placeholder automatically. The app supplies the value to Google Maps SDK at launch. Restrict the key to bundle identifier `com.errno.app` and Maps SDK for iOS.

The root `.env.example` records both setting names but contains placeholders only. The Android and iOS keys must not be interchanged. In Google Cloud, enable billing and activate Maps SDK for Android and Maps SDK for iOS. Do not enable Places, Geocoding, Routes or Navigation for this phase. Photon remains in use for address search and reverse lookup only. For project creation, restrictions, quotas and alerts, see `OWNER_CREDENTIALS_CHECKLIST.md`.
