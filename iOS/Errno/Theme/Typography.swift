// Typography.swift
// Errno
//
// Design System — Font styles & text ViewModifiers
// Uses SF Pro system fonts (no external dependencies).

import SwiftUI

// MARK: — Font Scale

extension Font {
    // Display — large hero text
    static var errnoDisplayLarge: Font  { .system(size: 34, weight: .bold,     design: .rounded) }
    static var errnoDisplayMedium: Font { .system(size: 28, weight: .bold,     design: .rounded) }
    
    // Headline — section titles
    static var errnoHeadlineLarge: Font  { .system(size: 24, weight: .semibold, design: .default) }
    static var errnoHeadlineMedium: Font { .system(size: 20, weight: .semibold, design: .default) }
    static var errnoHeadlineSmall: Font  { .system(size: 18, weight: .semibold, design: .default) }
    
    // Body — reading text
    static var errnoBodyLarge: Font  { .system(size: 17, weight: .regular, design: .default) }
    static var errnoBodyMedium: Font { .system(size: 15, weight: .regular, design: .default) }
    static var errnoBodySmall: Font  { .system(size: 13, weight: .regular, design: .default) }
    
    // Label — buttons, tags, inputs
    static var errnoLabelLarge: Font  { .system(size: 15, weight: .semibold, design: .default) }
    static var errnoLabelMedium: Font { .system(size: 13, weight: .medium,   design: .default) }
    static var errnoLabelSmall: Font  { .system(size: 12, weight: .medium,   design: .default) }
    
    // Caption — micro text, timestamps
    static var errnoCaption: Font      { .system(size: 11, weight: .regular, design: .default) }
    static var errnoOverline: Font     { .system(size: 10, weight: .semibold, design: .default) }
}

// MARK: — ViewModifier Helpers

struct ErrnoTextStyle: ViewModifier {
    let font: Font
    let color: Color
    let tracking: CGFloat
    
    init(font: Font, color: Color = .errnoTextPrimary, tracking: CGFloat = 0) {
        self.font     = font
        self.color    = color
        self.tracking = tracking
    }
    
    func body(content: Content) -> some View {
        content
            .font(font)
            .foregroundStyle(color)
            .tracking(tracking)
    }
}

extension View {
    // MARK: Display
    func errnoDisplayLarge(color: Color = .errnoTextOnDark) -> some View {
        modifier(ErrnoTextStyle(font: .errnoDisplayLarge, color: color))
    }
    
    func errnoDisplayMedium(color: Color = .errnoTextPrimary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoDisplayMedium, color: color))
    }
    
    // MARK: Headline
    func errnoHeadlineLarge(color: Color = .errnoTextPrimary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoHeadlineLarge, color: color))
    }
    
    func errnoHeadlineMedium(color: Color = .errnoTextPrimary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoHeadlineMedium, color: color))
    }
    
    func errnoHeadlineSmall(color: Color = .errnoTextPrimary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoHeadlineSmall, color: color))
    }
    
    // MARK: Body
    func errnoBodyLarge(color: Color = .errnoTextPrimary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoBodyLarge, color: color))
    }
    
    func errnoBodyMedium(color: Color = .errnoTextPrimary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoBodyMedium, color: color))
    }
    
    func errnoBodySmall(color: Color = .errnoTextSecondary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoBodySmall, color: color))
    }
    
    // MARK: Label
    func errnoLabelLarge(color: Color = .errnoTextPrimary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoLabelLarge, color: color))
    }
    
    func errnoLabelMedium(color: Color = .errnoTextSecondary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoLabelMedium, color: color))
    }
    
    func errnoLabelSmall(color: Color = .errnoTextSecondary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoLabelSmall, color: color))
    }
    
    // MARK: Caption
    func errnoCaption(color: Color = .errnoTextSecondary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoCaption, color: color))
    }
    
    func errnoOverline(color: Color = .errnoTextSecondary) -> some View {
        modifier(ErrnoTextStyle(font: .errnoOverline, color: color, tracking: 1.2))
    }
}
