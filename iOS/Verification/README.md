# Phase 1 local frontend verification

The application uses one `LocalMarketplaceStore`, owned by `AppRouter` and injected into SwiftUI. It has no network or database persistence. Logout clears authentication and navigation; sandbox jobs/profiles remain in memory to allow owner/worker role testing. Relaunch clears the sandbox.

## Executable checks

From the repository root:

```sh
python3 -B iOS/Verification/check_local.py
```

This compiles the actual models, store, service adapter, authentication/posting ViewModels and router using the macOS Swift toolchain. The executable and compiler cache are outside the repository. It verifies exact-ID mutations, duplicate protection, OTP results/cancellation, profile propagation, masked identity, completion/earnings, withdrawal balances, posting submission and typed auth routing. It is not an iOS application build or a UI automation test.

All app Swift files can also be syntax-parsed with `swiftc -frontend -parse`. New app sources are included by the project's existing `PBXFileSystemSynchronizedRootGroup` for `Errno/`; verification sources are outside that group.

## Required iOS build on a machine with full Xcode

```sh
xcodebuild -project iOS/Errno.xcodeproj -scheme Errno -configuration Debug \
  -sdk iphonesimulator -derivedDataPath /tmp/errno-phase1-derived \
  CODE_SIGNING_ALLOWED=NO build
```

Implementation environment: Command Line Tools with Swift 6.3.3, no full Xcode or iOS simulator SDK. The command above stops at xcode-select's missing-Xcode error here. iOS linking, asset compilation, previews and simulator behavior are therefore unverified.

## Manual journeys still to run on iPhone 14 / iOS 17+

1. Splash → role → consent. Continue remains disabled until checked. Read both legal sheets; checkbox survives dismissal.
2. Owner registration/login → OTP `123456`; invalid OTP displays error. Leaving during verification must not navigate later. Countdown enables resend.
3. Post delivery and non-delivery jobs. Check category-derived title, six-day calendar window, time slots, 250-character description, fixed duration totals and custom positive values.
4. Edit from preview; submit once; success → Jobs. Verify dashboard, list and applicant counts share state.
5. In owner job details, opt into **Add Local Demo Applicants**. Accept/decline; verify only that job changes and other job applications stay pending.
6. Logout; log in as worker. The same open jobs appear. Accept one; confirmation → My Jobs selects Ongoing. Accepted jobs disappear from discovery.
7. Logout; log in as owner. In the assigned job details, **Simulate Shift Completion**. Only that shift completes. Payment checkout is deliberately not linked to this control.
8. Log in as worker. Completed jobs, rating and one earnings record appear. Simulate withdrawal; balance reduces without changing lifetime earnings.
9. Edit each role's profile; Cancel discards edits. Check support URLs and legal sheets.
10. Verification: use test Aadhaar digits only, consent, then demo OTP `123456`. Check masked ID and demo badge. No government service is contacted.
11. Open checkout/receipt through their Xcode previews only. Check all four payment methods, test-field validation, fixed ₹18 fee, simulation result and receipt sharing.
12. Review small/large text, VoiceOver, keyboard overlap, home indicator, landscape, smaller phones and Reduce Motion.

## Deliberate deviations and remaining visual QA

- Android's broad title/status job mutations are replaced with exact UUID matching.
- Android accepts any nonblank OTP; this demo consistently requires `123456` and exposes error/loading states.
- Newly accepted jobs initially show Ongoing, avoiding Android's empty Upcoming default.
- Owner completion is an explicitly labeled local test control; Android's completion methods had no reachable caller.
- Optional applicant fixtures replace contradictory automatic iOS seed lists.
- Withdrawal changes only a simulated balance; no financial claim is made.
- Payment views remain isolated because Android does not register them in navigation.
- SF Symbols, SwiftUI sheets/date picker and platform text metrics are approximations pending simulator comparison. Dynamic Type extremes and dialog dimensions still require runtime review.
- The inherited AppIcon catalog still has no supplied 1024px artwork. The original Android logo is copied byte-for-byte as `ErrnoLogo`, without upscaling or modifying Android assets.
- No live OTP, Google authentication, FastAPI requests, DigiLocker, GPS tracking, notifications, payments or bank withdrawals are implemented. Those belong to later integration work.
