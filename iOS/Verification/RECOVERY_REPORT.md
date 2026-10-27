# Errno iOS build and simulator investigation — 2026-10-27

## Result

The application builds successfully from two new, isolated DerivedData directories. The local domain checks pass. A standalone UI test harness also compiles. The simulator installer log eventually confirms installation, although the CLI timed out first. Functional launch and UI verification remain blocked by the simulator environment; no UI test pass or successful application screen is claimed.

All 190 files present in the initial tracked/untracked source baseline were preserved byte-for-byte. Android, backend code, the application Xcode project, application logic, navigation, Xcode and the installed runtime were not modified. No simulator was erased or deleted. No Git commit or push was performed.

## Audit before changes

- Branch: `feature/ios-frontend-phase-1` with substantial preexisting modified/untracked iOS implementation. Baseline captured before edits.
- Xcode: 27.1, build `27A9275`; developer directory `/Applications/Xcode.app/Contents/Developer`.
- SDK/runtime: iOS Simulator 27.1; runtime build `24A94425`, arm64. Runtime metadata lists only iPhone Duo as a supported device type. An attempted iPhone 17 creation was rejected as incompatible; no iPhone 17 was created.
- Free space at start: 49 GiB. Storage was sufficient for both builds.
- Application project/target/scheme: `iOS/Errno.xcodeproj`, `Errno`, `Errno`.
- Configurations: Debug and Release; project default Release. Verification explicitly used Debug.
- Deployment target: iOS 17.0; Swift language mode 5, default MainActor isolation, approachable concurrency enabled.
- Signing: Automatic with existing team `6MTUWR95N7`. Simulator builds used the command-line override `CODE_SIGNING_ALLOWED=NO`; no signing settings or accounts changed.
- No Swift packages, CocoaPods or other external package requirements found in the application project. The synchronized `Errno/` group includes new app sources automatically. Verification sources are outside that group.
- Entry: `Errno/ErrnoApp.swift`; SwiftUI `WindowGroup` injects `AppRouter` and its `LocalMarketplaceStore`. `AppRootView` selects splash/auth/worker/shopkeeper roots; auth navigation uses typed routes.
- Xcode includes `Contents/Applications/DeviceHub.app`, which was opened. There is no legacy `Simulator.app` at either expected Xcode path. Its absence alone was not treated as the cause of the failure.

## Recovery actions and evidence

Original device: iPhone Duo, `B035B8BF-FC66-45A8-80F9-C87FE414E0A8`.

1. Inspected device/runtime lists, initial boot status, display ports, screenshots, service logs and existing crash reports.
2. Restarted only this device without erasing data. Boot status again reported `Data Migration Failed` despite returning exit code 0. A zero exit code is therefore insufficient to establish a healthy boot in this environment.
3. Inspected both integrated displays explicitly. The initial default screenshot selected LCD-1 / screen 3 and was black. Primary-display capture later timed out. Neither constitutes a functional application screen.
4. Attempted installation and launch with bounded commands; both timed out.
5. Collected local diagnostics under `/tmp/errno-recovery-20261027/diagnostics`. Collection timed out, leaving partial diagnostic files; no archive-completion claim is made. Nothing was uploaded.
6. Shut down the original device and preserved it with all data.
7. Created a separate device, **Errno Verification Duo**, UUID `F93AC18D-9B8C-44F9-9262-0299F2FEA619`, using the existing runtime.
8. Its first boot reported `Finished` after migration. Screen 1 showed an Apple boot logo; screen 3 was black. Installation, app registry queries and launch subsequently stalled. A direct filesystem check found no installed third-party bundle on this device at that time.
9. Stopped the stalled first UI attempt, shut down the verification device, closed Device Hub and restarted CoreSimulatorService with SIGTERM. No directories or device contents were removed.
10. Rebooted the verification device. It then also reported `Data Migration Failed`. A 120-second installation retry, 60-second launch retry and subsequent screenshot attempts timed out.

Some timed-out simulator requests completed asynchronously later. The installation log confirms `Install successful for (Developer:Errno.Errno)` at 19:20:08, followed by removal of the pending LaunchServices operation after its registry save. The installed `Errno.app` bundle also exists on the fresh simulator. This confirms installation independently of the timed-out CLI. Later-arriving screenshots still show the Apple boot logo rather than Errno. Installation evidence was retained at `/tmp/errno-recovery-20261027/errno-installation-evidence.log`.

A separate launch attempt made after confirming installation (`launch --terminate-running-process`) timed out after 45 seconds. A delayed original-device capture, `original-secondary.png`, showed a partial lock-screen wallpaper with “Swipe up to open”; this confirms that a black capture of one Duo panel does not establish that every panel is black. It does not verify touch interaction or Errno launch. Device Hub accessibility inspection returned no windows and no menu bar, preventing menu-driven interaction through that route.

Finally, restarting only SpringBoard on the verification device returned exit 0, but its subsequently captured second display (`after-springboard-restart.png`) remained black. No usable Errno UI was obtained. The last disk-space check reported 44 GiB available. All 190 initial source files still matched their baseline hashes, and `git diff --check` passed.

The original device's `Library/Preferences/com.apple.migration.plist` records `DMLastMigrationResults.success = false`, with `com.apple.MobileSafari.migrator` and `com.apple.CloudTabsMigrator.migrator` failures lasting approximately 30 seconds each. On the separate device, all 35 recorded plugins report success, but the overall migration result is false. A compact read-only summary is saved at `/tmp/errno-recovery-20261027/migration-state-summary.json`.

This establishes migration failures and simulator-service unresponsiveness beyond Errno's source code. The underlying runtime/host cause is **not established**. Prior disk exhaustion is documented by earlier logs, but does not explain all current symptoms. No migration flags were edited to disguise failure, and no runtime or Xcode repair/reinstallation was attempted.

## Builds and tests

| Check | Actual result |
| --- | --- |
| Initial application build, new `DerivedData` | Passed, exit 0 |
| Final application build, new `FinalDerivedData` | Passed, exit 0 |
| Local checks within Codex sandbox | Failed because the Observation macro plugin could not execute correctly |
| Same local checks outside sandbox | Passed, exit 0 |
| Standalone UI harness `build-for-testing`, arm64 | Passed, exit 0 |
| First UI execution attempt | Stalled before test cases; interrupted for simulator-service recovery |
| Final UI execution retry after service recovery | Timed out after 180 seconds without a completed test case; no pass |
| Installation/launch on original device | Timed out; success not established |
| Installation on separate device | CLI timed out; installation later confirmed by installer log and installed bundle |
| Launch on separate device | Timed out; functional application screen not established |

The local executable checks exercise exact-ID job mutations, duplicate protection, application isolation, authorization guards, earnings/withdrawal balances, profiles, masked demo identity, OTP results/cancellation, posting submission and typed auth routing. They execute production model/service/ViewModel/router code on macOS, not an iOS UI.

The standalone `UI/` harness targets the already-installed `Errno.Errno` bundle. It is separate from the existing application project. Its tests cover a shopkeeper-to-worker marketplace journey, legal sheets/consent, invalid demo OTP, registration validation, worker role routing, DigiLocker simulation and process-local session reset. Compiling this harness does not establish that these flows passed on a simulator.

The only application-build warning observed was skipped AppIntents metadata extraction because no AppIntents.framework dependency exists. The generated executable contains arm64 and x86_64 simulator slices; its Info.plist confirms `Errno.Errno`, iOS 17.0 minimum, and `iPhoneSimulator` platform support.

The historical SpringBoard crash report contains EXC_BREAKPOINT / SIGTRAP. No new Errno crash report was found during inspection. That does not establish crash-free behavior because successful installation/launch was not verified.

## Functionality and backend boundaries

Source inspection confirms the requested authentication, worker and shopkeeper screens are present and wired into the existing router. UI behavior remains unverified due to the simulator blocker.

`MockAuthService` simulates sending and checking OTP; only the explicit local demo code `123456` succeeds. Registration stores an in-memory name and proceeds to demo OTP. `MockJobService` uses the shared process-local marketplace store. No URLSession authentication/job client or disk database exists in this iOS implementation.

Jobs, profiles, applications, verification and earnings survive role changes within one process; logout clears identity/navigation. App process termination clears the store. This is session-only behavior, not durable persistence. DigiLocker, payments, withdrawals, GPS, Google login and notifications are labeled simulations/placeholders; no external success was generated or claimed.

The backend is under `Android/Backend`. Its auth request schema uses `phone_number`, `otp_code` and `full_name`; Android DTOs use camelCase fields. Future API wiring must map those names and the backend's user fields explicitly. There is no current iOS API contract implementation to validate against a running backend. Backend integration, real credentials/OTP delivery, government verification, payment settlement and durable storage remain unimplemented, rather than merely unavailable test credentials.

## Android parity review

Compared Android `NavGraph.kt`, auth repository/DTOs, backend auth schemas, theme tokens, role selection, owner/worker ViewModels and the corresponding SwiftUI screens.

- The source hierarchies contain the corresponding owner dashboard/post-details/duration/location/preview/success/jobs/applications/profile routes and worker discovery/details/acceptance/my-jobs/earnings/profile/DigiLocker routes.
- Core green `#5B9600`, lime `#A4E637`, navy `#0B121F`, background `#F8F9FA` and secondary text `#6C757D` match.
- Both role screens use a 140-unit illustration area, 26-unit welcome heading, 14-unit subtitle, and 600-unit width cap. Some spacing, icon sizes, heading sizes and native text metrics differ. SF Symbols replace Android Material icons. Pixel parity cannot be established from source values alone.
- Android starts its NavHost at role selection; iOS presents an additional explicit Get Started splash.
- Android's fallback auth accepts any six-character OTP; iOS deliberately requires the documented demo code and supports a visible incorrect-code state.
- Both marketplace implementations are currently local. iOS's exact UUID mutations and idempotent completion/submission protect against Android's broad title/status-based updates. Those existing iOS safeguards were preserved.
- Android payment screens are not registered by its navigation graph. iOS payment screens likewise remain outside the main journey. No payment flow was falsely presented as integrated.
- Empty initial jobs, the default delivery draft and its two-hour ₹249 total are consistent. iOS's opt-in demo applicant fixtures and explicit local completion/withdrawal controls remain documented deviations.

No visual parity fixes were applied without a working simulator, and no 100% UI parity claim is made. Smaller screens, landscape, Dynamic Type, VoiceOver, keyboard overlap, loading/error rendering and touch targets still require actual runtime review.

## Artifacts and rerun commands

Artifacts: `/tmp/errno-recovery-20261027` (temporary; retain elsewhere if needed).

- `initial-build.log`, `final-build.log`: application builds.
- `local-checks-unsandboxed.log`: passing local checks.
- `ui-build.log`: passing UI test compilation.
- `fresh-ui-tests.log`, `UITests.xcresult`: interrupted first UI attempt; result bundle may be incomplete.
- `final-ui-retry.log`, `FinalUITests.xcresult`: final bounded attempt timed out before a completed case. The bundle may be incomplete. An earlier command was rejected for an unsupported timeout flag and was corrected; that rejection is not a test execution.
- `original-reboot.log`, `fresh-boot.log`, `fresh-reboot-after-service.log`: boot evidence.
- `original.png`, `original-reboot.png`: original simulator's black display captures.
- `original-secondary.png`: delayed partial lock-screen capture, not Errno. `original-primary.png`: delayed Apple-logo capture.
- `fresh-screen-1.png`: Apple boot logo; `fresh-screen-3.png`: black secondary display. Later-arriving `errno-launch.png`, `errno-after-service-restart.png` and `final-simulator.png` also show the Apple logo. These are diagnostic simulator captures, **not successful Errno screenshots**, despite the filenames.
- `source-baseline.json`, `source-integrity.json`, `migration-state-summary.json`, `runtimes.json`: audit evidence.
- `after-springboard-restart.png`: final black second-display capture after the non-destructive SpringBoard restart.

The final app bundle is `/tmp/errno-recovery-20261027/FinalDerivedData/Build/Products/Debug-iphonesimulator/Errno.app`.

Run from the repository root after the simulator environment is usable. Bootstatus must actually say Finished, and installation/launch must complete; these commands can currently hang on the affected environment.

```sh
xcodebuild -project iOS/Errno.xcodeproj -scheme Errno -configuration Debug \
  -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/errno-recovery-20261027/FinalDerivedData \
  CODE_SIGNING_ALLOWED=NO build

ERRNO_SIM_UUID=F93AC18D-9B8C-44F9-9262-0299F2FEA619
xcrun simctl bootstatus "$ERRNO_SIM_UUID" -b
open -a /Applications/Xcode.app/Contents/Applications/DeviceHub.app
xcrun simctl install "$ERRNO_SIM_UUID" \
  /tmp/errno-recovery-20261027/FinalDerivedData/Build/Products/Debug-iphonesimulator/Errno.app
xcrun simctl launch "$ERRNO_SIM_UUID" Errno.Errno
xcrun simctl io "$ERRNO_SIM_UUID" screenshot --display=1 /tmp/errno-rerun-screen.png

python3 -B iOS/Verification/check_local.py

xcodebuild test -project iOS/Verification/UI/ErrnoValidation.xcodeproj \
  -scheme ErrnoValidation -destination "platform=iOS Simulator,id=$ERRNO_SIM_UUID" \
  -derivedDataPath /tmp/errno-recovery-20261027/UITestDerivedData \
  -parallel-testing-enabled NO ARCHS=arm64 ONLY_ACTIVE_ARCH=YES CODE_SIGNING_ALLOWED=NO
```

Further recovery should begin with a host restart at a convenient time, then a simulator boot check. A host restart interrupts unrelated work and was not performed automatically. If failure persists, runtime/Xcode support investigation is required; reinstalling or changing them is outside the current safety rules. Erasing the original simulator is neither necessary to reproduce this problem nor authorized.
