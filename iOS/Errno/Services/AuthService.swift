// AuthService.swift
// Errno — Services
//
// Protocol-backed mock auth service.

import Foundation

// MARK: — Protocol

protocol AuthServiceProtocol: Sendable {
    func sendOTP(to phone: String, role: UserRole) async throws -> WhatsAppOTPChallenge
    func resendOTP(to phone: String, role: UserRole, requestID: String) async throws -> WhatsAppOTPChallenge
    func verifyOTP(_ otp: String, phone: String, role: UserRole, requestID: String, fullName: String?) async throws -> FirebaseUserProfile
}

// MARK: — Errors

enum AuthError: LocalizedError {
    case networkFailure
    case invalidOTP
    case rateLimited

    var errorDescription: String? {
        switch self {
        case .networkFailure: "Network error. Please check your connection."
        case .invalidOTP:     "The OTP you entered is incorrect."
        case .rateLimited:    "Too many attempts. Please wait and try again."
        }
    }
}

// MARK: — Mock Implementation

/// Demo mode does not authenticate with a static or synthetic OTP.
struct MockAuthService: AuthServiceProtocol {
    nonisolated init() {}

    func sendOTP(to phone: String, role: UserRole) async throws -> WhatsAppOTPChallenge {
        // Simulate 1.5 s network round-trip
        try await Task.sleep(for: .milliseconds(1500))
        throw APIError.unsupportedFeature
    }

    func resendOTP(to phone: String, role: UserRole, requestID: String) async throws -> WhatsAppOTPChallenge {
        throw APIError.unsupportedFeature
    }

    func verifyOTP(_ otp: String, phone: String, role: UserRole, requestID: String, fullName: String?) async throws -> FirebaseUserProfile {
        throw APIError.unsupportedFeature
    }
}
