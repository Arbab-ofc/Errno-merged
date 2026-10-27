// PostJobView.swift
// Errno — Views/Shopkeeper
//
// Matches Android "Post a New Job" step 1.

import SwiftUI

struct PostJobView: View {
    @State private var viewModel = PostJobViewModel()
    @Environment(\.dismiss) private var dismiss
    
    // For the custom date picker chips
    private let dates: [Date] = (0..<6).map { Calendar.current.date(byAdding: .day, value: $0, to: Date())! }
    
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
                        Text("Step 1 of 3 • Basic Details & Calendar Schedule")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(Color.errnoGreen)
                    }
                    Spacer()
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.vertical, Spacing.md)
                
                // Progress Bar
                HStack(spacing: 8) {
                    ProgressStep(title: "1. Details", isActive: true)
                    ProgressStep(title: "2. Duration", isActive: false)
                    ProgressStep(title: "3. Location", isActive: false)
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.bottom, Spacing.md)
                
                Divider().background(Color.errnoStroke)
                
                ScrollView {
                    VStack(alignment: .leading, spacing: Spacing.xl) {
                        Text("Basic Information & Calendar Booking")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                            .padding(.top, Spacing.md)
                        
                        // Category Dropdown mock
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Job Category")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)
                            
                            Menu {
                                ForEach(JobCategory.allCases, id: \.self) { category in
                                    Button(category.rawValue) {
                                        viewModel.category = category
                                    }
                                }
                            } label: {
                                HStack {
                                    Text(viewModel.category.rawValue)
                                        .font(.system(size: 16))
                                        .foregroundStyle(Color.errnoTextPrimary)
                                    Spacer()
                                    Image(systemName: "chevron.down")
                                        .foregroundStyle(Color.errnoTextPrimary)
                                }
                                .padding(Spacing.md)
                                .background(Color.errnoSurfaceElevated)
                                .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                                .overlay(
                                    RoundedRectangle(cornerRadius: Radius.md)
                                        .strokeBorder(Color.errnoStroke, lineWidth: 1)
                                )
                            }
                        }
                        
                        // Job Title
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Job Title")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)
                            
                            TextField("e.g. Delivery Partner", text: $viewModel.title)
                                .font(.system(size: 16))
                                .padding(Spacing.md)
                                .background(Color.errnoSurfaceElevated)
                                .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                                .overlay(
                                    RoundedRectangle(cornerRadius: Radius.md)
                                        .strokeBorder(Color.errnoStroke, lineWidth: 1)
                                )
                        }
                        
                        // Calendar Schedule
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Text("Select Schedule Date (Calendar)")
                                    .font(.system(size: 14, weight: .bold))
                                Spacer()
                                Text("Max 6 Days Ahead Limit")
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundStyle(Color.errnoGreen)
                            }
                            
                            ScrollView(.horizontal, showsIndicators: false) {
                                HStack(spacing: Spacing.sm) {
                                    ForEach(0..<dates.count, id: \.self) { index in
                                        let date = dates[index]
                                        let isSelected = Calendar.current.isDate(viewModel.scheduledStartTime, inSameDayAs: date)
                                        
                                        Button(action: {
                                            viewModel.scheduledStartTime = date
                                            viewModel.isScheduled = true
                                        }) {
                                            VStack(spacing: 4) {
                                                Image(systemName: "calendar")
                                                    .font(.system(size: 16))
                                                Text(dateLabel(for: index))
                                                    .font(.system(size: 14, weight: .bold))
                                            }
                                            .frame(width: 80, height: 70)
                                            .foregroundStyle(isSelected ? Color.errnoGreen : Color.errnoTextSecondary)
                                            .background(isSelected ? Color.errnoGreen.opacity(0.1) : Color.errnoSurfaceElevated)
                                            .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                                            .overlay(
                                                RoundedRectangle(cornerRadius: Radius.md)
                                                    .strokeBorder(isSelected ? Color.errnoGreen : Color.errnoStroke, lineWidth: 1)
                                            )
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Job Description
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Job Description & Requirements")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)
                            
                            TextEditor(text: $viewModel.description)
                                .font(.system(size: 16))
                                .frame(height: 120)
                                .padding(4) // Internal padding
                                .background(Color.errnoSurfaceElevated)
                                .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                                .overlay(
                                    RoundedRectangle(cornerRadius: Radius.md)
                                        .strokeBorder(Color.errnoStroke, lineWidth: 1)
                                )
                                .onChange(of: viewModel.description) { _, newValue in
                                    if newValue.count > 250 {
                                        viewModel.description = String(newValue.prefix(250))
                                    }
                                }
                            
                            Text("\(viewModel.description.count)/250")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundStyle(Color.errnoTextSecondary)
                                .frame(maxWidth: .infinity, alignment: .trailing)
                        }
                    }
                    .padding(.horizontal, Spacing.lg)
                    .padding(.bottom, 100)
                }
            }
            
            // Bottom Action
            VStack {
                Spacer()
                VStack {
                    NavigationLink(destination: PayStructureView(viewModel: viewModel)) {
                        Text("Next: Select Duration →")
                            .font(.system(size: 16, weight: .bold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(viewModel.isStep1Valid ? Color.errnoGreen : Color.errnoStroke)
                            .foregroundStyle(viewModel.isStep1Valid ? .white : Color.errnoTextSecondary)
                            .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                    }
                    .disabled(!viewModel.isStep1Valid)
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.vertical, Spacing.md)
                .background(Color.errnoSurface)
                .shadow(color: Color.black.opacity(0.05), radius: 10, y: -5)
            }
        }
        .navigationBarHidden(true)
    }
    
    private func dateLabel(for index: Int) -> String {
        switch index {
        case 0: return "Today"
        case 1: return "Tomorrow"
        default: return "+\(index) Days"
        }
    }
}

// MARK: - Progress Step Component

private struct ProgressStep: View {
    let title: String
    let isActive: Bool
    
    var body: some View {
        Text(title)
            .font(.system(size: 14, weight: .bold))
            .foregroundStyle(isActive ? Color.errnoGreen : Color.errnoTextSecondary)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .background(isActive ? Color.errnoGreen.opacity(0.1) : Color.errnoStroke.opacity(0.5))
            .clipShape(RoundedRectangle(cornerRadius: Radius.sm))
    }
}
