// RegisterView.swift
// Errno — Views/Auth
//
// Matches Android "Create Account" screen.

import SwiftUI

struct RegisterView: View {
    @Environment(AppRouter.self) private var router
    @Environment(\.dismiss) private var dismiss

    var initialRole: UserRole = .shopkeeper

    @State private var selectedRole: UserRole = .shopkeeper
    @State private var fullName: String = ""
    @State private var phoneNumber: String = ""
    @State private var isLoading: Bool = false
    @State private var registrationTask: Task<Void, Never>?
    @State private var initialized = false
    @State private var googlePlaceholder = false
    @State private var errorMessage: String? = nil

    @FocusState private var focusedField: Field?

    private enum Field {
        case name, phone
    }

    private var isValid: Bool {
        !fullName.trimmingCharacters(in: .whitespaces).isEmpty && phoneNumber.count == 10
    }

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: Spacing.lg) {
                // Header
                VStack(alignment: .leading, spacing: 6) {
                    Text("Join ERRNO Community")
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(Color.errnoTextPrimary)

                    Text("Fill in your details to get started")
                        .font(.system(size: 13, weight: .regular))
                        .foregroundStyle(Color.errnoTextSecondary)
                }
                .padding(.top, Spacing.xs)

                // Role Selector Section
                VStack(alignment: .leading, spacing: Spacing.sm) {
                    Text("I want to register as")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(Color.errnoTextPrimary)

                    HStack(spacing: 12) {
                        RegisterRoleCard(
                            role: .shopkeeper,
                            title: "Shop Owner",
                            subtitle: "Hire workers for your store",
                            iconName: "storefront",
                            isSelected: selectedRole == .shopkeeper
                        ) {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                selectedRole = .shopkeeper
                            }
                        }

                        RegisterRoleCard(
                            role: .worker,
                            title: "Worker",
                            subtitle: "Find daily wage work easily",
                            iconName: "wrench.and.screwdriver",
                            isSelected: selectedRole == .worker
                        ) {
                            withAnimation(.easeInOut(duration: 0.2)) {
                                selectedRole = .worker
                            }
                        }
                    }
                }

                // Input Fields
                VStack(spacing: 14) {
                    // Full Name
                    HStack(spacing: 12) {
                        Image(systemName: "person.fill")
                            .font(.system(size: 16))
                            .foregroundStyle(Color.errnoLime)
                            .frame(width: 24)

                        TextField("Full Name", text: $fullName)
                            .font(.system(size: 15, weight: .medium))
                            .focused($focusedField, equals: .name)
                    }
                    .frame(height: 52)
                    .padding(.horizontal, 14)
                    .background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(focusedField == .name ? Color.errnoLime : Color.errnoStroke, lineWidth: 1)
                    )

                    // Mobile Number
                    HStack(spacing: 12) {
                        Image(systemName: "phone.fill")
                            .font(.system(size: 16))
                            .foregroundStyle(Color.errnoLime)
                            .frame(width: 24)

                        TextField("Mobile Number", text: $phoneNumber)
                            .font(.system(size: 15, weight: .medium))
                            .keyboardType(.numberPad)
                            .focused($focusedField, equals: .phone)
                            .onChange(of: phoneNumber) { _, newValue in
                                let digits = newValue.filter { $0.isNumber }
                                if digits.count > 10 {
                                    phoneNumber = String(digits.prefix(10))
                                } else if digits != newValue {
                                    phoneNumber = digits
                                }
                            }
                    }
                    .frame(height: 52)
                    .padding(.horizontal, 14)
                    .background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(focusedField == .phone ? Color.errnoLime : Color.errnoStroke, lineWidth: 1)
                    )
                }
                .padding(.top, 4)

                if let error = errorMessage {
                    Text(error)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(Color.errnoError)
                }

                // Action Button: Create Account
                Button {
                    focusedField = nil
                    isLoading = true
                    errorMessage = nil

                    registrationTask = Task {
                        do { try await Task.sleep(for: .milliseconds(600)) } catch { isLoading = false; return }
                        guard !Task.isCancelled else { return }
                        await MainActor.run {
                            isLoading = false
                            router.registrationName = fullName.trimmingCharacters(in: .whitespacesAndNewlines)
                            router.navigateToOTP(phone: phoneNumber, role: selectedRole)
                        }
                    }
                } label: {
                    Group {
                        if isLoading {
                            ProgressView()
                                .tint(isValid ? Color(hex: "#0B121F") : Color.errnoTextSecondary)
                        } else {
                            Text("Create Account")
                                .font(.system(size: 15, weight: .bold))
                                .foregroundStyle(isValid ? Color(hex: "#0B121F") : Color.errnoTextSecondary)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(isValid ? Color.errnoLime : Color(hex: "#E5E7EB"))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .disabled(!isValid || isLoading)
                .padding(.top, Spacing.xs)

                Button { googlePlaceholder = true } label: {
                    HStack(spacing: 12) { Text("G").foregroundStyle(.blue).font(.system(size: 20, weight: .bold)); Text("Sign up with Google").font(.system(size: 15, weight: .bold)) }
                        .frame(maxWidth: .infinity).frame(height: 52)
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.errnoStroke))
                }.foregroundStyle(Color.errnoTextPrimary)
                // Footer Links
                VStack(spacing: Spacing.md) {
                    Button {
                        // Return to login
                        router.navigateToLogin(role: selectedRole)
                    } label: {
                        HStack(spacing: 4) {
                            Text("Already have an account?")
                                .font(.system(size: 13, weight: .regular))
                                .foregroundStyle(Color.errnoTextPrimary)
                            Text("Login")
                                .font(.system(size: 13, weight: .bold))
                                .foregroundStyle(Color.errnoLime)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, 4)

                    Spacer(minLength: 40)

                    LegalLinks()
                    MockNotice(text: "Demo registration is kept only for this app session.")
                    // Trust Badge
                    HStack(spacing: 6) {
                        Image(systemName: "shield.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(Color.errnoTextSecondary)
                        Text("Secure & Verified Platform")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Color.errnoTextSecondary)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.bottom, Spacing.lg)
                }
            }
            .padding(.horizontal, Spacing.lg)
        }
        .background(Color(hex: "#FFFFFF").ignoresSafeArea())
        .toolbar(.visible, for: .navigationBar)
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
                Text("Create Account")
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(Color.errnoTextPrimary)
            }
        }
        .alert("Google Sign-Up", isPresented: $googlePlaceholder) { Button("OK", role: .cancel) {} }
        message: { Text("Google registration is a placeholder in the Android reference. Use the local phone flow.") }
        .onDisappear { registrationTask?.cancel(); isLoading = false }
        .onAppear {
            if !initialized { selectedRole = initialRole; initialized = true }
        }
    }
}

// MARK: — Register Role Card

private struct RegisterRoleCard: View {
    let role: UserRole
    let title: String
    let subtitle: String
    let iconName: String
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            ZStack(alignment: .topTrailing) {
                VStack(alignment: .center, spacing: 6) {
                    Image(systemName: iconName)
                        .font(.system(size: 26))
                        .foregroundStyle(isSelected ? Color.errnoLime : Color.errnoTextSecondary)
                        .frame(height: 32)

                    Text(title)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(isSelected ? Color.errnoLime : Color.errnoTextPrimary)

                    Text(subtitle)
                        .font(.system(size: 10, weight: .regular))
                        .foregroundStyle(Color.errnoTextSecondary)
                        .multilineTextAlignment(.center)
                        .lineLimit(2)
                        .minimumScaleFactor(0.85)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .padding(.horizontal, 10)
                .background(Color.white)
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(isSelected ? Color.errnoLime : Color.errnoStroke, lineWidth: isSelected ? 2 : 1)
                )

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 15))
                        .foregroundStyle(Color.errnoLime)
                        .padding(8)
                }
            }
        }
        .buttonStyle(.plain)
    }
}
