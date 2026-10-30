import Foundation
import Observation

/// A process-local sandbox. No network, database, credentials or disk persistence.
/// Session identity clears on logout; marketplace records survive role changes until app exit.
@Observable
@MainActor
final class LocalMarketplaceStore {
    private(set) var currentUser: User?
    private(set) var selectedRole: UserRole = .shopkeeper
    private(set) var shopkeeper = User(phone: "", role: .shopkeeper, name: "Shopkeeper", shopName: "Rahul General Store")
    private(set) var worker = User(phone: "", role: .worker, name: "Worker", rating: 0, totalJobsCompleted: 0)
    private(set) var jobs: [Job] = []
    private(set) var applications: [Application] = []
    private(set) var earnings: [Earning] = []
    private(set) var workers: [User] = []
    private(set) var maskedAadhaar = ""
    private(set) var withdrawnAmount: Double = 0
    var shopAddress = "Okhla Market Area, Block B, New Delhi"
    var currentLocation = "Okhla Market Area"
    var payoutUPI = "amanworker@upi"

    var ownerJobs: [Job] { jobs.filter { $0.shopOwnerId == shopkeeper.id } }
    var availableJobs: [Job] { jobs.filter { $0.status == .open } }
    var workerJobs: [Job] { jobs.filter { $0.assignedWorkerId == worker.id } }
    var activeCount: Int { ownerJobs.filter { $0.status == .open || $0.status == .assigned || $0.status == .inProgress }.count }
    var totalEarned: Double { earnings.filter { $0.workerId == worker.id }.reduce(0) { $0 + $1.amount } }
    var balance: Double { max(0, totalEarned - withdrawnAmount) }
    var isVerified: Bool { !maskedAadhaar.isEmpty }

    func signIn(phone: String, role: UserRole, name: String = "") {
        selectedRole = role
        if role == .shopkeeper {
            shopkeeper.phone = phone
            if !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { shopkeeper.name = name }
            currentUser = shopkeeper
        } else {
            worker.phone = phone
            if !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { worker.name = name }
            currentUser = worker
        }
    }

    /// Replace prototype identity with the server profile ID returned after verified Firebase login.
    func signIn(profile: FirebaseUserProfile) {
        guard let backendID = UUID(uuidString: profile.id) else { return }
        if profile.role == "worker" {
            worker = User(id: backendID, phone: profile.phone_number ?? "", role: .worker,
                          name: profile.name ?? "Worker", rating: worker.rating, totalJobsCompleted: worker.totalJobsCompleted)
            currentUser = worker; selectedRole = .worker
        } else if profile.role == "shop_owner" || profile.role == "shopkeeper" {
            shopkeeper = User(id: backendID, phone: profile.phone_number ?? "", role: .shopkeeper,
                              name: profile.name ?? "Shopkeeper", shopName: shopkeeper.shopName)
            currentUser = shopkeeper; selectedRole = .shopkeeper
        }
    }

    func updateRemoteShop(name: String, address: String, category: String?) {
        shopkeeper.shopName = name
        shopAddress = address
        currentUser = shopkeeper
    }

    func installBackendJobs(_ remote: [BackendJob], ownerID: UUID? = nil) {
        let owner = ownerID ?? shopkeeper.id
        let mapped = remote.compactMap { row -> Job? in
            guard let id = UUID(uuidString: row.id) else { return nil }
            let status: JobStatus = switch row.status {
            case "completed": .completed
            case "cancelled": .cancelled
            case "assigned": .assigned
            case "in_progress", "inProgress": .inProgress
            default: .open
            }
            var job = Job(id: id, shopOwnerId: owner, category: JobCategory(rawValue: row.category ?? "") ?? .other,
                          title: row.title, description: row.description ?? "", payType: .fixed,
                          payAmount: row.pay_amount, estimatedDurationHours: Double(row.duration_type.filter(\.isNumber)) ?? 1,
                          latitude: 0, longitude: 0, status: status)
            job.location = row.location ?? ""
            job.pickupLocation = row.pickup_location ?? ""
            job.dropLocation = row.drop_location ?? ""
            job.assignedWorkerId = row.assigned_worker_id.flatMap(UUID.init(uuidString:))
            return job
        }
        let ids = Set(mapped.map(\.id))
        jobs.removeAll { $0.shopOwnerId == owner && !ids.contains($0.id) }
        for job in mapped {
            if let index = jobs.firstIndex(where: { $0.id == job.id }) { jobs[index] = job }
            else { jobs.insert(job, at: 0) }
        }
    }

    func updateLifecycle(_ row: BackendJob, ownerID: UUID? = nil) {
        installBackendJobs([row], ownerID: ownerID ?? shopkeeper.id)
    }

    func installBackendApplications(_ remote: [BackendOwnerApplication]) {
        var mapped: [Application] = []
        for row in remote {
            guard let id = UUID(uuidString: row.id), let jobID = UUID(uuidString: row.job_id),
                  let workerID = UUID(uuidString: row.worker_id),
                  let status = ApplicationStatus(rawValue: row.status) else { continue }
            mapped.append(Application(id: id, jobId: jobID, workerId: workerID, status: status))
            if !workers.contains(where: { $0.id == workerID }) {
                workers.append(User(id: workerID, phone: "", role: .worker, name: row.worker_name ?? "Worker"))
            }
        }
        applications = mapped
    }

    func updateApplicationStatus(id: UUID, status: ApplicationStatus) {
        guard let index = applications.firstIndex(where: { $0.id == id }) else { return }
        applications[index].status = status
    }

    func signOut() { currentUser = nil; selectedRole = .shopkeeper }
    func user(id: UUID) -> User? {
        if id == worker.id { return worker }
        if id == shopkeeper.id { return shopkeeper }
        return workers.first { $0.id == id }
    }
    func job(id: UUID) -> Job? { jobs.first { $0.id == id } }
    func updateProfile(role: UserRole, name: String, shopName: String = "") {
        guard currentUser?.role == role else { return }
        if role == .shopkeeper {
            shopkeeper.name = name; shopkeeper.shopName = shopName; currentUser = shopkeeper
        } else {
            worker.name = name; currentUser = worker
        }
    }

    @discardableResult
    func post(_ job: Job) throws -> Job {
        guard currentUser?.role == .shopkeeper, job.shopOwnerId == shopkeeper.id else { throw MarketplaceError.unauthorized }
        if let existing = self.job(id: job.id) { return existing }
        guard job.payAmount.isFinite, job.payAmount > 0, job.payAmount < Double(Int.max),
              let hours = job.estimatedDurationHours, hours.isFinite, hours > 0, hours < Double(Int.max) else { throw MarketplaceError.invalidPay }
        jobs.insert(job, at: 0)
        return job
    }

    func accept(jobId: UUID) throws {
        guard currentUser?.role == .worker else { throw MarketplaceError.unauthorized }
        guard let index = jobs.firstIndex(where: { $0.id == jobId }) else { throw MarketplaceError.missingJob }
        guard jobs[index].status == .open, jobs[index].assignedWorkerId == nil else { throw MarketplaceError.unavailable }
        jobs[index].status = .inProgress
        jobs[index].assignedWorkerId = worker.id
        applications.append(Application(jobId: jobId, workerId: worker.id, status: .accepted))
        rejectOtherApplications(jobId: jobId, workerId: worker.id)
    }

    func hire(applicationId: UUID, jobId: UUID) throws {
        guard currentUser?.role == .shopkeeper else { throw MarketplaceError.unauthorized }
        guard let j = jobs.firstIndex(where: { $0.id == jobId }), jobs[j].shopOwnerId == shopkeeper.id else { throw MarketplaceError.missingJob }
        guard jobs[j].status == .open else { throw MarketplaceError.unavailable }
        guard let a = applications.firstIndex(where: { $0.id == applicationId && $0.jobId == jobId }),
              applications[a].status == .pending else { throw MarketplaceError.invalidApplication }
        let workerId = applications[a].workerId
        applications[a].status = .accepted
        jobs[j].assignedWorkerId = workerId
        jobs[j].status = .inProgress
        rejectOtherApplications(jobId: jobId, workerId: workerId)
    }

    private func rejectOtherApplications(jobId: UUID, workerId: UUID) {
        for i in applications.indices where applications[i].jobId == jobId && applications[i].workerId != workerId {
            applications[i].status = .rejected
        }
    }

    func decline(applicationId: UUID) {
        guard currentUser?.role == .shopkeeper,
              let i = applications.firstIndex(where: { $0.id == applicationId && $0.status == .pending }),
              job(id: applications[i].jobId)?.shopOwnerId == shopkeeper.id else { return }
        applications[i].status = .rejected
    }

    /// Explicit demo control in owner job details; no payment is implied.
    func complete(jobId: UUID) throws {
        guard currentUser?.role == .shopkeeper else { throw MarketplaceError.unauthorized }
        guard let i = jobs.firstIndex(where: { $0.id == jobId }), jobs[i].shopOwnerId == shopkeeper.id else { throw MarketplaceError.missingJob }
        if jobs[i].status == .completed { return }
        guard jobs[i].status == .inProgress, let workerId = jobs[i].assignedWorkerId else { throw MarketplaceError.unavailable }
        jobs[i].status = .completed
        for a in applications.indices where applications[a].jobId == jobId && applications[a].status == .accepted {
            applications[a].status = .completed
        }
        if !earnings.contains(where: { $0.jobId == jobId }) {
            earnings.insert(Earning(jobId: jobId, workerId: workerId, title: jobs[i].title,
                                    hours: Int(jobs[i].estimatedDurationHours ?? 2),
                                    amount: jobs[i].payAmount, date: Date()), at: 0)
        }
    }

    func rate(jobId: UUID, role: UserRole, stars: Int, comment: String) {
        guard currentUser?.role == role, (1...5).contains(stars),
              let i = jobs.firstIndex(where: { $0.id == jobId && $0.status == .completed }) else { return }
        if role == .shopkeeper, jobs[i].shopOwnerId == shopkeeper.id {
            jobs[i].workerRating = stars; jobs[i].workerReview = comment
        } else if role == .worker, jobs[i].assignedWorkerId == worker.id {
            jobs[i].shopkeeperRating = stars; jobs[i].shopkeeperReview = comment
        }
    }

    func verify(lastFour: String) {
        guard currentUser?.role == .worker, lastFour.count == 4, lastFour.allSatisfy(\.isNumber) else { return }
        maskedAadhaar = "XXXX-XXXX-\(lastFour)"
    }
    @discardableResult
    func withdraw(upi: String) throws -> Double {
        guard currentUser?.role == .worker else { throw MarketplaceError.unauthorized }
        guard !upi.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, balance > 0 else { throw MarketplaceError.invalidPay }
        let amount = balance
        withdrawnAmount += amount
        payoutUPI = upi
        return amount
    }

    /// Opt-in fixtures for an existing job, never an automatic applicant acquisition system.
    func addDemoApplicants(jobId: UUID) {
        guard currentUser?.role == .shopkeeper, let job = job(id: jobId),
              job.shopOwnerId == shopkeeper.id, job.status == .open,
              !applications.contains(where: { $0.jobId == jobId }) else { return }
        for person in MockData.applicants() {
            workers.append(person)
            applications.append(Application(jobId: jobId, workerId: person.id))
        }
    }
}
