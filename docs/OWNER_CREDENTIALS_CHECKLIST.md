# Owner Credentials Checklist: Google Maps

Create a Google Cloud project owned by ERRNO, enable billing, and enable only the Maps SDK for Android and Maps SDK for iOS. The mobile maps shown in this release use those SDKs. External Google Maps directions use Maps URLs and do not require a Maps API key.

Create two different keys:

| Key | Application restriction | API restriction | Runtime setting |
|---|---|---|---|
| Android Maps key | Android app `com.erno.app`; add the SHA-1 signing certificate fingerprint for every debug/release signer that needs access | Maps SDK for Android | `ERRNO_GOOGLE_MAPS_ANDROID_API_KEY` in `Android/gradle.properties.local` |
| iOS Maps key | iOS app bundle ID `com.errno.app` | Maps SDK for iOS | `ERRNO_GOOGLE_MAPS_IOS_API_KEY` in `iOS/Local.xcconfig` |

Do not use either mobile key as a server key. Restrict each key to the listed app and API, keep separate development and production keys where practical, rotate a key if exposed, and never commit real key values. Android SHA-1 values come from the signing certificates used for builds; include the Play App Signing certificate fingerprint for Play-distributed builds.

Set conservative per-SKU quotas, configure billing budgets and alert notifications, and review usage by SKU in Google Cloud Billing. Budget alerts notify owners but do not cap spending. Confirm current India pricing and account eligibility before launch. The launch design avoids Routes, Places, Geocoding and Navigation SDK calls; Photon remains the temporary address-search provider. Google pricing and terms can change.
