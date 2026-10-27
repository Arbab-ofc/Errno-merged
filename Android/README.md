# ⚡ ERRNO — On-Demand Workforce Marketplace (Android App)

[![Android](https://img.shields.io/badge/Platform-Android-green.svg?logo=android)](https://developer.android.com)
[![Kotlin](https://img.shields.io/badge/Language-Kotlin%202.2.10-purple.svg?logo=kotlin)](https://kotlinlang.org/)
[![Jetpack Compose](https://img.shields.io/badge/UI-Jetpack%20Compose%20M3-4285F4.svg?logo=jetpackcompose)](https://developer.android.com/jetpack/compose)
[![AGP](https://img.shields.io/badge/AGP-9.4.1-blue.svg)](https://developer.android.com/studio/releases/gradle-plugin)

**ERRNO** is a dual-sided mobile marketplace platform that connects **Shopkeepers / Business Owners** needing temporary, on-demand staff with nearby **Workers & Independent Service Providers** looking for daily-wage shifts and delivery opportunities.

---

## 🌟 Key Highlights & Features

### 🏪 Shopkeeper / Business Owner Flow
- **⚡ 15-Minute Guarantee**: Fast, reliable access to verified temporary workers (`ERRNO Guarantee: Temporary Worker within 15 minutes`).
- **📝 Step-by-Step Job Posting**: Post work opportunities with flexible shift durations (2 hrs, 4 hrs, 8 hrs, or custom hours/rates).
- **📍 Smart Location Selection**:
  - **1-Tap GPS Auto-Detection**: Auto-detects current store location with one tap.
  - **Quick-Selection Chips**: Tap popular market chips (`Okhla Market`, `Sector 18 Noida`, `Nehru Place`, etc.) to fill addresses without typing.
  - **Map Pin Presets**: Adjust store map pin using interactive presets (`Main Gate`, `Delivery Bay`, `Metro Station Exit`).
- **👥 Worker Applications & Hiring**: Review applicant profiles, experience, past ratings, and contact workers directly via Call or WhatsApp.
- **📊 Shop Dashboard & Analytics**: Real-time tracking of active jobs, applicant counts, and store profile options.

---

### 👷 Worker / Daily Wage Partner Flow
- **🔍 Nearby Shift Discovery**: Browse available shifts filtered by categories (*Store Helper*, *Delivery Partner*, *Counter Staff*, *Inventory Assistant*).
- **🗺️ Interactive Map Canvas**: Custom Jetpack Compose Canvas map with route lines, pulse indicators, dark/light theme toggle, and 1-tap Google Maps directions.
- **🔒 DigiLocker Aadhaar Verification**: Built-in identity verification workflow using masked Aadhaar integration.
- **💰 Shift Earnings & History**: Track daily earnings, accepted shift status (`Ongoing` ➔ `Completed`), and past ratings.

---

### 📜 Legal & Compliance Onboarding
- **🛡️ Onboarding Consent Gate**: Onboarding agreement gate requiring users to review and accept the **Terms of Service** & **Privacy Policy** before proceeding to role selection/login.
- **📄 Interactive Legal Viewers**: Complete in-app legal document viewers for [Privacy Policy](app/src/main/java/com/erno/app/ui/screens/legal/PrivacyPolicyScreen.kt) and [Terms & Conditions](app/src/main/java/com/erno/app/ui/screens/legal/TermsConditionsScreen.kt).
- **🔑 Mobile OTP Authentication**: Quick 10-digit phone number validation and 6-digit OTP verification.

---

## 🏗️ Architecture & Tech Stack

The ERRNO frontend is built following modern Android architecture guidelines (**MVVM**, **Single Activity Architecture**, **Unidirectional Data Flow**):

- **Language**: [Kotlin](https://kotlinlang.org/) (100% Idiomatic Kotlin)
- **UI Framework**: [Jetpack Compose](https://developer.android.com/jetpack/compose) with Material 3 Design System
- **Navigation**: [Jetpack Navigation Compose](https://developer.android.com/jetpack/compose/navigation)
- **State Management**: Kotlin Coroutines, `StateFlow`, `mutableStateOf`, and Jetpack `ViewModel`
- **Custom Graphics**: Jetpack Compose `Canvas` rendering custom map roads, dashed paths, and animated pulse rings
- **Build System**: Gradle 9.6 + Android Gradle Plugin 9.4.1

---

## 📁 Project Directory Structure

```text
app/src/main/java/com/erno/app/
├── data/
│   ├── model/                  # Data classes (JobPost, User, DurationPay, AuthModels)
│   └── repository/             # Data repositories
├── navigation/
│   ├── NavGraph.kt             # Navigation host & route definitions
│   └── Screen.kt               # Sealed class screen route definitions
├── ui/
│   ├── components/             # Reusable UI components
│   │   ├── ErnoBranding.kt     # Official ERNO logo & brand assets
│   │   ├── ShopkeeperNav.kt    # Shopkeeper 4-tab bottom navigation bar
│   │   ├── WorkerNav.kt        # Worker 4-tab bottom navigation bar
│   │   └── WorkerLocationMapView.kt # Custom Canvas route & map component
│   ├── screens/
│   │   ├── auth/               # Login, Register, DigiLocker, and OTP screens
│   │   ├── legal/              # Privacy Policy, Terms & Conditions, and Consent Gate
│   │   ├── role/               # Dual Role Selection Screen (Shopkeeper vs Worker)
│   │   ├── shopkeeper/         # Shopkeeper Dashboard, Post Job, Applications, Profile
│   │   └── worker/             # Worker Home, Job Details, Earnings, Profile
│   └── theme/                  # Material 3 Color tokens (ErnoGreen, ErnoLime), Typography
```

---

## 🚀 How to Build & Run

### Prerequisites
- **Android Studio**: Android Studio Ladybug (2024.2+) or higher.
- **JDK**: Java 17 or Java 21.
- **Android SDK**: `compileSdk = 36`, `minSdk = 24` (Android 7.0+).

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Mayankpatel-10/errno-.git
   cd errno-
   ```

2. **Open in Android Studio**:
   - Open Android Studio and choose **File ➔ Open**, then select the project root directory.

3. **Build the Debug APK**:
   ```bash
   ./gradlew assembleDebug
   ```

4. **Run the App**:
   - Select your connected Android device or emulator in Android Studio and click **Run 'app'** ▶️ (`Shift + F10`).

---

## 🌐 Connecting with the FastAPI Backend

The Android app communicates with the Python FastAPI backend located in the `Backend/` directory:

- **Local Emulator Base URL**: `http://10.0.2.2:8000`
- **Real Device Base URL**: `http://<your-local-ip>:8000`

To start the backend locally:
```bash
cd Backend
python main.py
```

---

## 📄 License & Copyright

© 2024 **Errno Smart Solutions**. All Rights Reserved.
