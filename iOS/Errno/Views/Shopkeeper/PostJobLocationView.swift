import SwiftUI

struct PostJobLocationView: View {
    @Bindable var viewModel: PostJobViewModel
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(viewModel.category.isDelivery ? "Delivery Route Locations" : "Shop / Work Address")
                    .font(.system(size: 16, weight: .bold))
                if viewModel.category.isDelivery {
                    ManualAddressField(title: "Pickup Location", text: $viewModel.pickupLocation)
                    ManualAddressField(title: "Customer Drop Location", text: $viewModel.dropLocation)
                } else {
                    ManualAddressField(title: "Shop / Work Address", text: $viewModel.location)
                }
                Text("Enter a complete address. Address suggestions and GPS pin placement are unavailable because ERRNO has no configured geocoder or location permission flow.")
                    .font(.system(size: 12)).foregroundStyle(Color.errnoTextSecondary)
                if !viewModel.isLocationValid {
                    Text(viewModel.category.isDelivery ? "Pickup and drop-off locations are required." : "Work address is required.")
                        .font(.system(size: 12, weight: .medium)).foregroundStyle(Color.errnoError)
                }
            }.padding(20).frame(maxWidth: 800).frame(maxWidth: .infinity)
        }.marketplacePage()
            .navigationTitle("Post a New Job").navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
            .safeAreaInset(edge: .top) { PostingProgress(step: 3) }
            .safeAreaInset(edge: .bottom) {
                HStack(spacing: 12) {
                    PrimaryButton(title: "← Back", style: .secondary) { dismiss() }
                    NavigationLink(destination: PreviewJobView(viewModel: viewModel)) {
                        Text("Preview & Post →").font(.system(size: 15, weight: .bold)).frame(maxWidth: .infinity).frame(height: 52)
                            .background(Color.errnoGreen, in: RoundedRectangle(cornerRadius: 12)).foregroundStyle(.white)
                    }.disabled(!viewModel.isLocationValid).opacity(viewModel.isLocationValid ? 1 : 0.55)
                }.padding(16).background(.white)
            }
    }
}

struct PostingProgress: View {
    let step: Int
    var body: some View {
        HStack(spacing: 8) {
            ForEach(Array(["1. Details", "2. Duration", "3. Location"].enumerated()), id: \.offset) { index, title in
                Text(title).font(.system(size: 12, weight: .bold)).frame(maxWidth: .infinity).padding(.vertical, 8)
                    .foregroundStyle(index < step ? Color.errnoGreen : .gray)
                    .background(index < step ? Color.errnoGreenLight : Color(hex: "F0F0F0"), in: RoundedRectangle(cornerRadius: 8))
            }
        }.padding(.horizontal, 20).padding(.vertical, 12).background(.white)
    }
}

struct ManualAddressField: View {
    let title: String
    @Binding var text: String
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.system(size: 13, weight: .medium))
            HStack {
                Image(systemName: "mappin.and.ellipse").foregroundStyle(.gray)
                TextField(title, text: $text)
                if !text.isEmpty { Button { text = "" } label: { Image(systemName: "xmark.circle").frame(width: 44, height: 44) }.accessibilityLabel("Clear \(title)") }
            }.padding(.horizontal, 12).frame(minHeight: 52)
                .background(.white, in: RoundedRectangle(cornerRadius: 10))
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.errnoStroke))
            Text("Manual address entry").font(.system(size: 10)).foregroundStyle(.gray)
        }
    }
}
