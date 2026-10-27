// OTPViewModel.swift
// Errno — ViewModels/Auth
//
// Manages OTP verification and 30s countdown timer.

import SwiftUI
import Observation
import Combine

@Observable
@MainActor
final class OTPViewModel {
    var otp: String = ""
    var isLoading: Bool = false
    var isError: Bool = false
    var isSuccess: Bool = false
    var errorMessage: String? = nil

    var timeRemaining: Int = 30
    var canResend: Bool = false

    private let authService: AuthServiceProtocol
    private let phone: String
    private var timerCancellable: AnyCancellable?

    init(phone: String, authService: AuthServiceProtocol = MockAuthService()) {
        self.phone = phone
        self.authService = authService
        startTimer()
    }

    var isOTPComplete: Bool {
        otp.count == 6
    }

    func startTimer() {
        timeRemaining = 30
        canResend = false
        timerCancellable?.cancel()
        
        timerCancellable = Timer.publish(every: 1, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                guard let self = self else { return }
                if self.timeRemaining > 0 {
                    self.timeRemaining -= 1
                } else {
                    self.canResend = true
                    self.timerCancellable?.cancel()
                }
            }
    }

    func resendOTP() {
        guard canResend else { return }
        
        // Mock resend logic
        startTimer()
        otp = ""
        isError = false
        errorMessage = nil
    }

    func verifyOTP(role: UserRole, onSuccess: @escaping (UserRole) -> Void) {
        guard isOTPComplete else { return }

        isLoading = true
        isError = false
        errorMessage = nil

        Task {
            do {
                let success = try await authService.verifyOTP(otp, phone: phone)
                await MainActor.run {
                    self.isLoading = false
                    if success {
                        self.isSuccess = true
                        // Brief delay for success animation
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                            onSuccess(role)
                        }
                    } else {
                        self.isError = true
                        self.errorMessage = "Incorrect code. Please try again."
                        self.otp = ""
                    }
                }
            } catch {
                await MainActor.run {
                    self.isLoading = false
                    self.isError = true
                    self.errorMessage = error.localizedDescription
                }
            }
        }
    }
}
