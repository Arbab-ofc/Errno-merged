import SwiftUI

struct PreviewJobView: View {
    @Bindable var viewModel: PostJobViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var success = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack { Text(viewModel.category.rawValue).font(.system(size: 20, weight: .bold)); Spacer(); if viewModel.category.isDelivery { StatusBadge(text: "Delivery Job") } }
                Label(viewModel.location, systemImage: "mappin.and.ellipse").font(.system(size: 14)).foregroundStyle(.gray)
                Text("Scheduled: \(viewModel.scheduledStartTime.formatted(date: .abbreviated, time: .omitted)) at \(viewModel.selectedTime):00").font(.system(size: 13))
                if viewModel.category.isDelivery {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("📦 Pickup: \(viewModel.pickupLocation)")
                        Text("📍 Drop: \(viewModel.dropLocation)")
                    }.font(.system(size: 13, weight: .bold)).padding(12).background(Color.errnoBackground, in: RoundedRectangle(cornerRadius: 10))
                }
                WorkerLocationMapView(locationName: viewModel.category.isDelivery ? viewModel.pickupLocation : viewModel.location, isDarkTheme: false)
                Text(viewModel.description).font(.system(size: 14)).foregroundStyle(Color.errnoTextSecondary)
                Text("Fixed Time Options & Pay Structure").font(.system(size: 15, weight: .bold))
                HStack { Text("\(Int(viewModel.estimatedDurationHours)) Hours Limit"); Spacer(); Text("₹\(viewModel.payAmountString)").bold() }.font(.system(size: 14))
                MockNotice(text: "Local demo • This post is visible only inside this app session.")
                if let error = viewModel.errorMessage { Text(error).foregroundStyle(Color.errnoError) }
            }.marketplaceCard(padding: 20).padding(20).frame(maxWidth: 800).frame(maxWidth: .infinity)
        }.marketplacePage().navigationTitle("Preview Job").navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
            .navigationBarBackButtonHidden(viewModel.isSubmitting || success)
            .safeAreaInset(edge: .bottom) {
                HStack(spacing: 12) {
                    PrimaryButton(title: "Edit", style: .secondary, isDisabled: viewModel.isSubmitting) { dismiss() }
                    PrimaryButton(title: "Post Job", style: .dark, isLoading: viewModel.isSubmitting) {
                        viewModel.submitJob { success = true }
                    }
                }.padding(16).background(.white)
            }
            .navigationDestination(isPresented: $success) { PostJobSuccessView(viewModel: viewModel) }
    }
}
