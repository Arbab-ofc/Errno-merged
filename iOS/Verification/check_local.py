"""Compile and execute the real local-domain code using macOS Command Line Tools.

This is not an iOS application build. All compiler output stays in a temporary directory.
Run from any directory: python3 -B iOS/Verification/check_local.py
"""
from pathlib import Path
import subprocess
import tempfile

ios = Path(__file__).resolve().parents[1]
sources = [
    "Theme/Color+Extensions.swift", "Theme/Theme.swift", "Theme/Typography.swift",
    "Models/UserRole.swift", "Models/User.swift", "Models/Job.swift",
    "Models/Application.swift", "Models/Earning.swift",
    "Services/MockData.swift", "Services/LocalMarketplaceStore.swift",
    "Services/JobService.swift", "Services/AuthService.swift",
    "ViewModels/Auth/AuthViewModel.swift", "ViewModels/Auth/OTPViewModel.swift",
    "ViewModels/Shopkeeper/PostJobViewModel.swift",
    "ViewModels/Shopkeeper/ShopkeeperDashboardViewModel.swift",
    "Navigation/AppRouter.swift",
]
with tempfile.TemporaryDirectory(prefix="errno-phase1-") as directory:
    executable = Path(directory) / "local-checks"
    command = [
        "swiftc", "-parse-as-library", "-swift-version", "5",
        "-default-isolation", "MainActor",
        "-module-cache-path", str(Path(tempfile.gettempdir()) / "errno-phase1-module-cache"),
        *[str(ios / "Errno" / source) for source in sources],
        str(ios / "Verification/LocalMarketplaceChecks.swift"),
        "-o", str(executable),
    ]
    subprocess.run(command, check=True)
    subprocess.run([str(executable)], check=True)
