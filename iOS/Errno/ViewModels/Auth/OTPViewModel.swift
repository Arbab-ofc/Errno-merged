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
    var expiryRemaining: Int = 300
    var canResend: Bool = false

    private let authService: AuthServiceProtocol
    private let phone: String
    private let role: UserRole
    private var requestID: String
    private var initialResendAfter: Int
    private var timerCancellable: AnyCancellable?
    @ObservationIgnored private var verificationTask: Task<Void, Never>?
    @ObservationIgnored private var resendTask: Task<Void, Never>?

    func cancel() {
        verificationTask?.cancel()
        resendTask?.cancel()
        timerCancellable?.cancel()
        isLoading = false
    }

    init(phone: String, role: UserRole, requestID: String, expiresIn: Int, resendAfter: Int, authService: AuthServiceProtocol = AppDependencies.authService()) {
        self.phone = phone
        self.role = role
        self.requestID = requestID
        self.expiryRemaining = expiresIn
        self.initialResendAfter = resendAfter
        self.authService = authService
        startTimer()
    }

    var isOTPComplete: Bool {
        otp.count == 6 && otp.allSatisfy(\.isNumber)
    }

    func startTimer() {
        timeRemaining = initialResendAfter
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
                }
                if self.expiryRemaining > 0 { self.expiryRemaining -= 1 }
                if self.expiryRemaining == 0 {
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
            do {
                let challenge = try await authService.resendOTP(to: phone, role: role, requestID: requestID)
                requestID = challenge.requestId
                expiryRemaining = challenge.expiresInSeconds
                initialResendAfter = challenge.resendAfterSeconds
                timeRemaining = challenge.resendAfterSeconds
                canResend = false
                startTimer()
            }
            catch { errorMessage = error.localizedDescription }
        }
    }

    func verifyOTP(role: UserRole, fullName: String?, onSuccess: @escaping (FirebaseUserProfile) -> Void) {
        guard isOTPComplete, !isLoading, !isSuccess else { return }

        isLoading = true
        isError = false
        errorMessage = nil

        verificationTask = Task {
            do {
                let profile = try await authService.verifyOTP(otp, phone: phone, role: role, requestID: requestID, fullName: fullName)
                try Task.checkCancellation()
                isSuccess = true
                try await Task.sleep(for: .milliseconds(350))
                try Task.checkCancellation()
                isLoading = false
                onSuccess(profile)
                return
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
