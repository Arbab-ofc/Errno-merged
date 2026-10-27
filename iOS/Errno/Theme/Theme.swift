// Theme.swift
// Errno
//
// Design System — Global spacing, radius, shadow, and animation constants

import SwiftUI

// MARK: — Spacing

enum Spacing {
    static let xs:  CGFloat = 4
    static let sm:  CGFloat = 8
    static let md:  CGFloat = 16
    static let lg:  CGFloat = 24
    static let xl:  CGFloat = 32
    static let xxl: CGFloat = 48
    static let xxxl: CGFloat = 64
}

// MARK: — Corner Radius

enum Radius {
    static let sm:   CGFloat = 8
    static let md:   CGFloat = 12
    static let lg:   CGFloat = 16
    static let xl:   CGFloat = 24
    static let xxl:  CGFloat = 32
    static let full: CGFloat = 9999
}

// MARK: — Shadows

struct ErrnoShadow {
    let color:   Color
    let radius:  CGFloat
    let x:       CGFloat
    let y:       CGFloat
}

enum Shadow {
    static let subtle = ErrnoShadow(
        color:  Color.black.opacity(0.06),
        radius: 8, x: 0, y: 2
    )
    static let card = ErrnoShadow(
        color:  Color.black.opacity(0.10),
        radius: 16, x: 0, y: 4
    )
    static let modal = ErrnoShadow(
        color:  Color.black.opacity(0.18),
        radius: 24, x: 0, y: 8
    )
    static let lime = ErrnoShadow(
        color:  Color.errnoLime.opacity(0.40),
        radius: 16, x: 0, y: 6
    )
    static let green = ErrnoShadow(
        color:  Color.errnoGreen.opacity(0.30),
        radius: 12, x: 0, y: 4
    )
}

// MARK: — Animation Constants

enum ErrnoAnimation {
    static let spring        = Animation.spring(response: 0.4, dampingFraction: 0.75)
    static let snappy        = Animation.spring(response: 0.3, dampingFraction: 0.8)
    static let smooth        = Animation.easeInOut(duration: 0.3)
    static let smoothSlow    = Animation.easeInOut(duration: 0.5)
    static let bouncy        = Animation.spring(response: 0.5, dampingFraction: 0.65)
}

// MARK: — View+Shadow Helper

extension View {
    func errnoBadge() -> some View {
        self
            .font(.errnoLabelSmall)
            .foregroundStyle(.white)
            .padding(.horizontal, Spacing.sm)
            .padding(.vertical, Spacing.xs)
            .background(Color.errnoError)
            .clipShape(Capsule())
    }
    
    func errnoCard(padding: CGFloat = Spacing.md) -> some View {
        self
            .padding(padding)
            .background(Color.errnoSurface)
            .clipShape(RoundedRectangle(cornerRadius: Radius.lg))
            .shadow(
                color:  Shadow.card.color,
                radius: Shadow.card.radius,
                x:      Shadow.card.x,
                y:      Shadow.card.y
            )
    }
    
    func errnoShadow(_ style: ErrnoShadow) -> some View {
        shadow(color: style.color, radius: style.radius, x: style.x, y: style.y)
    }
}

// MARK: — Icon Sizes

enum IconSize {
    static let sm:  CGFloat = 16
    static let md:  CGFloat = 20
    static let lg:  CGFloat = 24
    static let xl:  CGFloat = 32
    static let xxl: CGFloat = 48
}

// MARK: — Z-Index Layers

enum ZLayer {
    static let base:    Double = 0
    static let card:    Double = 1
    static let overlay: Double = 2
    static let modal:   Double = 3
    static let toast:   Double = 4
}
