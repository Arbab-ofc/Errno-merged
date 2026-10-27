// Color+Extensions.swift
// Errno
//
// Design System — Brand color palette
// All colors match the Android UI tokens exactly.

import SwiftUI

extension Color {
    // MARK: — Brand Core
    
    /// Android action green — primary brand, headers, nav backgrounds
    static let errnoGreen = Color(hex: "#5B9600")
    
    /// Electric lime — CTAs, highlights, active tab indicators
    static let errnoLime = Color(hex: "#A4E637")
    
    /// Deep navy — dark backgrounds, splash screen, modals
    static let errnoNavy = Color(hex: "#0B121F")
    
    // MARK: — Surface & Background
    
    /// App-wide light background
    static let errnoBackground = Color(hex: "#F8F9FA")
    
    /// Cards, sheets, elevated surfaces
    static let errnoSurface = Color.white
    
    /// Elevated surface components (e.g., text fields, map overlays)
    static let errnoSurfaceElevated = Color.white
    
    // MARK: — Text
    
    /// Primary body text (same as Navy)
    static let errnoTextPrimary = Color(hex: "#0B121F")
    
    /// Subtitles, captions, placeholder text
    static let errnoTextSecondary = Color(hex: "#6C757D")
    
    /// Text rendered on dark (green/navy) backgrounds
    static let errnoTextOnDark = Color.white
    
    // MARK: — Semantic
    
    /// Validation errors, destructive actions
    static let errnoError = Color(hex: "#EF4444")
    
    /// Success states, completion indicators
    static let errnoSuccess = Color(hex: "#22C55E")
    
    /// Warning / amber states
    static let errnoWarning = Color(hex: "#F59E0B")
    
    // MARK: — Utility
    
    /// Borders, dividers, stroke lines
    static let errnoStroke = Color(hex: "#E5E7EB")
    
    /// Light tint of ErrnoGreen for chip/tag backgrounds
    static let errnoGreenLight = Color(hex: "#EAF5D8")
    
    /// Light tint of ErrnoLime for soft highlights
    static let errnoLimeLight = Color(hex: "#EAF5D8")
    
    // MARK: — Gradient Helpers
    
    /// Vertical gradient: Navy → ErrnoGreen (used on Splash + dark screens)
    static var errnoSplashGradient: LinearGradient {
        LinearGradient(
            colors: [.errnoNavy, .errnoGreen],
            startPoint: .top,
            endPoint: .bottom
        )
    }
    
    /// Lime accent gradient for buttons & highlights
    static var errnoLimeGradient: LinearGradient {
        LinearGradient(
            colors: [Color(hex: "#B5F040"), .errnoLime],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}

// MARK: — Hex Initialiser

extension Color {
    /// Initialises a Color from a hex string (e.g. "#A4E637" or "A4E637").
    init(hex: String) {
        let sanitized = hex.trimmingCharacters(in: .alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: sanitized).scanHexInt64(&int)
        
        let r, g, b, a: UInt64
        switch sanitized.count {
        case 6: // RGB (no alpha)
            (r, g, b, a) = ((int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF, 255)
        case 8: // RGBA
            (r, g, b, a) = ((int >> 24) & 0xFF, (int >> 16) & 0xFF, (int >> 8) & 0xFF, int & 0xFF)
        default:
            (r, g, b, a) = (0, 0, 0, 255)
        }
        
        self.init(
            .sRGB,
            red:   Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
