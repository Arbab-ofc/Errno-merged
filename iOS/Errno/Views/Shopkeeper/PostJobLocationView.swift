// PostJobLocationView.swift
// Errno — Views/Shopkeeper
//
// Matches Android "Post a New Job" step 3 (Location).

import SwiftUI

struct PostJobLocationView: View {
    var viewModel: PostJobViewModel
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        ZStack {
            Color.errnoBackground.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Custom Header
                HStack(spacing: Spacing.md) {
                    Button(action: { dismiss() }) {
                        Image(systemName: "arrow.left")
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                    }
                    
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Post a New Job")
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                        Text("Step 3 of 3 • Select Location")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(Color.errnoGreen)
                    }
                    Spacer()
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.vertical, Spacing.md)
                
                // Progress Bar
                HStack(spacing: 8) {
                    ProgressStepLocation(title: "1. Details", state: .completed)
                    ProgressStepLocation(title: "2. Duration", state: .completed)
                    ProgressStepLocation(title: "3. Location", state: .active)
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.bottom, Spacing.md)
                
                Divider().background(Color.errnoStroke)
                
                ScrollView {
                    VStack(alignment: .leading, spacing: Spacing.md) {
                        Text("Confirm Job Location")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                            .padding(.top, Spacing.md)
                        
                        // Fake Map
                        ZStack {
                            RoundedRectangle(cornerRadius: Radius.md)
                                .fill(Color.errnoSurfaceElevated)
                                .frame(height: 200)
                                .overlay(
                                    RoundedRectangle(cornerRadius: Radius.md)
                                        .strokeBorder(Color.errnoStroke, lineWidth: 1)
                                )
                            
                            VStack {
                                Image(systemName: "mappin.circle.fill")
                                    .font(.system(size: 40))
                                    .foregroundStyle(Color.errnoGreen)
                                Text("Okhla Market Area")
                                    .font(.system(size: 14, weight: .bold))
                                    .padding(.top, 4)
                            }
                        }
                    }
                    .padding(.horizontal, Spacing.lg)
                    .padding(.bottom, 120)
                }
            }
            
            // Bottom Action
            VStack {
                Spacer()
                HStack(spacing: Spacing.md) {
                    Button(action: { dismiss() }) {
                        Text("← Back")
                            .font(.system(size: 16, weight: .bold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .foregroundStyle(Color.errnoTextPrimary)
                            .background(Color.errnoSurface)
                            .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                            .overlay(
                                RoundedRectangle(cornerRadius: Radius.md)
                                    .strokeBorder(Color.errnoStroke, lineWidth: 1)
                            )
                    }
                    
                    NavigationLink(destination: PostJobSuccessView(viewModel: viewModel)) {
                        HStack {
                            if viewModel.isSubmitting {
                                ProgressView().tint(.white)
                            } else {
                                Text("Post Job")
                            }
                        }
                        .font(.system(size: 16, weight: .bold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color.errnoGreen)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                    }
                    .simultaneousGesture(TapGesture().onEnded {
                        viewModel.submitJob {}
                    })
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.vertical, Spacing.md)
                .background(Color.errnoSurface)
                .shadow(color: Color.black.opacity(0.05), radius: 10, y: -5)
            }
        }
        .navigationBarHidden(true)
    }
}

// MARK: - Progress Step Component

private struct ProgressStepLocation: View {
    let title: String
    let state: ProgressState
    
    var body: some View {
        Text(title)
            .font(.system(size: 14, weight: .bold))
            .foregroundStyle(textColor)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .background(bgColor)
            .clipShape(RoundedRectangle(cornerRadius: Radius.sm))
    }
    
    var textColor: Color {
        switch state {
        case .completed: return Color.errnoGreen
        case .active: return Color.errnoGreen
        case .inactive: return Color.errnoTextSecondary
        }
    }
    
    var bgColor: Color {
        switch state {
        case .completed: return Color.errnoLimeLight
        case .active: return Color.errnoLimeLight
        case .inactive: return Color.errnoStroke.opacity(0.5)
        }
    }
}
