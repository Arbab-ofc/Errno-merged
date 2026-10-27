// PostJobSuccessView.swift
// Errno — Views/Shopkeeper
//
// Matches Android "Job Posted Successfully" screen.

import SwiftUI

struct PostJobSuccessView: View {
    var viewModel: PostJobViewModel
    @Environment(AppRouter.self) private var router
    
    var body: some View {
        ZStack {
            Color.errnoBackground.ignoresSafeArea()
            
            ScrollView { VStack(spacing: Spacing.xl) {
                Spacer()
                
                // Success Icon & Text
                VStack(spacing: Spacing.md) {
                    ZStack {
                        Circle()
                            .fill(Color.errnoGreen)
                            .frame(width: 80, height: 80)
                        Image(systemName: "checkmark")
                            .font(.system(size: 40, weight: .bold))
                            .foregroundStyle(.white)
                    }
                    
                    VStack(spacing: 8) {
                        Text("Job Posted Successfully!")
                            .font(.system(size: 24, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                        Text("Your job is live now. Nearby workers\nwill see it and can accept.")
                            .errnoBodyMedium(color: .errnoTextSecondary)
                            .multilineTextAlignment(.center)
                    }
                }
                
                // Job Details Card
                VStack(alignment: .leading, spacing: Spacing.md) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(viewModel.title.isEmpty ? viewModel.category.rawValue : viewModel.title)
                            .font(.system(size: 18, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                        
                        HStack(spacing: 4) {
                            Image(systemName: "mappin.and.ellipse")
                                .font(.system(size: 12))
                            Text(viewModel.postedJob?.locationLabel ?? viewModel.location)
                                .font(.system(size: 14))
                        }
                        .foregroundStyle(Color.errnoTextSecondary)
                        
                        Text("Posted just now")
                            .font(.system(size: 12))
                            .foregroundStyle(Color.errnoTextSecondary)
                            .padding(.top, 4)
                    }
                    
                    Divider().background(Color.errnoStroke)
                    
                    VStack(alignment: .leading, spacing: Spacing.sm) {
                        Text("Pay Structure")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundStyle(Color.errnoTextPrimary)
                        
                        HStack {
                            Text("\(Int(viewModel.estimatedDurationHours)) Hours")
                                .font(.system(size: 14))
                                .foregroundStyle(Color.errnoTextSecondary)
                            Spacer()
                            Text("₹\(viewModel.payAmountString)")
                                .font(.system(size: 16, weight: .bold))
                                .foregroundStyle(Color.errnoTextPrimary)
                        }
                    }
                }
                .padding(Spacing.lg)
                .background(Color.errnoSurface)
                .clipShape(RoundedRectangle(cornerRadius: Radius.lg))
                .overlay(
                    RoundedRectangle(cornerRadius: Radius.lg)
                        .strokeBorder(Color.errnoStroke, lineWidth: 1)
                )
                .padding(.horizontal, Spacing.lg)
                
                Spacer()
                
                // Actions
                VStack(spacing: Spacing.md) {
                    Button(action: {
                        router.postingPresented = false
                        router.shopkeeperTab = 1
                    }) {
                        Text("Go to My Jobs")
                            .font(.system(size: 16, weight: .bold))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(Color.errnoGreen)
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: Radius.md))
                    }
                    
                    ShareLink(item: "\(viewModel.postedJob?.title ?? viewModel.title) • \(viewModel.postedJob?.locationLabel ?? viewModel.location) • ₹\(viewModel.payAmountString) (local demo)") {
                        Text("Share Job")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(Color.errnoGreen)
                            .padding(.vertical, 8)
                    }
                }
                .padding(.horizontal, Spacing.lg)
                .padding(.bottom, Spacing.xl)
            }
        }}
        .navigationBarHidden(true)
        .navigationBarBackButtonHidden(true)
    }
}
