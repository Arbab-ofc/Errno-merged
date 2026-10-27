// LoginView.swift
// Errno — Views/Auth
//
// Matches Android "Login as Shop Owner" and "Login as Worker" screens.

import SwiftUI

struct LoginView: View {
    @Environment(AppRouter.self) private var router
    @Environment(\.dismiss) private var dismiss

    let role: UserRole
    @State private var viewModel = AuthViewModel()
    @FocusState private var isPhoneFocused: Bool

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: Spacing.lg) {
                // Top Illustration Banner
                ZStack {
                    RoundedRectangle(cornerRadius: 16)
                        .fill(Color(hex: "#F2F9E8"))
                        .frame(height: 120)

                    if role == .shopkeeper {
                        Image(systemName: "storefront")
                            .font(.system(size: 54))
                            .foregroundStyle(Color(hex: "#99E329"))
                    } else {
                        Image(systemName: "person.badge.shield.checkmark")
                            .font(.system(size: 54))
                            .foregroundStyle(Color(hex: "#99E329"))
                    }
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.top, Spacing.xs)

                // Elevated Floating Card
                VStack(spacing: Spacing.md) {
                    // Top Icon Circle Badge
                    ZStack {
                        Circle()
                            .fill(Color(hex: "#EBF8DC"))
                            .frame(width: 48, height: 48)

                        Image(systemName: role == .shopkeeper ? "storefront" : "person.badge.shield.checkmark")
                            .font(.system(size: 22))
                            .foregroundStyle(Color(hex: "#84CC16"))
                    }
                    .padding(.top, 4)

                    // Card Title & Subtitle
                    VStack(spacing: 6) {
                        Text("Enter Mobile Number")
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)

                        Text("We will send you an OTP to verify\nyour mobile number.")
                            .font(.system(size: 13, weight: .regular))
                            .foregroundStyle(Color.errnoTextSecondary)
                            .multilineTextAlignment(.center)
                            .lineSpacing(2)
                    }

                    // Mobile Number Input Field (+91 ▾ | Mobile number)
                    HStack(spacing: 10) {
                        HStack(spacing: 4) {
                            Text("+91")
                                .font(.system(size: 15, weight: .semibold))
                                .foregroundStyle(Color.errnoTextPrimary)

                            Image(systemName: "arrowtriangle.down.fill")
                                .font(.system(size: 8))
                                .foregroundStyle(Color.errnoTextSecondary)
                        }
                        .padding(.leading, 14)

                        Rectangle()
                            .fill(Color.errnoStroke)
                            .frame(width: 1, height: 24)

                        TextField("Mobile number", text: $viewModel.phoneNumber)
                            .font(.system(size: 15, weight: .medium))
                            .keyboardType(.numberPad)
                            .focused($isPhoneFocused)
                            .onChange(of: viewModel.phoneNumber) { _, newValue in
                                let digitsOnly = newValue.filter { $0.isNumber }
                                if digitsOnly.count > 10 {
                                    viewModel.phoneNumber = String(digitsOnly.prefix(10))
                                } else if digitsOnly != newValue {
                                    viewModel.phoneNumber = digitsOnly
                                }
                            }
                    }
                    .frame(height: 52)
                    .background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(isPhoneFocused ? Color.errnoLime : Color.errnoStroke, lineWidth: 1)
                    )
                    .padding(.top, 4)

                    if let error = viewModel.errorMessage {
                        Text(error)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Color.errnoError)
                    }

                    // Send OTP Button
                    Button {
                        isPhoneFocused = false
                        viewModel.requestOTP(role: role) { phone, selectedRole in
                            router.navigateToOTP(phone: phone, role: selectedRole)
                        }
                    } label: {
                        Group {
                            if viewModel.isLoading {
                                ProgressView()
                                    .tint(viewModel.isValidPhone ? Color(hex: "#0B121F") : Color.errnoTextSecondary)
                            } else {
                                Text("Send OTP")
                                    .font(.system(size: 15, weight: .bold))
                                    .foregroundStyle(viewModel.isValidPhone ? Color(hex: "#0B121F") : Color.errnoTextSecondary)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(viewModel.isValidPhone ? Color.errnoLime : Color(hex: "#E5E7EB"))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .disabled(!viewModel.isValidPhone || viewModel.isLoading)
                    .padding(.top, 4)
                }
                .padding(20)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 20))
                .shadow(color: Color.black.opacity(0.06), radius: 12, x: 0, y: 5)
                .padding(.horizontal, Spacing.lg)

                // Secondary Links
                VStack(spacing: Spacing.md) {
                    // Create Account Link
                    Button {
                        router.navigateToRegister(role: role)
                    } label: {
                        HStack(spacing: 4) {
                            Text("New to ERRNO?")
                                .font(.system(size: 13, weight: .regular))
                                .foregroundStyle(Color.errnoTextPrimary)
                            Text("Create an account")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundStyle(Color.errnoLime)
                        }
                    }

                    // Worker-only: "OR" & Continue with Google
                    if role == .worker {
                        HStack(spacing: 12) {
                            Rectangle()
                                .fill(Color.errnoStroke)
                                .frame(height: 1)
                            Text("OR")
                                .font(.system(size: 11, weight: .medium))
                                .foregroundStyle(Color.errnoTextSecondary)
                            Rectangle()
                                .fill(Color.errnoStroke)
                                .frame(height: 1)
                        }
                        .padding(.horizontal, Spacing.lg)
                        .padding(.vertical, 2)

                        Button {
                            // Demo Google login for worker
                            router.navigateToHome(role: .worker)
                        } label: {
                            HStack(spacing: 8) {
                                Image(systemName: "person.circle.fill")
                                    .font(.system(size: 18))
                                    .foregroundStyle(Color.errnoTextPrimary)

                                Text("Continue with Google")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundStyle(Color.errnoTextPrimary)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(Color.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            .overlay(
                                RoundedRectangle(cornerRadius: 12)
                                    .stroke(Color.errnoStroke, lineWidth: 1)
                            )
                        }
                        .padding(.horizontal, Spacing.lg)
                    }

                    // Trust Guarantee
                    HStack(spacing: 6) {
                        Image(systemName: "shield.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(Color.errnoTextSecondary)
                        Text("Your number is safe with us")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Color.errnoTextSecondary)
                    }
                    .padding(.top, Spacing.md)
                }
                .padding(.bottom, Spacing.xl)
            }
        }
        .background(Color(hex: "#FAFAFA").ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 18, weight: .medium))
                        .foregroundStyle(Color.errnoTextPrimary)
                        .padding(8)
                }
            }
            ToolbarItem(placement: .principal) {
                Text(role == .shopkeeper ? "Login as Shop Owner" : "Login as Worker")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Color.errnoTextPrimary)
            }
        }
    }
}
