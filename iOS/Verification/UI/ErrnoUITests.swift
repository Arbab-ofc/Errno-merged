import XCTest

final class ErrnoUITests: XCTestCase {
    let app = XCUIApplication(bundleIdentifier: "Errno.Errno")
    override func setUpWithError() throws { continueAfterFailure = false }
    func snap(_ name: String) {
        let shot = XCTAttachment(screenshot: app.screenshot()); shot.name = name; shot.lifetime = .keepAlways; add(shot)
        print("SCREEN VERIFIED: \(name)")
    }
    func tap(_ label: String, timeout: TimeInterval = 12) {
        let button = app.buttons[label].firstMatch
        XCTAssertTrue(button.waitForExistence(timeout: timeout), "Missing button \(label)\n\(app.debugDescription)")
        for _ in 0..<5 { if button.isHittable { break }; app.swipeUp() }
        button.tap()
    }
    func text(_ label: String, timeout: TimeInterval = 12) {
        XCTAssertTrue(app.staticTexts[label].firstMatch.waitForExistence(timeout: timeout), "Missing text \(label)\n\(app.debugDescription)")
    }
    func login(worker: Bool) {
        if worker {
            let role = app.buttons.containing(.staticText, identifier: "Worker").firstMatch
            XCTAssertTrue(role.waitForExistence(timeout: 10)); role.tap()
        }
        tap("Continue")
        let agree = app.buttons["Agree & Continue"]
        XCTAssertTrue(agree.waitForExistence(timeout: 10)); XCTAssertFalse(agree.isEnabled)
        snap(worker ? "worker-consent" : "owner-consent")
        tap("I agree to Terms of Service and Privacy Policy")
        XCTAssertTrue(agree.isEnabled); agree.tap()
        text(worker ? "Login as Worker" : "Login as Shop Owner")
        snap(worker ? "worker-login" : "owner-login")
        let phone = app.textFields["Mobile number"]
        XCTAssertTrue(phone.waitForExistence(timeout: 10)); phone.tap(); phone.typeText("9876543210")
        tap("Send OTP")
        text("Enter OTP")
        snap(worker ? "worker-otp" : "owner-otp")
        let otp = app.textFields["Six digit verification code"]
        XCTAssertTrue(otp.waitForExistence(timeout: 10))
        if !worker {
            otp.typeText("000000")
            tap("Verify OTP")
            text("Incorrect code. Please try again.")
            XCTAssertFalse(app.buttons["Verify OTP"].isEnabled)
            snap("invalid-demo-otp")
            otp.tap()
        }
        otp.typeText("123456")
        tap("Verify OTP")
    }
    func logout() {
        tap("Profile")
        let logout = app.buttons["Logout Account"]
        for _ in 0..<4 { if logout.isHittable { break }; app.swipeUp() }
        tap("Logout Account"); tap("Yes, Logout")
        text("Welcome to")
    }
    func testMarketplaceJourney() {
        app.launch()
        text("Connecting Local Shops & Workers"); snap("splash")
        tap("Get Started")
        text("Welcome to"); snap("role-selection")
        tap("Terms of Service"); text("Terms & Conditions"); snap("terms"); tap("Done")
        tap("Privacy Policy"); text("Privacy Policy"); snap("privacy"); tap("Done")
        login(worker: false)
        text("Manage your jobs easily"); snap("owner-dashboard")
        tap("Post a New Job")
        text("Basic Information & Calendar Booking"); snap("post-details")
        tap("Next: Select Duration →")
        text("How much time do you need the worker for?"); snap("post-duration")
        tap("Next: Location →")
        text("Delivery Route Locations"); snap("post-location")
        tap("Preview & Post →")
        text("Fixed Time Options & Pay Structure"); snap("post-preview")
        tap("Post Job")
        text("Job Posted Successfully!"); snap("post-success")
        tap("Go to My Jobs")
        text("My Jobs & Assigned Workers"); text("Settlement Pay: ₹249"); snap("owner-my-jobs")
        tap("Applications"); text("No Applications Received Yet"); snap("owner-applications")
        tap("Profile"); text("Profile & Business Settings"); snap("owner-profile")
        logout()
        login(worker: true)
        text("Available Jobs & Deliveries"); snap("worker-home")
        let card = app.buttons.containing(.staticText, identifier: "Delivery Partner").firstMatch
        XCTAssertTrue(card.waitForExistence(timeout: 10)); card.tap()
        text("Choose Duration & Pay"); snap("worker-job-details")
        tap("Accept Job")
        text("Job Accepted!"); snap("worker-acceptance")
        tap("View Job Info")
        text("My Jobs"); snap("worker-my-jobs")
        tap("Earnings"); text("Available Balance"); snap("worker-earnings")
        tap("Profile"); text("Worker Profile Settings"); snap("worker-profile")
        tap("DigiLocker Aadhaar Verification")
        text("Enter 12-Digit Aadhaar Number"); snap("verification-input")
        let aadhaar = app.textFields["Aadhaar Number"]; aadhaar.tap(); aadhaar.typeText("123456789012")
        tap("Fetch from DigiLocker")
        text("Enter 6-Digit DigiLocker OTP"); snap("verification-otp")
        let code = app.textFields["6-Digit OTP"]; code.tap(); code.typeText("123456")
        tap("Verify Aadhaar & Complete")
        text("Aadhaar Card Verified ✓"); snap("verification-success")
        tap("Back to Worker Dashboard")
        logout()
        snap("logged-out")
    }

    func testRegistrationValidationAndSessionReset() {
        app.launch()
        tap("Get Started")
        tap("Create an account")
        let agree = app.buttons["Agree & Continue"]
        XCTAssertTrue(agree.waitForExistence(timeout: 10))
        XCTAssertFalse(agree.isEnabled)
        tap("I agree to Terms of Service and Privacy Policy")
        tap("Terms of Service")
        text("Terms & Conditions")
        tap("Done")
        XCTAssertTrue(agree.isEnabled, "Consent must survive opening legal documents")
        tap("Agree & Continue")
        text("Join ERRNO Community")
        XCTAssertFalse(app.buttons["Create Account"].isEnabled)
        let worker = app.buttons.containing(.staticText, identifier: "Worker").firstMatch
        XCTAssertTrue(worker.exists)
        worker.tap()
        let name = app.textFields["Full Name"]
        name.tap(); name.typeText("UI Test Worker")
        let phone = app.textFields["Mobile Number"]
        phone.tap(); phone.typeText("98765")
        XCTAssertFalse(app.buttons["Create Account"].isEnabled)
        phone.typeText("43210")
        XCTAssertTrue(app.buttons["Create Account"].isEnabled)
        snap("registration-validation")
        tap("Create Account")
        text("Enter OTP")
        let otp = app.textFields["Six digit verification code"]
        XCTAssertTrue(otp.waitForExistence(timeout: 10))
        otp.typeText("123456")
        tap("Verify OTP")
        text("Hello, UI Test Worker 👋")
        text("No Available Jobs Nearby")
        snap("registered-worker")
        app.terminate()
        app.launch()
        text("Connecting Local Shops & Workers")
        snap("session-reset-on-relaunch")
    }
}
