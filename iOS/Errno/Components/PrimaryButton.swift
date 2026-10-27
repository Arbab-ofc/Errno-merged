// PrimaryButton.swift
// Errno
//
// Reusable primary CTA button component.
// Lime background with green text — the signature Errno action button.

import SwiftUI

// MARK: — Button Style Variants

enum ErrnoButtonStyle {
    case primary    // Lime bg, green text
    case secondary  // Outlined, green border + text
    case ghost      // No bg, lime text
    case danger     // Red bg, white text
    case dark       // Navy/Green bg, white text
}

enum ErrnoButtonSize {
    case large   // Full-width, 56pt height
    case medium  // 48pt height
    case small   // 38pt height, compact padding
    
    var height:          CGFloat { switch self { case .large: 56; case .medium: 48; case .small: 38 } }
    var horizontalPad:   CGFloat { switch self { case .large: 24; case .medium: 20; case .small: 16 } }
    var font:            Font    { switch self { case .large, .medium: .errnoLabelLarge; case .small: .errnoLabelMedium } }
}

// MARK: — Primary Button

struct PrimaryButton: View {
    let title:      String
    var icon:       String?      = nil  // SF Symbol name
    var style:      ErrnoButtonStyle = .primary
    var size:       ErrnoButtonSize  = .large
    var isLoading:  Bool         = false
    var isDisabled: Bool         = false
    var fullWidth:  Bool         = true
    let action:     () -> Void
    
    @State private var isPressed = false
    
    private var backgroundColor: Color {
        guard !isDisabled else { return .errnoStroke }
        switch style {
        case .primary:   return .errnoLime
        case .secondary: return .clear
        case .ghost:     return .clear
        case .danger:    return .errnoError
        case .dark:      return .errnoGreen
        }
    }
    
    private var foregroundColor: Color {
        guard !isDisabled else { return .errnoTextSecondary }
        switch style {
        case .primary:   return .errnoGreen
        case .secondary: return .errnoGreen
        case .ghost:     return .errnoLime
        case .danger:    return .white
        case .dark:      return .white
        }
    }
    
    private var strokeColor: Color {
        switch style {
        case .secondary: return isDisabled ? .errnoStroke : .errnoGreen
        default:         return .clear
        }
    }
    
    var body: some View {
        Button {
            guard !isDisabled && !isLoading else { return }
            action()
        } label: {
            ZStack {
                // Button background
                RoundedRectangle(cornerRadius: Radius.md)
                    .fill(backgroundColor)
                    .overlay(
                        RoundedRectangle(cornerRadius: Radius.md)
                            .strokeBorder(strokeColor, lineWidth: 1.5)
                    )
                
                // Lime gradient shimmer (primary only)
                if style == .primary && !isDisabled {
                    RoundedRectangle(cornerRadius: Radius.md)
                        .fill(Color.errnoLimeGradient)
                }
                
                // Content
                if isLoading {
                    ProgressView()
                        .tint(foregroundColor)
                        .scaleEffect(0.9)
                } else {
                    HStack(spacing: Spacing.sm) {
                        if let icon {
                            Image(systemName: icon)
                                .font(.system(size: 16, weight: .semibold))
                        }
                        Text(title)
                            .font(size.font)
                    }
                    .foregroundStyle(foregroundColor)
                }
            }
            .frame(height: size.height)
            .frame(maxWidth: fullWidth ? .infinity : nil)
            .padding(.horizontal, fullWidth ? 0 : size.horizontalPad)
        }
        .buttonStyle(.plain)
        .scaleEffect(isPressed ? 0.97 : 1.0)
        .animation(ErrnoAnimation.snappy, value: isPressed)
        .errnoShadow(style == .primary && !isDisabled ? Shadow.lime : Shadow.subtle)
        .simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in isPressed = true  }
                .onEnded   { _ in isPressed = false }
        )
        .disabled(isDisabled || isLoading)
        .accessibilityLabel(title)
    }
}

// MARK: — Previews

#Preview("Primary Button Variants") {
    ScrollView {
        VStack(spacing: Spacing.md) {
            PrimaryButton(title: "Post a Job", icon: "plus.circle.fill", action: {})
            PrimaryButton(title: "Continue",   style: .primary,    size: .large,  action: {})
            PrimaryButton(title: "Loading...", style: .primary,    isLoading: true, action: {})
            PrimaryButton(title: "Disabled",   style: .primary,    isDisabled: true, action: {})
            PrimaryButton(title: "Outline",    style: .secondary,  action: {})
            PrimaryButton(title: "Ghost",      style: .ghost,      action: {})
            PrimaryButton(title: "Danger",     style: .danger,     action: {})
            PrimaryButton(title: "Dark",       style: .dark,       action: {})
            PrimaryButton(title: "Small",      style: .primary,    size: .small,  fullWidth: false, action: {})
        }
        .padding(Spacing.lg)
    }
    .background(Color.errnoBackground)
}
