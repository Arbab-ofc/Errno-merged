// PostJobView.swift
// Errno — Views/Shopkeeper
//
// Matches Android "Post a New Job" step 1.

import SwiftUI

struct PostJobView: View {
    @State private var viewModel: PostJobViewModel
    init(store: LocalMarketplaceStore) {
        _viewModel = State(initialValue: PostJobViewModel(jobService: MockJobService(store: store), currentUser: store.shopkeeper))
    }
    @Environment(\.dismiss) private var dismiss
    
    
    var body: some View {
        ZStack {
            Color.errnoBackground.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Custom Header
                HStack(spacing: Spacing.md) {
                    Button(action: { dismiss() }) {
                        Image(systemName: "arrow.left")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                    }
                    
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Post a New Job")
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                        Text("Step 1 of 3 • Basic Details & Calendar Schedule")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundStyle(Color.errnoGreen)
                    }
                    Spacer()
                }
                .padding(.horizontal, 20)
                .padding(.vertical, Spacing.md)
                
                // Progress Bar
                HStack(spacing: 8) {
                    ProgressStep(title: "1. Details", isActive: true)
                    ProgressStep(title: "2. Duration", isActive: false)
                    ProgressStep(title: "3. Location", isActive: false)
                }
                .padding(.horizontal, 20)
                .padding(.bottom, Spacing.md)
                
                Divider().background(Color.errnoStroke)
                
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Basic Information & Calendar Booking")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                            .padding(.top, Spacing.md)
                        
                        // Category Dropdown mock
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Job Category")
                                .font(.system(size: 14, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)
                            
                            Menu {
                                ForEach(JobCategory.marketplaceCategories, id: \.self) { category in
                                    Button(category.rawValue) {
                                        viewModel.category = category
                                        viewModel.title = category.rawValue
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
                        
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Select Schedule Date & Time (Calendar)").font(.system(size: 15, weight: .bold))
                            Text("Current Month Calendar • Maximum 6-Day Pre-Booking Limit").font(.system(size: 11)).foregroundStyle(.gray)
                            DatePicker("Work Date (Calendar)", selection: $viewModel.scheduledStartTime,
                                       in: Calendar.current.startOfDay(for: Date())...(Calendar.current.date(byAdding: .day, value: 6, to: Calendar.current.startOfDay(for: Date())) ?? Date()),
                                       displayedComponents: .date)
                            Picker("Start Time", selection: $viewModel.selectedTime) {
                                ForEach(9...20, id: \.self) { hour in
                                    Text(String(format: "%02d:00 %@", hour > 12 ? hour - 12 : hour, hour >= 12 ? "PM" : "AM")).tag(hour)
                                }
                            }.pickerStyle(.menu)
                            Text("Scheduled Work: \(viewModel.scheduledStartTime.formatted(date: .abbreviated, time: .omitted)) at \(viewModel.selectedTime):00")
                                .font(.system(size: 12, weight: .bold)).foregroundStyle(Color.errnoGreen)
                        }.marketplaceCard(radius: 14)

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
                    .padding(.horizontal, 20)
                    .padding(.bottom, 16)
                }
            }
            
        }
        .safeAreaInset(edge: .bottom) {
            NavigationLink(destination: PayStructureView(viewModel: viewModel)) {
                Text("Next: Select Duration →").font(.system(size: 15, weight: .bold))
                    .frame(maxWidth: .infinity).frame(height: 52)
                    .background(Color.errnoGreen, in: RoundedRectangle(cornerRadius: 12)).foregroundStyle(.white)
            }.padding(16).background(.white)
        }
        .navigationBarHidden(true)
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
