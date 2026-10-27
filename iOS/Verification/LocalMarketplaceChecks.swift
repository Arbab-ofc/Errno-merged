// Standalone local-domain checks. Excluded from the app's synchronized Errno source group.
import Foundation

@main
struct LocalMarketplaceChecks {
    @MainActor static func main() async throws {
        let store = LocalMarketplaceStore()
        func require(_ condition: Bool, _ message: String) { precondition(condition, message) }
        func rejects(_ message: String, _ action: () throws -> Void) {
            do { try action(); preconditionFailure(message) } catch { }
        }
        func draft(_ title: String) -> Job {
            Job(shopOwnerId: store.shopkeeper.id, category: .delivery, title: title,
                description: "Local test", payType: .fixed, payAmount: 249,
                estimatedDurationHours: 2, latitude: 28.5355, longitude: 77.2641)
        }
        require(store.jobs.isEmpty && store.currentUser == nil, "Clean local start")
        store.signIn(phone: "9876543210", role: .shopkeeper, name: "Owner")
        let first = draft("First"), second = draft("Second"), third = draft("Third")
        try store.post(first); try store.post(first); try store.post(second); try store.post(third)
        require(store.jobs.count == 3 && store.ownerJobs.count == 3, "Idempotent posting")
        require(store.availableJobs.count == 3 && store.activeCount == 3, "Discovery shares owner records")
        var invalid = draft("Invalid"); invalid.payAmount = 0
        rejects("Zero pay accepted") { try store.post(invalid) }
        invalid.payAmount = .infinity
        rejects("Infinite pay accepted") { try store.post(invalid) }
        store.updateProfile(role: .shopkeeper, name: "Updated", shopName: "Shop")
        require(store.currentUser?.name == "Updated" && store.shopkeeper.shopName == "Shop", "Profile propagation")
        store.signOut()
        require(store.currentUser == nil && store.jobs.count == 3, "Logout clears session and preserves sandbox records")
        rejects("Signed-out mutation allowed") { try store.accept(jobId: first.id) }
        store.signIn(phone: "9876543211", role: .worker, name: "Worker")
        try store.accept(jobId: first.id)
        require(store.job(id: first.id)?.status == .inProgress && store.workerJobs.count == 1, "Acceptance")
        require(store.job(id: second.id)?.status == .open && store.job(id: third.id)?.status == .open, "No unrelated acceptance")
        rejects("Duplicate acceptance allowed") { try store.accept(jobId: first.id) }
        rejects("Missing ID accepted") { try store.accept(jobId: UUID()) }
        require(store.applications.count == 1, "No duplicate applications")
        store.verify(lastFour: "1234")
        require(store.maskedAadhaar == "XXXX-XXXX-1234", "Only masked identity retained")
        store.signIn(phone: "9876543210", role: .shopkeeper)
        store.addDemoApplicants(jobId: second.id); store.addDemoApplicants(jobId: second.id)
        store.addDemoApplicants(jobId: third.id)
        let secondApps = store.applications.filter { $0.jobId == second.id }
        require(secondApps.count == 2, "Fixtures are opt-in and idempotent")
        guard let accepted = secondApps.first, let declined = store.applications.first(where: { $0.jobId == third.id }) else { preconditionFailure("Missing fixture") }
        store.decline(applicationId: declined.id)
        require(store.applications.first { $0.id == declined.id }?.status == .rejected, "Decline exact ID")
        try store.hire(applicationId: accepted.id, jobId: second.id)
        require(store.job(id: second.id)?.assignedWorkerId == accepted.workerId, "Correct applicant hired")
        require(store.applications.filter { $0.jobId == second.id && $0.status == .accepted }.count == 1, "One accepted application")
        require(store.applications.filter { $0.jobId == second.id && $0.status == .rejected }.count == 1, "Competing application rejected")
        require(store.job(id: third.id)?.status == .open, "Hiring does not affect unrelated job")
        rejects("Accepted application hired again") { try store.hire(applicationId: accepted.id, jobId: second.id) }
        try store.complete(jobId: first.id); try store.complete(jobId: first.id)
        require(store.earnings.count == 1 && store.totalEarned == 249, "Exactly one earning per completed job")
        require(store.job(id: second.id)?.status == .inProgress, "Completion exact ID")
        store.rate(jobId: first.id, role: .shopkeeper, stars: 4, comment: "Good")
        require(store.job(id: first.id)?.workerRating == 4, "Owner rating")
        store.signIn(phone: "9876543211", role: .worker)
        store.rate(jobId: first.id, role: .worker, stars: 5, comment: "Good")
        require(store.job(id: first.id)?.shopkeeperRating == 5, "Worker rating")
        rejects("Blank withdrawal accepted") { _ = try store.withdraw(upi: " ") }
        let amount = try store.withdraw(upi: "demo@upi")
        require(amount == 249 && store.balance == 0 && store.totalEarned == 249, "Withdrawal balance versus lifetime earnings")
        rejects("Duplicate withdrawal accepted") { _ = try store.withdraw(upi: "demo@upi") }
        let auth = MockAuthService()
        let correct = try await auth.verifyOTP("123456", phone: "9876543210")
        let incorrect = try await auth.verifyOTP("654321", phone: "9876543210")
        require(correct && !incorrect, "Deterministic OTP")
        let phone = AuthViewModel(); phone.phoneNumber = "abcdefghij"
        require(!phone.isValidPhone, "Nonnumeric phone blocked")
        phone.phoneNumber = "9876543210"; require(phone.isValidPhone, "Valid phone accepted")
        let otp = OTPViewModel(phone: "9876543210")
        otp.otp = "654321"
        otp.verifyOTP(role: .worker) { _ in preconditionFailure("Incorrect OTP navigated") }
        try await Task.sleep(for: .milliseconds(1200))
        require(otp.isError && otp.otp.isEmpty && !otp.isSuccess, "OTP ViewModel error state")
        otp.otp = "123456"
        var verifiedRole: UserRole?
        otp.verifyOTP(role: .worker) { verifiedRole = $0 }
        try await Task.sleep(for: .milliseconds(1700))
        require(otp.isSuccess && verifiedRole == .worker, "OTP ViewModel role navigation")
        otp.cancel()
        let cancelledOTP = OTPViewModel(phone: "9876543210")
        cancelledOTP.otp = "123456"
        cancelledOTP.verifyOTP(role: .worker) { _ in preconditionFailure("Cancelled verification navigated") }
        cancelledOTP.cancel()
        try await Task.sleep(for: .milliseconds(1200))
        require(!cancelledOTP.isSuccess, "Leaving OTP cancels pending navigation")
        store.signIn(phone: "9876543210", role: .shopkeeper)
        let vm = PostJobViewModel(jobService: MockJobService(store: store), currentUser: store.shopkeeper)
        var callbacks = 0
        vm.submitJob { callbacks += 1 }; vm.submitJob { callbacks += 1 }
        try await Task.sleep(for: .milliseconds(1200))
        require(vm.postedJob != nil && callbacks == 1 && store.jobs.count == 4, "Submission debounce and success after creation")
        vm.submitJob { callbacks += 1 }
        require(store.jobs.count == 4, "Retry completed draft cannot duplicate job")
        require(vm.postedJob?.payType == .fixed && vm.postedJob?.payAmount == 249, "Shift total pay")
        let badVM = PostJobViewModel(jobService: MockJobService(store: store), currentUser: store.shopkeeper)
        badVM.payAmountString = ""
        badVM.submitJob { preconditionFailure("Invalid draft succeeded") }
        require(badVM.errorMessage != nil && !badVM.isSubmitting, "Invalid submission error")
        let projection = ShopkeeperDashboardViewModel(store: store)
        require(projection.jobs.count == store.jobs.count, "Dashboard projection shares store")
        let router = AppRouter()
        router.requestConsent(role: .worker)
        require(router.authPath.last == .consent(role: .worker, registration: false), "Consent destination")
        router.finishConsent(role: .worker, registration: false)
        require(router.authPath == [.login(role: .worker)], "Consent replaces gate with role login")
        router.navigateToOTP(phone: "9876543210", role: .worker)
        require(router.authPath.last == .verifyOTP(phone: "9876543210", role: .worker), "OTP route identity")
        router.marketplace.signIn(phone: "9876543210", role: .worker)
        router.navigateToHome(role: .worker)
        require(router.appState == .workerHome && router.authPath.isEmpty, "Worker home clears auth path")
        router.postingPresented = true
        router.workerTab = 3
        router.signOut()
        require(router.appState == .auth && router.marketplace.currentUser == nil &&
                router.workerTab == 0 && !router.postingPresented, "Logout resets router and session")
        print("PASS: local store, exact-ID mutations, duplicate guards, earnings, withdrawal, profiles, verification, auth, and submission checks")
    }
}
