// PayStructureView.swift
// Errno — Views/Shopkeeper
//
// Matches Android "Post a New Job" step 2 (Duration).

import SwiftUI

struct PayStructureView: View {
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
                        Text("Step 2 of 3 • Select Duration Needed")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(Color.errnoGreen)
                    }
                    Spacer()
                }
                .padding(.horizontal, 20)
                .padding(.vertical, Spacing.md)
                
                // Progress Bar
                HStack(spacing: 8) {
                    ProgressStep(title: "1. Details", state: .completed)
                    ProgressStep(title: "2. Duration", state: .active)
                    ProgressStep(title: "3. Location", state: .inactive)
                }
                .padding(.horizontal, 20)
                .padding(.bottom, Spacing.md)
                
                Divider().background(Color.errnoStroke)
                
                ScrollView {
                    VStack(alignment: .leading, spacing: Spacing.md) {
                        Text("How much time do you need the worker for?")
                            .font(.system(size: 15, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                            .padding(.top, Spacing.md)
                        
                        Text("Select a configured duration. The final customer price is quoted for the scheduled service time.")
                            .errnoBodyMedium(color: .errnoTextSecondary)
                        
                        if viewModel.pricingOptions.isEmpty {
                            if let error = viewModel.errorMessage {
                                Text(error).font(.footnote).foregroundStyle(Color.errnoError)
                                Button("Retry loading prices") { Task { await viewModel.loadPricingOptions() } }.tint(.errnoGreen)
                            } else { Text("Loading approved prices…").errnoBodyMedium(color: .errnoTextSecondary) }
                        }
                        VStack(spacing: Spacing.md) {
                            ForEach(viewModel.pricingOptions.sorted(by: { $0.hours < $1.hours }), id: \.hours) { option in
                                DurationOptionCard(
                                    label: "\(option.hours) Hour\(option.hours == 1 ? "" : "s")",
                                    rate: NSDecimalNumber(decimal: option.maximum).intValue,
                                    isSelected: viewModel.estimatedDurationHours == Double(option.hours)
                                ) {
                                    viewModel.estimatedDurationHours = Double(option.hours)
                                    viewModel.payType = .fixed
                                }
                            }
                            
                        }
                    }
                    .padding(.horizontal, 20)
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
                    
                    NavigationLink(destination: PostJobLocationView(viewModel: viewModel)) {
                        Text("Next: Location →")
                            .font(.system(size: 16, weight: .bold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(Color.errnoGreen)
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                    }
                    .disabled(!viewModel.isStep3Valid || viewModel.pricingOptions.isEmpty)
                    .opacity(viewModel.isStep3Valid && !viewModel.pricingOptions.isEmpty ? 1 : 0.55)
                }
                .padding(.horizontal, 20)
                .padding(.vertical, Spacing.md)
                .background(Color.errnoSurface)
                .shadow(color: Color.black.opacity(0.05), radius: 10, y: -5)
            }
        }
        .navigationBarHidden(true)
        .task { await viewModel.loadPricingOptions() }
    }
}

// MARK: - Progress Step Component

enum ProgressState {
    case completed
    case active
    case inactive
}

private struct ProgressStep: View {
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

// MARK: - Duration Option Card

private struct DurationOptionCard: View {
    let label: String
    let rate: Int
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: Spacing.md) {
                Image(systemName: isSelected ? "largecircle.fill.circle" : "circle")
                    .font(.system(size: 24)).foregroundStyle(isSelected ? Color.errnoGreen : .gray)
                    .frame(width: 44, height: 44)

                VStack(alignment: .leading, spacing: 4) {
                    Text(label)
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(Color.errnoTextPrimary)
                    Text("Pay Rate: ₹\(rate)")
                        .errnoBodyMedium(color: .errnoTextSecondary)
                }
                
                Spacer()
                
                if isSelected {
                    HStack(spacing: 4) {
                        Image(systemName: "checkmark")
                        Text("Selected")
                    }
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(Color.errnoGreen)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.errnoLimeLight)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                }
            }
            .padding(.horizontal, 16).padding(.vertical, 14)
            .background(Color.errnoSurface)
            .clipShape(RoundedRectangle(cornerRadius: Radius.md))
            .overlay(
                RoundedRectangle(cornerRadius: Radius.md)
                    .strokeBorder(isSelected ? Color.errnoGreen : Color.errnoStroke, lineWidth: isSelected ? 2 : 1)
            )
        }
        .buttonStyle(.plain)
    }
}
