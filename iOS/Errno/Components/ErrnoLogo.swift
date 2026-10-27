// ErrnoLogo.swift
// Errno
//
// Reusable brand logo component — used on SplashView, RoleSelectionView, and profile screens.
// Supports light (on-dark) and dark (on-light) variants, plus configurable sizes.

import SwiftUI

// MARK: — Logo Variant

enum ErrnoLogoVariant {
    /// White wordmark + lime icon — for dark/green backgrounds
    case light
    /// Dark wordmark + green icon — for light/white backgrounds
    case dark
    /// Icon mark only (no wordmark)
    case iconOnly
}

// MARK: — Logo Size

enum ErrnoLogoSize {
    case small   // Icon 24, text 18
    case medium  // Icon 32, text 24
    case large   // Icon 64, text 48
    
    var iconSize:  CGFloat { switch self { case .small: 24; case .medium: 32; case .large: 64 } }
    var textSize:  CGFloat { switch self { case .small: 18; case .medium: 24; case .large: 48 } }
    var spacing:   CGFloat { switch self { case .small:  6; case .medium:  8; case .large: 16 } }
}

// MARK: — ErrnoLogo Component

struct ErrnoLogo: View {
    var variant: ErrnoLogoVariant = .light
    var size:    ErrnoLogoSize    = .large
    var animate: Bool             = false
    
    @State private var isAnimating = false
    
    private var iconColor: Color {
        switch variant {
        case .light:    .errnoLime
        case .dark:     .errnoGreen
        case .iconOnly: .errnoLime
        }
    }
    
    private var textColor: Color {
        switch variant {
        case .light:    .white
        case .dark:     .errnoGreen
        case .iconOnly: .clear
        }
    }
    
    var body: some View {
        HStack(spacing: size.spacing) {
            // Icon Mark — stylized "E"
            ErrnoIconMark(size: size.iconSize, color: iconColor)
                .scaleEffect(isAnimating ? 1.0 : (animate ? 0.6 : 1.0))
                .opacity(isAnimating ? 1.0 : (animate ? 0.0 : 1.0))
            
            if variant != .iconOnly {
                // Wordmark & Subtitle
                VStack(alignment: .leading, spacing: size == .large ? 4 : 0) {
                    Text("Errno")
                        .font(.system(size: size.textSize, weight: .semibold, design: .rounded))
                        .foregroundStyle(textColor)
                        .opacity(isAnimating ? 1.0 : (animate ? 0.0 : 1.0))
                        .offset(x: isAnimating ? 0 : (animate ? -8 : 0))
                    
                    if size == .large {
                        Text("SMART SOLUTIONS")
                            .font(.system(size: size.textSize * 0.25, weight: .bold, design: .default))
                            .foregroundStyle(Color.errnoLime)
                            .tracking(2)
                            .opacity(isAnimating ? 1.0 : (animate ? 0.0 : 1.0))
                            .offset(x: isAnimating ? 0 : (animate ? -8 : 0))
                    }
                }
            }
        }
        .onAppear {
            guard animate else {
                isAnimating = true
                return
            }
            withAnimation(ErrnoAnimation.bouncy.delay(0.2)) {
                isAnimating = true
            }
        }
    }
}

// MARK: — Icon Mark

/// Custom "errno" icon — a stylized letter 'E' made of a continuous rounded path
struct ErrnoIconMark: View {
    let size:  CGFloat
    let color: Color
    
    var body: some View {
        ZStack {
            // The 'E' is drawn as a stroked path
            Path { path in
                let w = size
                let h = size
                let r = size * 0.35 // Large corner radius for the outer curves
                
                // Top bar right
                path.move(to: CGPoint(x: w * 0.9, y: h * 0.15))
                // Curve to top left
                path.addLine(to: CGPoint(x: r, y: h * 0.15))
                path.addArc(
                    center: CGPoint(x: r, y: r + h * 0.15),
                    radius: r,
                    startAngle: .degrees(-90),
                    endAngle: .degrees(180),
                    clockwise: true
                )
                // Curve to bottom left
                path.addLine(to: CGPoint(x: 0, y: h - r - h * 0.15))
                path.addArc(
                    center: CGPoint(x: r, y: h - r - h * 0.15),
                    radius: r,
                    startAngle: .degrees(180),
                    endAngle: .degrees(90),
                    clockwise: true
                )
                // Bottom bar right
                path.addLine(to: CGPoint(x: w * 0.9, y: h * 0.85))
                
                // Middle bar
                path.move(to: CGPoint(x: 0, y: h * 0.5))
                path.addLine(to: CGPoint(x: w * 0.7, y: h * 0.5))
            }
            .stroke(
                LinearGradient(
                    colors: [Color.errnoLime, Color.errnoGreen],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                ),
                style: StrokeStyle(lineWidth: size * 0.18, lineCap: .round, lineJoin: .round)
            )
        }
        .frame(width: size, height: size)
    }
}

// MARK: — Previews

#Preview("Logo Variants") {
    VStack(spacing: Spacing.xl) {
        ZStack {
            Color.errnoNavy.ignoresSafeArea()
            VStack(spacing: Spacing.lg) {
                ErrnoLogo(variant: .light, size: .large,  animate: false)
                ErrnoLogo(variant: .light, size: .medium, animate: false)
                ErrnoLogo(variant: .light, size: .small,  animate: false)
            }
        }
        .frame(height: 300)
        
        ZStack {
            Color.errnoBackground.ignoresSafeArea()
            VStack(spacing: Spacing.lg) {
                ErrnoLogo(variant: .dark, size: .large,  animate: false)
                ErrnoLogo(variant: .iconOnly, size: .large, animate: false)
            }
        }
        .frame(height: 250)
    }
    .ignoresSafeArea()
}
