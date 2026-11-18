"""Source contract checks that normal mobile authentication never opens KYC UI."""
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


def test_android_worker_login_and_dashboard_have_no_kyc_redirect_or_prompt():
    nav = (REPO / "Android/app/src/main/java/com/erno/app/navigation/NavGraph.kt").read_text()
    home = (REPO / "Android/app/src/main/java/com/erno/app/ui/screens/worker/WorkerHomeScreen.kt").read_text()
    assert "triggerDigiLockerPopup(true)" not in nav
    assert "showDigiLockerPopup" not in home
    assert "DigiLocker Aadhaar Verification" not in home


def test_ios_worker_login_routes_directly_to_home_without_kyc_navigation():
    otp = (REPO / "iOS/Errno/Views/Auth/VerifyOTPView.swift").read_text()
    router = (REPO / "iOS/Errno/Navigation/AppRouter.swift").read_text()
    assert "DigiLockerVerificationView" not in otp
    assert "WorkerRoute.verification" not in otp
    assert "case .worker:     appState = .workerHome" in router
