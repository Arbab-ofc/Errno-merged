import SwiftUI

/// Android's schematic Canvas map, deliberately independent of GPS or map SDKs.
struct WorkerLocationMapView: View {
    let locationName: String
    var distanceText = "Location Map Preview"
    var isDarkTheme = true
    @Environment(\.openURL) private var openURL
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var dark: Bool
    @State private var details = true
    @State private var failed = false
    init(locationName: String, distanceText: String = "Location Map Preview", isDarkTheme: Bool = true) {
        self.locationName = locationName; self.distanceText = distanceText; self.isDarkTheme = isDarkTheme
        _dark = State(initialValue: isDarkTheme)
    }
    var body: some View {
        ZStack(alignment: .bottom) {
            TimelineView(.animation(minimumInterval: 1.0 / 30, paused: reduceMotion)) { timeline in
                Canvas { context, size in
                    let road = dark ? Color(hex: "202D3D") : .white
                    context.fill(Path(CGRect(x: 0, y: size.height * 0.4, width: size.width, height: 16)), with: .color(road))
                    for x in [0.35, 0.7] {
                        context.fill(Path(CGRect(x: size.width * x, y: 0, width: 16, height: size.height)), with: .color(road))
                    }
                    var route = Path()
                    route.move(to: CGPoint(x: size.width * 0.15, y: size.height * 0.75))
                    route.addLine(to: CGPoint(x: size.width * 0.35, y: size.height * 0.4))
                    route.addLine(to: CGPoint(x: size.width * 0.7, y: size.height * 0.4))
                    context.stroke(route, with: .color(.errnoGreen), style: StrokeStyle(lineWidth: 5, dash: [8, 6]))
                    let phase = reduceMotion ? 0.0 : timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 1.2) / 1.2
                    let radius = 8 + phase * 8
                    let center = CGPoint(x: size.width * 0.15, y: size.height * 0.75)
                    context.fill(Path(ellipseIn: CGRect(x: center.x - radius, y: center.y - radius, width: radius * 2, height: radius * 2)), with: .color(.blue.opacity((1 - phase) * 0.6)))
                    context.fill(Path(ellipseIn: CGRect(x: center.x - 6, y: center.y - 6, width: 12, height: 12)), with: .color(.blue))
                }
            }.accessibilityHidden(true)
            VStack {
                HStack(alignment: .top) {
                    if details {
                        Text("Schematic route • \(distanceText)").font(.system(size: 10, weight: .semibold))
                            .padding(8).background(.black.opacity(0.75), in: RoundedRectangle(cornerRadius: 10))
                    }
                    Spacer(minLength: 0)
                    Button { dark.toggle() } label: { Image(systemName: dark ? "sun.max.fill" : "moon.fill").frame(width: 36, height: 36) }
                        .background(.black.opacity(0.5), in: Circle()).accessibilityLabel("Toggle map theme")
                    Button { details.toggle() } label: { Image(systemName: "location.circle").frame(width: 36, height: 36) }
                        .background(.black.opacity(0.5), in: Circle()).accessibilityLabel("Toggle route details")
                }
                Spacer()
                Label(locationName, systemImage: "storefront.fill").font(.system(size: 11, weight: .bold))
                    .padding(10).background(Color.errnoGreen, in: Capsule()).padding(.leading, 40)
                Spacer()
                Button {
                    var components = URLComponents(string: "https://www.google.com/maps/search/")
                    components?.queryItems = [URLQueryItem(name: "api", value: "1"), URLQueryItem(name: "query", value: locationName)]
                    if let url = components?.url { openURL(url) { if !$0 { failed = true } } }
                } label: {
                    HStack {
                        Text(locationName).lineLimit(1)
                        Spacer()
                        Label("Open in Maps", systemImage: "arrow.triangle.turn.up.right.diamond")
                    }.font(.system(size: 11)).padding(10).background(.black.opacity(0.7))
                }.buttonStyle(.plain)
            }.padding(.top, 8)
        }.foregroundStyle(.white).frame(height: 200)
            .background(dark ? Color(hex: "131D2A") : Color(hex: "E8ECEF"))
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .alert("Unable to open Maps", isPresented: $failed) { Button("OK", role: .cancel) {} }
    }
}
