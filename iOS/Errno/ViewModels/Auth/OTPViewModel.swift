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
    @ObservationIgnored private var verificationTask: Task<Void, Never>?
    @ObservationIgnored private var resendTask: Task<Void, Never>?

    func cancel() {
        verificationTask?.cancel()
        resendTask?.cancel()
        timerCancellable?.cancel()
        isLoading = false
    }

    init(phone: String, authService: AuthServiceProtocol = AppDependencies.authService()) {
        self.phone = phone
        self.authService = authService
        startTimer()
    }

    var isOTPComplete: Bool {
        otp.count == 6 && otp.allSatisfy(\.isNumber)
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
                }
                if self.timeRemaining == 0 {
                    self.canResend = true
                    self.timerCancellable?.cancel()
                }
            }
    }

    func resendOTP() {
        guard canResend, !isLoading else { return }
        startTimer()
        otp = ""
        isError = false
        errorMessage = nil
        resendTask = Task {
            do { try await authService.sendOTP(to: phone) }
            catch { errorMessage = error.localizedDescription }
        }
    }

    func verifyOTP(role: UserRole, onSuccess: @escaping (UserRole) -> Void) {
        guard isOTPComplete, !isLoading, !isSuccess else { return }

        isLoading = true
        isError = false
        errorMessage = nil

        verificationTask = Task {
            do {
                let success = try await authService.verifyOTP(otp, phone: phone)
                try Task.checkCancellation()
                if success {
                    isSuccess = true
                    try await Task.sleep(for: .milliseconds(500))
                    try Task.checkCancellation()
                    isLoading = false
                    onSuccess(role)
                    return
                }
                await MainActor.run {
                    self.isLoading = false
                    self.isError = true
                    self.errorMessage = "Incorrect code. Please try again."
                    self.otp = ""
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
