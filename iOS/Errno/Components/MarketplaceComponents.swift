import SwiftUI

extension View {
    func marketplaceCard(padding: CGFloat = 16, radius: CGFloat = 16) -> some View {
        self.padding(padding).frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.white, in: RoundedRectangle(cornerRadius: radius))
            .shadow(color: .black.opacity(0.04), radius: 2, y: 1)
    }
    func marketplacePage(dark: Bool = false) -> some View {
        self.frame(maxWidth: .infinity, maxHeight: .infinity)
            .background((dark ? Color.errnoNavy : Color(hex: "F9FAFB")).ignoresSafeArea())
    }
}

struct MarketplaceHeader: View {
    let title: String
    var dark = false
    var back: (() -> Void)?
    var body: some View {
        HStack(spacing: 12) {
            if let back {
                Button(action: back) { Image(systemName: "arrow.left").frame(width: 44, height: 44) }
                    .accessibilityLabel("Back")
            }
            Text(title).font(.system(size: 18, weight: .bold))
            Spacer(minLength: 0)
        }
        .foregroundStyle(dark ? .white : Color.errnoTextPrimary)
        .padding(.horizontal, 20).frame(minHeight: 56)
        .background(dark ? Color.errnoNavy : .white)
    }
}

struct StatusBadge: View {
    let text: String
    var body: some View {
        Text(text).font(.system(size: 11, weight: .bold))
            .foregroundStyle(Color.errnoGreen).padding(.horizontal, 10).padding(.vertical, 4)
            .background(Color.errnoGreenLight, in: Capsule())
    }
}

struct MarketplaceEmptyState: View {
    let title: String
    let message: String
    var dark = false
    var body: some View {
        VStack(spacing: 12) {
            ErrnoLogo(size: .large).saturation(0).opacity(0.55)
            Text(title).font(.system(size: 16, weight: .bold))
            Text(message).font(.system(size: 12)).foregroundStyle(dark ? Color.white.opacity(0.7) : .errnoTextSecondary)
                .multilineTextAlignment(.center)
        }.padding(28).frame(maxWidth: .infinity)
            .foregroundStyle(dark ? .white : .errnoTextPrimary)
            .background(dark ? Color(hex: "131D2A") : .white, in: RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(dark ? Color(hex: "202D3D") : .errnoStroke))
    }
}

struct MarketplaceFilters: View {
    let labels: [String]
    @Binding var selection: Int
    var dark = false
    var body: some View {
        HStack(spacing: 0) {
            ForEach(labels.indices, id: \.self) { index in
                Button { selection = index } label: {
                    VStack(spacing: 12) {
                        Text(labels[index]).font(.system(size: 13, weight: selection == index ? .bold : .medium))
                            .foregroundStyle(selection == index ? Color.errnoGreen : .gray)
                        Rectangle().fill(selection == index ? Color.errnoGreen : .clear).frame(height: 3)
                    }.frame(maxWidth: .infinity).padding(.top, 12)
                }.buttonStyle(.plain).accessibilityAddTraits(selection == index ? .isSelected : [])
            }
        }.background(dark ? Color.errnoNavy : .white)
    }
}

struct MarketplaceBottomBar: View {
    let titles: [String]
    let icons: [String]
    @Binding var selection: Int
    var dark = false
    var body: some View {
        HStack(spacing: 0) {
            ForEach(titles.indices, id: \.self) { index in
                Button { selection = index } label: {
                    VStack(spacing: 5) {
                        Image(systemName: icons[index]).font(.system(size: 22))
                        Text(titles[index]).font(.system(size: 11))
                    }.foregroundStyle(selection == index ? Color.errnoGreen : .gray)
                        .frame(maxWidth: .infinity).frame(minHeight: 64)
                }.buttonStyle(.plain).accessibilityAddTraits(selection == index ? .isSelected : [])
            }
        }.background(dark ? Color(hex: "0E1726") : .white)
    }
}

struct RatingDialog: View {
    let title: String
    let target: String
    let submit: (Int, String) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var stars = 5
    @State private var comment = ""
    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                Text("Rate \(target) after shift completion").font(.system(size: 12)).foregroundStyle(.gray)
                HStack(spacing: 8) {
                    ForEach(1...5, id: \.self) { value in
                        Button { stars = value } label: {
                            Image(systemName: value <= stars ? "star.fill" : "star")
                                .font(.system(size: 30)).foregroundStyle(Color(hex: "FFB300"))
                                .frame(minWidth: 44, minHeight: 44)
                        }.accessibilityLabel("\(value) stars")
                    }
                }
                TextField("Add feedback review notes...", text: $comment, axis: .vertical)
                    .textFieldStyle(.roundedBorder)
                PrimaryButton(title: "Submit Rating", style: .dark) { submit(stars, comment); dismiss() }
                Spacer()
            }.padding(20).navigationTitle(title).navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } } }
        }.presentationDetents([.medium, .large])
    }
}

struct MockNotice: View {
    let text: String
    var body: some View {
        Text(text).font(.system(size: 11)).foregroundStyle(Color.errnoTextSecondary)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct ContactActions: View {
    let phone: String
    var email: String?
    @Environment(\.openURL) private var openURL
    @State private var failed = false
    private func open(_ value: String) {
        guard let url = URL(string: value) else { failed = true; return }
        openURL(url) { accepted in if !accepted { failed = true } }
    }
    var body: some View {
        VStack(spacing: 10) {
            PrimaryButton(title: "Call \(phone)", icon: "phone.fill", style: .dark) { open("tel:\(phone)") }
            PrimaryButton(title: "WhatsApp Chat", style: .secondary) {
                open("https://wa.me/\(phone.filter(\.isNumber))")
            }
            if let email { Button("Email \(email)") { open("mailto:\(email)") } }
        }.alert("Unable to open contact app", isPresented: $failed) {
            Button("OK", role: .cancel) {}
        } message: { Text("Contact \(phone) directly, or try on a device with a supported app.") }
    }
}
