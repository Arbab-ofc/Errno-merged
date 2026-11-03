import SwiftUI
import UniformTypeIdentifiers
import UIKit

struct DigiLockerVerificationView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var status: KYCStatusResponse?
    @State private var documentType = ""
    @State private var consent = false
    @State private var busy = false
    @State private var error: String?
    @State private var notice: String?
    @State private var choosingDocument = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                Text("Identity verification").font(.system(size: 24, weight: .bold))
                Text("Status: \(status?.status ?? "Loading")").font(.headline)
                Text("Method: \(status?.verificationMethod ?? "Not verified")")
                Text("ERRNO uses identity details for onboarding and eligibility review. Authorized reviewers can access verification results. Retention follows the configured policy. DigiLocker sign-in takes place outside ERRNO. Never share your DigiLocker password, PIN, or OTP with ERRNO.")
                    .font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary)
                if let status, !status.availableDocumentTypes.isEmpty {
                    Picker("Document category", selection: $documentType) {
                        ForEach(status.availableDocumentTypes, id: \.self) { Text($0).tag($0) }
                    }.pickerStyle(.menu)
                } else { Text("No document categories are currently configured.").font(.footnote) }
                Toggle("I consent to use the selected category for ERRNO identity verification.", isOn: $consent)
                Button {
                    Task {
                        await perform {
                            guard let repo = try? AppDependencies.backendRepository() else { throw APIError.configuration }
                            let result = try await repo.startKYC(documentTypes: [documentType], version: status?.consentVersion ?? "v1")
                            if let raw = result.authorizationUrl, result.providerReady, let url = URL(string: raw), url.scheme == "https" { await UIApplication.shared.open(url) }
                            else { notice = "DigiLocker is not configured. No identity verification was started." }
                        }
                    }
                } label: { Label("Continue with DigiLocker", systemImage: "arrow.up.forward.app") }
                    .buttonStyle(.borderedProminent).disabled(busy || !consent || documentType.isEmpty || status?.digilockerEnabled != true)
                if status?.manualReviewEnabled == true {
                    Text("Manual review is a separate ERRNO process and does not mean DigiLocker verified the document.").font(.footnote)
                    Button("Submit a document for manual review") { choosingDocument = true }
                        .buttonStyle(.bordered).disabled(busy || !consent || documentType.isEmpty)
                }
                Button("Refresh status") { Task { await refresh() } }.disabled(busy)
                Button("Withdraw consent", role: .destructive) {
                    Task { await perform { let repo = try AppDependencies.backendRepository(); status = try await repo.withdrawKYCConsent(); notice = "Consent withdrawn." } }
                }.disabled(busy)
                if busy { ProgressView() }
                if let error { Text(error).foregroundStyle(Color.errnoError) }
                if let notice { Text(notice).foregroundStyle(Color.errnoTextSecondary) }
            }.padding(22).frame(maxWidth: 640, alignment: .leading).frame(maxWidth: .infinity)
        }.marketplacePage().navigationTitle("Identity verification").navigationBarTitleDisplayMode(.inline)
            .task { await refresh() }
            .fileImporter(isPresented: $choosingDocument, allowedContentTypes: [.pdf, .jpeg, .png], allowsMultipleSelection: false) { result in
                Task {
                    await perform {
                        let picked = try result.get()
                        guard let url = picked.first else { throw APIError.invalidInput }
                        guard url.startAccessingSecurityScopedResource() else { throw APIError.invalidInput }
                        defer { url.stopAccessingSecurityScopedResource() }
                        let data = try Data(contentsOf: url)
                        let mime = url.pathExtension.lowercased() == "pdf" ? "application/pdf" : (url.pathExtension.lowercased() == "png" ? "image/png" : "image/jpeg")
                        let repo = try AppDependencies.backendRepository()
                        let response = try await repo.uploadKYC(documentType: documentType, version: status?.consentVersion ?? "v1", bytes: data, mime: mime)
                        notice = "Submitted for manual review (\(response.status)). This is not official DigiLocker verification."
                        await refresh()
                    }
                }
            }
    }

    @MainActor private func refresh() async {
        do { let repo = try AppDependencies.backendRepository(); status = try await repo.kycStatus(); if documentType.isEmpty { documentType = status?.availableDocumentTypes.first ?? "" } }
        catch { self.error = error.localizedDescription }
    }
    @MainActor private func perform(_ action: @escaping () async throws -> Void) async {
        busy = true; error = nil
        defer { busy = false }
        do { try await action() } catch { self.error = error.localizedDescription }
    }
}
