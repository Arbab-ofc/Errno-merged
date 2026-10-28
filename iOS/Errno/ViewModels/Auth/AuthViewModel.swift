// AuthViewModel.swift
// Errno — ViewModels/Auth
//
// Manages state for the phone number input screen.

import SwiftUI
import Observation

@Observable
@MainActor
final class AuthViewModel {
    var phoneNumber: String = ""
    var isLoading: Bool = false
    var errorMessage: String? = nil

    private let authService: AuthServiceProtocol
    @ObservationIgnored private var requestTask: Task<Void, Never>?

    func cancelRequest() { requestTask?.cancel(); isLoading = false }

    init(authService: AuthServiceProtocol = AppDependencies.authService()) {
        self.authService = authService
    }

    var isValidPhone: Bool {
        phoneNumber.count == 10 && phoneNumber.allSatisfy(\.isNumber)
    }

    func requestOTP(role: UserRole, onSuccess: @escaping (String, UserRole) -> Void) {
        guard !isLoading else { return }
        guard isValidPhone else {
            errorMessage = "Please enter a valid 10-digit number."
            return
        }

        errorMessage = nil
        isLoading = true

        requestTask = Task {
            do {
                try await authService.sendOTP(to: phoneNumber)
                try Task.checkCancellation()
                await MainActor.run {
                    self.isLoading = false
                    onSuccess(self.phoneNumber, role)
                }
            } catch {
                await MainActor.run {
                    self.isLoading = false
                    self.errorMessage = error.localizedDescription
                }
            }
        }
    }
}
