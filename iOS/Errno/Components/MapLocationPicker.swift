import SwiftUI
import WebKit
import CoreLocation

struct PickedMapLocation { let address: String; let latitude: Double; let longitude: Double }

struct MapLocationPicker: View {
    @Binding var address: String
    @Binding var latitude: Double?
    @Binding var longitude: Double?
    @State private var query = ""
    @State private var results: [SearchResult] = []
    @State private var webView: WKWebView?
    @State private var message: String?
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            TextField("Search address", text: $query).textFieldStyle(.roundedBorder).onChange(of: query) { _, q in
                webView?.evaluateJavaScript("window.ErrnoMapAPI&&ErrnoMapAPI.search(\(Self.js(q)))")
            }
            ForEach(results) { item in
                Button(item.label) { choose(item) }.font(.system(size: 13)).frame(maxWidth: .infinity, alignment: .leading).padding(8).background(.white, in: RoundedRectangle(cornerRadius: 8))
            }
            MapWebView(address: address, latitude: latitude, longitude: longitude, onReady: { webView = $0 }, onSelection: { selection in
                address = selection.address; latitude = selection.latitude; longitude = selection.longitude
            }, onResults: { results = $0; message = nil }, onError: { message = $0 })
                .frame(height: 260).clipShape(RoundedRectangle(cornerRadius: 12))
            HStack {
                Button { locate() } label: { Label("Use my current location", systemImage: "location") }
                Spacer()
                Text("Map pin or manual address").font(.caption).foregroundStyle(.secondary)
            }
            if let message { Text(message).font(.caption).foregroundStyle(.red) }
            TextField("Enter address manually", text: $address).textFieldStyle(.roundedBorder)
        }
    }
    private func choose(_ item: SearchResult) {
        address = item.label; latitude = item.latitude; longitude = item.longitude; results = []
        webView?.evaluateJavaScript("ErrnoMapAPI.select({latitude:\(item.latitude),longitude:\(item.longitude),label:\(Self.js(item.label))})")
    }
    private func locate() {
        LocationPermission.shared.requestLocation { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let loc):
                    latitude=loc.coordinate.latitude; longitude=loc.coordinate.longitude
                    webView?.evaluateJavaScript("ErrnoMapAPI.setLocation(\(loc.coordinate.latitude),\(loc.coordinate.longitude),'Current location',true)")
                case .failure(let error): message=error.description
                }
            }
        }
    }
    fileprivate static func js(_ value: String) -> String { let data = try? JSONSerialization.data(withJSONObject: [value]); let array = data.flatMap { String(data: $0, encoding: .utf8) } ?? "[\"\"]"; return String(array.dropFirst().dropLast()) }
}

private struct SearchResult: Identifiable { let label: String; let latitude: Double; let longitude: Double; var id: String { "\(latitude),\(longitude),\(label)" } }
private struct MapWebView: UIViewRepresentable {
    let address: String; let latitude: Double?; let longitude: Double?
    let onReady: (WKWebView) -> Void; let onSelection: (PickedMapLocation) -> Void; let onResults: ([SearchResult]) -> Void; let onError: (String) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration(); config.userContentController.add(context.coordinator, name: "errnoMap")
        let photon = Bundle.main.object(forInfoDictionaryKey: "ERRNO_PHOTON_ENDPOINT") as? String ?? "https://photon.komoot.io"
        let osrm = Bundle.main.object(forInfoDictionaryKey: "ERRNO_OSRM_ENDPOINT") as? String ?? "https://router.project-osrm.org/route/v1/driving"
        let tiles = Bundle.main.object(forInfoDictionaryKey: "ERRNO_TILE_ENDPOINT") as? String ?? "https://tiles.openfreemap.org/planet"
        let style = Bundle.main.object(forInfoDictionaryKey: "ERRNO_MAP_STYLE_URL") as? String ?? "https://tiles.openfreemap.org/styles/liberty"
        config.userContentController.addUserScript(WKUserScript(source: "window.ERRNO_PHOTON_ENDPOINT=\(MapLocationPicker.js(photon));window.ERRNO_OSRM_ENDPOINT=\(MapLocationPicker.js(osrm));window.ERRNO_TILE_ENDPOINT=\(MapLocationPicker.js(tiles));window.ERRNO_MAP_STYLE_URL=\(MapLocationPicker.js(style));", injectionTime: .atDocumentStart, forMainFrameOnly: true))
        let view = WKWebView(frame: .zero, configuration: config); view.scrollView.isScrollEnabled = false; view.navigationDelegate = context.coordinator
        if let file = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: nil) { view.loadFileURL(file, allowingReadAccessTo: file.deletingLastPathComponent()) } else { onError("Map module is missing. Enter the address manually.") }
        onReady(view); return view
    }
    func updateUIView(_ uiView: WKWebView, context: Context) {
        guard let lat=latitude, let lng=longitude else { return }
        uiView.evaluateJavaScript("ErrnoMapAPI&&ErrnoMapAPI.setLocation(\(lat),\(lng),\(MapLocationPicker.js(address)))")
    }
    final class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
        let parent: MapWebView; init(_ parent: MapWebView) { self.parent=parent }
        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard let obj=message.body as? [String:Any], let type=obj["type"] as? String else { return }
            if type == "selection", let lat=obj["latitude"] as? Double, let lng=obj["longitude"] as? Double { parent.onSelection(PickedMapLocation(address: obj["address"] as? String ?? "", latitude: lat, longitude: lng)) }
            if type == "results" { let rows=obj["items"] as? [[String:Any]] ?? []; parent.onResults(rows.compactMap { r in guard let label=r["label"] as? String, let lat=r["latitude"] as? Double, let lng=r["longitude"] as? Double else{return nil}; return SearchResult(label: label,latitude: lat,longitude: lng) }); if let error=obj["error"] as? String { parent.onError(error) } }
            if type == "error" { parent.onError("Map tiles could not be loaded. Enter the address manually.") }
        }
        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { parent.onError("Map failed to load. Enter the address manually.") }
    }
}
private struct LocationPermissionError: Error, CustomStringConvertible { let description: String }
private final class LocationPermission: NSObject, CLLocationManagerDelegate {
    static let shared = LocationPermission()
    private let manager = CLLocationManager()
    private var completion: ((Result<CLLocation,LocationPermissionError>)->Void)?
    func requestLocation(_ completion: @escaping (Result<CLLocation,LocationPermissionError>)->Void) {
        self.completion=completion; manager.delegate=self; manager.desiredAccuracy=kCLLocationAccuracyBest
        switch manager.authorizationStatus {
        case .authorizedAlways,.authorizedWhenInUse: manager.requestLocation()
        case .notDetermined: manager.requestWhenInUseAuthorization()
        case .denied,.restricted: completion(.failure(LocationPermissionError(description:"Location permission is denied. Select a pin or enter the address manually."))); self.completion=nil
        @unknown default: completion(.failure(LocationPermissionError(description:"Location access is unavailable."))); self.completion=nil
        }
    }
    func locationManager(_ manager: CLLocationManager, didChangeAuthorization status: CLAuthorizationStatus) {
        if status == .authorizedWhenInUse || status == .authorizedAlways { manager.requestLocation() }
        else if status == .denied || status == .restricted { completion?(.failure(LocationPermissionError(description:"Location permission is denied. Select a pin or enter the address manually."))); completion=nil }
    }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let loc=locations.last, Date().timeIntervalSince(loc.timestamp)<120 else { completion?(.failure(LocationPermissionError(description:"No fresh GPS fix. Select a pin or enter the address manually."))); completion=nil; return }
        completion?(.success(loc)); completion=nil
    }
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) { completion?(.failure(LocationPermissionError(description:"Unable to get a fresh GPS fix. Select a pin or enter the address manually."))); completion=nil }
}
