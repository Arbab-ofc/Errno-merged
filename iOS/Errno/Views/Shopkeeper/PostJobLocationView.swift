import SwiftUI

struct PostJobLocationView: View {
    @Bindable var viewModel: PostJobViewModel
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(viewModel.category.isDelivery ? "Delivery Route Locations" : "Shop Location & Map Pin")
                    .font(.system(size: 16, weight: .bold))
                if viewModel.category.isDelivery {
                    LocationAutocompleteField(title: "Pickup Location", text: $viewModel.pickupLocation)
                    LocationAutocompleteField(title: "Customer Drop Location", text: $viewModel.dropLocation)
                } else {
                    LocationAutocompleteField(title: "Shop / Work Address", text: $viewModel.location)
                }
                Text("Interactive Location Map Pin:").font(.system(size: 13, weight: .bold))
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack {
                        ForEach(["🏬 Shop Main Gate, Okhla", "📍 Store Delivery Bay, Block B", "🚇 Okhla Metro Exit 2", "🏢 Central Market Hub"], id: \.self) { value in
                            Button(value) {
                                if viewModel.category.isDelivery { viewModel.pickupLocation = value }
                                else { viewModel.location = value }
                            }.font(.system(size: 11, weight: .bold)).padding(8)
                                .background(Color.errnoGreenLight, in: Capsule())
                        }
                    }
                }
                WorkerLocationMapView(locationName: viewModel.category.isDelivery ? viewModel.pickupLocation : viewModel.location, isDarkTheme: false)
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
                    }
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

struct LocationAutocompleteField: View {
    let title: String
    @Binding var text: String
    @State private var editing = false
    static let locations = [
        "Okhla Market Store #12, Block B, New Delhi", "Okhla Industrial Area Phase 1, New Delhi",
        "Okhla Industrial Estate Phase 3, Delhi", "Okhla Phase 3 Metro Station Exit 2",
        "Okhla Main Market, Jamia Nagar, New Delhi", "Sector 18 Noida Market Area, UP",
        "Sector 15 Noida Metro Station, UP", "Sector 62 Noida IT Park, UP",
        "Connaught Place Central Market, New Delhi", "Lajpat Nagar Central Market, New Delhi",
        "Karol Bagh Wholesale Market, New Delhi", "Chandni Chowk Wholesale Store, Delhi",
        "Nehru Place Electronics Hub, Delhi", "Saket Select Citywalk Area, New Delhi", "South Extension Market Part 1, Delhi"
    ]
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.system(size: 13, weight: .medium))
            HStack {
                Image(systemName: "mappin.and.ellipse").foregroundStyle(.gray)
                TextField(title, text: $text, onEditingChanged: { editing = $0 })
                if !text.isEmpty { Button { text = "" } label: { Image(systemName: "xmark.circle").frame(width: 44, height: 44) }.accessibilityLabel("Clear \(title)") }
            }.padding(.horizontal, 12).frame(minHeight: 52)
                .background(.white, in: RoundedRectangle(cornerRadius: 10))
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.errnoStroke))
            if editing && text.count >= 2 {
                ForEach(Self.locations.filter { $0.localizedCaseInsensitiveContains(text) }, id: \.self) { suggestion in
                    Button(suggestion) { text = suggestion; editing = false }.font(.system(size: 13)).padding(.vertical, 4)
                }
            }
            Button("📍 Use Current GPS Location") { text = Self.locations[0]; editing = false }
                .font(.system(size: 11, weight: .bold))
            Text("Demo location preset • GPS is not accessed").font(.system(size: 10)).foregroundStyle(.gray)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack {
                    ForEach(["Okhla Market #12", "Sector 18 Noida", "Nehru Place Hub", "Connaught Place", "Lajpat Nagar Market"], id: \.self) { chip in
                        Button(chip) { text = "\(chip), Delhi NCR" }.font(.system(size: 11)).padding(8)
                            .background(.white, in: Capsule()).overlay(Capsule().stroke(Color.errnoStroke))
                    }
                }
            }
        }
    }
}
