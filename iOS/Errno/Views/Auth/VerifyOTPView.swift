// VerifyOTPView.swift
// Errno — Views/Auth
//
// Matches Android "Verify OTP" screen.

import SwiftUI

struct VerifyOTPView: View {
    @Environment(AppRouter.self) private var router
    @Environment(\.dismiss) private var dismiss

    let phone: String
    let role: UserRole

    @State private var viewModel: OTPViewModel
    @FocusState private var isOTPFieldFocused: Bool

    init(phone: String, role: UserRole) {
        self.phone = phone
        self.role = role
        _viewModel = State(initialValue: OTPViewModel(phone: phone))
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: Spacing.lg) {
                // Top Circular Phone + Lock Illustration
                ZStack {
                    Circle()
                        .fill(Color(hex: "#F0F9E8"))
                        .frame(width: 100, height: 100)

                    Image(systemName: "lock.iphone")
                        .font(.system(size: 44))
                        .foregroundStyle(Color(hex: "#99E329"))
                }
                .padding(.top, Spacing.sm)

                // Elevated Floating Card
                VStack(spacing: Spacing.md) {
                    // Title & Description
                    VStack(spacing: 6) {
                        Text("Enter OTP")
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)

                        Text("Enter the 6-digit OTP sent to")
                            .font(.system(size: 13, weight: .regular))
                            .foregroundStyle(Color.errnoTextSecondary)

                        HStack(spacing: 6) {
                            Text(phone.isEmpty ? "9876543210" : phone)
                                .font(.system(size: 15, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)

                            Button {
                                dismiss()
                            } label: {
                                Text("Edit")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundStyle(Color.errnoLime)
                            }
                        }
                    }

                    // 6-Digit OTP Boxes
                    ZStack {
                        // Hidden actual textfield for keyboard input
                        TextField("", text: $viewModel.otp)
                            .keyboardType(.numberPad)
                            .textContentType(.oneTimeCode)
                            .focused($isOTPFieldFocused)
                            .accentColor(.clear)
                            .foregroundColor(.clear)
                            .opacity(0.01)
                            .onChange(of: viewModel.otp) { _, newValue in
                                let digits = newValue.filter { $0.isNumber }
                                if digits.count > 6 {
                                    viewModel.otp = String(digits.prefix(6))
                                } else if digits != newValue {
                                    viewModel.otp = digits
                                }
                            }

                        // Visible 6 boxes
                        HStack(spacing: 8) {
                            ForEach(0..<6, id: \.self) { index in
                                let char = characterAt(index)
                                let isCurrentBox = viewModel.otp.count == index

                                ZStack {
                                    RoundedRectangle(cornerRadius: 10)
                                        .fill(Color.white)
                                        .frame(height: 50)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 10)
                                                .stroke(
                                                    viewModel.isError ? Color.errnoError :
                                                    (isCurrentBox && isOTPFieldFocused ? Color.errnoLime :
                                                     (!char.isEmpty ? Color.errnoLime.opacity(0.7) : Color.errnoStroke)),
                                                    lineWidth: (isCurrentBox && isOTPFieldFocused) || !char.isEmpty ? 1.5 : 1
                                                )
                                        )

                                    Text(char)
                                        .font(.system(size: 20, weight: .bold))
                                        .foregroundStyle(Color.errnoTextPrimary)
                                }
                            }
                        }
                        .contentShape(Rectangle())
                        .onTapGesture {
                            isOTPFieldFocused = true
                        }
                    }
                    .padding(.top, 4)

                    // Error Message
                    if let error = viewModel.errorMessage {
                        Text(error)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Color.errnoError)
                    }

                    // Resend Countdown
                    HStack(spacing: 4) {
                        Text("Resend OTP in")
                            .font(.system(size: 13, weight: .regular))
                            .foregroundStyle(Color.errnoTextSecondary)

                        let minutes = viewModel.timeRemaining / 60
                        let seconds = viewModel.timeRemaining % 60
                        Text(String(format: "%02d:%02d", minutes, seconds))
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Color.errnoLime)
                    }
                    .padding(.top, 2)

                    // Verify OTP Button
                    Button {
                        isOTPFieldFocused = false
                        viewModel.verifyOTP(role: role) { verifiedRole in
                            router.navigateToHome(role: verifiedRole)
                        }
                    } label: {
                        Group {
                            if viewModel.isLoading {
                                ProgressView()
                                    .tint(Color(hex: "#0B121F"))
                            } else {
                                Text("Verify OTP")
                                    .font(.system(size: 15, weight: .bold))
                                    .foregroundStyle(viewModel.isOTPComplete ? Color(hex: "#0B121F") : Color.errnoTextSecondary)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                        .background(viewModel.isOTPComplete ? Color.errnoLime : Color(hex: "#E5E7EB"))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    .disabled(!viewModel.isOTPComplete || viewModel.isLoading)
                    .padding(.top, 4)

                    // Resend Link
                    Button {
                        if viewModel.canResend {
                            viewModel.resendOTP()
                        }
                    } label: {
                        HStack(spacing: 4) {
                            Text("Didn't receive OTP?")
                                .font(.system(size: 13, weight: .regular))
                                .foregroundStyle(Color.errnoTextSecondary)

                            Text("Resend OTP")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundStyle(viewModel.canResend ? Color.errnoLime : Color.errnoTextSecondary.opacity(0.6))
                        }
                    }
                    .disabled(!viewModel.canResend)
                    .padding(.top, 2)
                }
                .padding(20)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 20))
                .shadow(color: Color.black.opacity(0.06), radius: 12, x: 0, y: 5)
                .padding(.horizontal, Spacing.lg)

                // Bottom Guarantee Card
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 20))
                        .foregroundStyle(Color.errnoLime)
                        .padding(.top, 2)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Your number is safe with us")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)

                        Text("We never share your number with anyone. It is used only for verification purposes.")
                            .font(.system(size: 11, weight: .regular))
                            .foregroundStyle(Color.errnoTextSecondary)
                            .lineSpacing(2)
                    }
                }
                .padding(16)
                .background(Color(hex: "#F8FAF5"))
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Color(hex: "#E8F2DF"), lineWidth: 1)
                )
                .padding(.horizontal, Spacing.lg)
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
                Text("Verify OTP")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Color.errnoTextPrimary)
            }
        }
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                isOTPFieldFocused = true
            }
        }
    }

    private func characterAt(_ index: Int) -> String {
        let otpArray = Array(viewModel.otp)
        if index < otpArray.count {
            return String(otpArray[index])
        }
        return ""
    }
}
