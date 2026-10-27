# Errno iOS — Implementation Plan

> Strict phased approach. Read this file at the start of every session.
> Mark [x] immediately after completing a phase. Never skip phases.

---

## Phase 1: Foundation, Memory & Design System ✅

- [x] Create `brain.md` with full architecture documentation
- [x] Create `plans.md` with phased checklist
- [x] Create `Theme/Color+Extensions.swift` — brand color palette
- [x] Create `Theme/Typography.swift` — font styles & ViewModifiers
- [x] Create `Theme/Theme.swift` — spacing, radius, shadow constants
- [x] Create `Components/ErrnoLogo.swift` — animated logo
- [x] Create `Components/PrimaryButton.swift` — primary CTA button
- [x] Create `Components/SecondaryButton.swift` — outlined button
- [x] Create `Components/ErrnoTextField.swift` — styled text field
- [x] Create `Components/OTPField.swift` — 6-box OTP input component

---

## Phase 2: Navigation & Authentication Flow ✅

- [x] Create `Navigation/AppRouter.swift` — NavigationStack + route enum
- [x] Update `ErrnoApp.swift` to use AppRouter as root
- [x] Create `Views/Auth/SplashView.swift` — scale/alpha animations, 2.5s auto-navigate
- [x] Create `Views/Auth/RoleSelectionView.swift` — Shopkeeper vs Worker role picker
- [x] Create `ViewModels/Auth/AuthViewModel.swift`
- [x] Create `Services/AuthService.swift` — mock phone + OTP auth
- [x] Create `Views/Auth/LoginView.swift` — 10-digit phone input + validation
- [x] Create `ViewModels/Auth/OTPViewModel.swift` — OTP state + 30s timer logic
- [x] Create `Views/Auth/VerifyOTPView.swift` — 6-digit OTP with countdown

---

## Phase 3: Shopkeeper Core Views ✅

- [x] Create `Models/User.swift`, `Models/Job.swift`, `Models/Application.swift`
- [x] Create `Services/MockData.swift` — seed jobs, applications, users
- [x] Create `Services/JobService.swift` — mock CRUD
- [x] Create `Views/Shopkeeper/ShopkeeperRootView.swift` — 4-tab shell
- [x] Create `ViewModels/Shopkeeper/ShopkeeperDashboardViewModel.swift`
- [x] Create `Views/Shopkeeper/ShopkeeperDashboardView.swift` — active jobs list
- [x] Create `ViewModels/Shopkeeper/PostJobViewModel.swift` — wizard state
- [x] Create `Views/Shopkeeper/PostJobView.swift` — step 1+2 (Category + Map Pin)
- [x] Create `Views/Shopkeeper/PayStructureView.swift` — step 3 (pay setup)
- [x] Create `Views/Shopkeeper/PreviewJobView.swift` — step 4 (review + submit)
- [x] Create `Views/Shopkeeper/ApplicationsView.swift` — applicant list + hire action

---

## Phase 4: Worker Core Views & Native MapKit ⏳

- [ ] Create `Views/Worker/WorkerRootView.swift` — 4-tab shell
- [ ] Create `ViewModels/Worker/WorkerHomeViewModel.swift` — gig map state
- [ ] Create `Views/Worker/WorkerHomeView.swift` — full-screen MapKit + gig Annotations
- [ ] Create `Views/Worker/WorkerJobDetailsView.swift` — job details + accept + navigate
- [ ] Create `Views/Worker/WorkerMyJobsView.swift` — active/past jobs list

---

## Phase 5: Payments & Profiles ⏳

- [ ] Create `Models/Earning.swift`
- [ ] Create `ViewModels/Worker/WorkerEarningsViewModel.swift`
- [ ] Create `Views/Worker/WorkerEarningsView.swift` — earnings + withdrawal
- [ ] Create `Payments/PaymentCheckoutView.swift` — UPI / Card mock UI
- [ ] Create `Payments/PaymentSuccessView.swift` — success animation
- [ ] Create `Views/Shopkeeper/ShopkeeperProfileView.swift`
- [ ] Create `Views/Worker/WorkerProfileView.swift`

---

## Notes

- After each phase, **stop and wait for user to build in Xcode**.
- Only start next phase after user confirms successful build.
- Update `brain.md` Session Ledger whenever a phase is marked complete.
