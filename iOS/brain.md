# Errno iOS — Architecture Brain

> **Last Updated:** Phase 1 — Foundation, Memory & Design System  
> **Target:** iOS 17+ | SwiftUI | Swift 5.9+ | MVVM + UDF

---

## 1. App Identity

| Property      | Value                                               |
|---------------|-----------------------------------------------------|
| Bundle ID     | `com.errno.app`                                     |
| App Name      | Errno                                               |
| Min iOS       | 17.0                                                |
| Architecture  | MVVM + Unidirectional Data Flow (UDF)               |
| UI Framework  | 100% SwiftUI (no UIKit)                             |
| Concurrency   | Swift async/await                                   |
| State Mgmt    | `@Observable` macro (iOS 17 observation framework)  |
| Maps          | Native MapKit (iOS 17 Map API)                      |
| Backend       | Mock (Supabase-ready data models)                   |

---

## 2. Project Folder Structure

```
Errno/
├── ErrnoApp.swift
├── ContentView.swift               # Temporary placeholder
├── Theme/
│   ├── Color+Extensions.swift
│   ├── Typography.swift
│   └── Theme.swift
├── Components/
│   ├── ErrnoLogo.swift
│   ├── PrimaryButton.swift
│   ├── SecondaryButton.swift
│   ├── ErrnoTextField.swift
│   └── OTPField.swift
├── Models/
│   ├── User.swift
│   ├── Job.swift
│   ├── Application.swift
│   └── Earning.swift
├── Services/
│   ├── AuthService.swift
│   ├── JobService.swift
│   └── MockData.swift
├── ViewModels/
│   ├── Auth/
│   │   ├── AuthViewModel.swift
│   │   └── OTPViewModel.swift
│   ├── Shopkeeper/
│   │   ├── ShopkeeperDashboardViewModel.swift
│   │   └── PostJobViewModel.swift
│   └── Worker/
│       ├── WorkerHomeViewModel.swift
│       └── WorkerEarningsViewModel.swift
├── Views/
│   ├── Auth/
│   │   ├── SplashView.swift
│   │   ├── RoleSelectionView.swift
│   │   ├── LoginView.swift
│   │   └── VerifyOTPView.swift
│   ├── Shopkeeper/
│   │   ├── ShopkeeperRootView.swift
│   │   ├── ShopkeeperDashboardView.swift
│   │   ├── PostJobView.swift
│   │   ├── PayStructureView.swift
│   │   ├── PreviewJobView.swift
│   │   ├── ApplicationsView.swift
│   │   └── ShopkeeperProfileView.swift
│   └── Worker/
│       ├── WorkerRootView.swift
│       ├── WorkerHomeView.swift
│       ├── WorkerJobDetailsView.swift
│       ├── WorkerMyJobsView.swift
│       ├── WorkerEarningsView.swift
│       └── WorkerProfileView.swift
├── Navigation/
│   └── AppRouter.swift
└── Payments/
    ├── PaymentCheckoutView.swift
    └── PaymentSuccessView.swift
```

---

## 3. Design System Tokens

### 3.1 Color Palette

| Token                  | Hex       | Usage                                      |
|------------------------|-----------|--------------------------------------------|
| `ErrnoGreen`           | `#11382A` | Primary brand, headers, nav backgrounds    |
| `ErrnoLime`            | `#A4E637` | CTAs, highlights, active tab indicators    |
| `ErrnoNavy`            | `#0B121F` | Dark backgrounds, splash, modals           |
| `ErrnoBackground`      | `#F8F9FA` | App-wide light background                  |
| `ErrnoSurface`         | `#FFFFFF` | Cards, sheet surfaces                      |
| `ErrnoTextPrimary`     | `#0B121F` | Primary text                               |
| `ErrnoTextSecondary`   | `#6B7280` | Subtitles, captions                        |
| `ErrnoTextOnDark`      | `#FFFFFF` | Text on dark/green/navy backgrounds        |
| `ErrnoError`           | `#EF4444` | Validation errors                          |
| `ErrnoSuccess`         | `#22C55E` | Success states                             |
| `ErrnoStroke`          | `#E5E7EB` | Borders, dividers                          |

### 3.2 Typography Scale

| Style           | Font           | Size | Weight   |
|-----------------|----------------|------|----------|
| `displayLarge`  | SF Pro Rounded | 34   | Bold     |
| `displayMedium` | SF Pro Rounded | 28   | Bold     |
| `headlineLarge` | SF Pro Display | 24   | Semibold |
| `headlineMed`   | SF Pro Display | 20   | Semibold |
| `bodyLarge`     | SF Pro Text    | 17   | Regular  |
| `bodyMedium`    | SF Pro Text    | 15   | Regular  |
| `labelLarge`    | SF Pro Text    | 15   | Semibold |
| `labelSmall`    | SF Pro Text    | 12   | Medium   |
| `caption`       | SF Pro Text    | 11   | Regular  |

### 3.3 Spacing Scale

| Token | Value |
|-------|-------|
| XS    | 4     |
| SM    | 8     |
| MD    | 16    |
| LG    | 24    |
| XL    | 32    |
| XXL   | 48    |

### 3.4 Radius Scale

| Token | Value |
|-------|-------|
| SM    | 8     |
| MD    | 12    |
| LG    | 16    |
| XL    | 24    |
| Full  | 9999  |

---

## 4. MVVM + UDF Architecture

```
View  ──(user action)──►  ViewModel  ──(async call)──►  Service
  ▲                            │                            │
  │                            │ (updates @Observable)      │
  └────(observes state)────────┘◄───(returns Result)────────┘
```

- Views are passive — only render state, forward actions.
- ViewModels own all business logic, expose state via `@Observable`.
- Services are protocol-based (mock → Supabase swap).
- NavigationStack + AppRouter manages all route transitions.

---

## 5. Authentication Flow

```
SplashView (2.5s auto-navigate)
    ▼
RoleSelectionView (Shopkeeper | Worker)
    ▼
LoginView (10-digit phone)
    ▼
VerifyOTPView (6-digit OTP, 30s timer)
    ▼
ShopkeeperRootView  OR  WorkerRootView
```

---

## 6. Shopkeeper Flow (4 Tabs)

| Tab | View                    | Icon                  |
|-----|-------------------------|-----------------------|
| 0   | ShopkeeperDashboardView | house.fill            |
| 1   | PostJobView (wizard)    | plus.circle.fill      |
| 2   | ApplicationsView        | person.2.fill         |
| 3   | ShopkeeperProfileView   | person.crop.circle    |

**Job Posting Wizard:** Category → Map Pin → Pay Structure → Preview

---

## 7. Worker Flow (4 Tabs)

| Tab | View               | Icon                          |
|-----|--------------------|-------------------------------|
| 0   | WorkerHomeView     | map.fill                      |
| 1   | WorkerMyJobsView   | briefcase.fill                |
| 2   | WorkerEarningsView | indianrupeesign.circle.fill   |
| 3   | WorkerProfileView  | person.crop.circle            |

---

## 8. Key Architectural Decisions

| Decision             | Choice                         | Reason                                        |
|----------------------|--------------------------------|-----------------------------------------------|
| State management     | `@Observable` macro            | iOS 17 native, no ObservableObject boilerplate|
| Navigation           | `NavigationStack` + enum router| Type-safe routing, deep-link ready            |
| Maps                 | Native MapKit (iOS 17)         | Declarative, no UIKit bridge needed           |
| Fonts                | SF Pro (system)                | No external font dependency                   |
| OTP Timer            | `Timer.publish`                | Reactive countdown                            |
| Mock data            | Protocol-backed MockServices   | Swap to Supabase without touching ViewModels  |

---

## 9. Session Ledger

| Phase | Status     | Notes                                  |
|-------|------------|----------------------------------------|
| 1     | ✅ Complete | Foundation, Design System, Components  |
| 2     | ✅ Complete | Navigation & Authentication Flow       |
| 3     | ✅ Complete | Shopkeeper Core Views                  |
| 4     | ⏳ Pending  | Worker Core Views & Native MapKit      |
| 5     | ⏳ Pending  | Payments & Profiles                    |
