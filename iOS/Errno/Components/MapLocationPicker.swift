import SwiftUI
import GoogleMaps
import CoreLocation

enum GoogleMapsConfiguration {
    static var apiKey: String? {
        guard let key = Bundle.main.object(forInfoDictionaryKey: "ERRNO_GOOGLE_MAPS_IOS_API_KEY") as? String,
              !key.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
              !key.contains("YOUR_"), !key.contains("$(") else { return nil }
        return key
    }
}

struct PickedMapLocation { let address: String; let latitude: Double; let longitude: Double }

private struct PhotonSearchResult: Identifiable {
    let label: String; let latitude: Double; let longitude: Double
    var id: String { "\(latitude),\(longitude),\(label)" }
}

struct MapLocationPicker: View {
    @Binding var address: String
    @Binding var latitude: Double?
    @Binding var longitude: Double?
    @State private var query = ""
    @State private var results: [PhotonSearchResult] = []
    @State private var message: String?
    @State private var searchTask: Task<Void, Never>?
    @State private var reverseRequestID = 0
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            TextField("Search address", text: $query).textFieldStyle(.roundedBorder)
                .onChange(of: query) { _, value in search(value) }
            ForEach(results) { result in
                Button(result.label) { select(result) }
                    .font(.system(size: 13)).frame(maxWidth: .infinity, alignment: .leading)
                    .padding(8).background(.white, in: RoundedRectangle(cornerRadius: 8))
            }
            Group {
                if GoogleMapsConfiguration.apiKey != nil {
                    GoogleShopPinMap(address: $address, latitude: $latitude, longitude: $longitude)
                } else {
                    ContentUnavailableView("Map unavailable", systemImage: "map", description: Text("Configure the iOS Google Maps SDK key to select a pin. You can still enter and keep the shop address."))
                }
            }.frame(height: 260).clipShape(RoundedRectangle(cornerRadius: 12))
            HStack {
                Button { useCurrentLocation() } label: { Label("Use my current location", systemImage: "location") }
                Spacer()
                if let latitude, let longitude, latitude.isFinite, longitude.isFinite {
                    Text(String(format: "%.6f, %.6f", latitude, longitude)).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                }
            }
            TextField("Enter address manually", text: $address).textFieldStyle(.roundedBorder)
            Text("Tap or drag the pin to adjust the exact shop location. Your address stays saved if location access is unavailable.")
                .font(.caption).foregroundStyle(.secondary)
            if let message { Text(message).font(.caption).foregroundStyle(.red) }
        }
        .onChange(of: [latitude, longitude]) { _, coordinates in
            guard coordinates.count == 2, let latitude = coordinates[0], let longitude = coordinates[1],
                  latitude.isFinite, longitude.isFinite else { return }
            resolveAddress(latitude: latitude, longitude: longitude)
        }
    }
    private func select(_ result: PhotonSearchResult) {
        address = result.label; latitude = result.latitude; longitude = result.longitude; query = result.label; results = []; message = nil
    }
    private func search(_ value: String) {
        searchTask?.cancel()
        guard value.trimmingCharacters(in: .whitespacesAndNewlines).count >= 3 else { results = []; return }
        searchTask = Task {
            try? await Task.sleep(for: .milliseconds(350))
            guard !Task.isCancelled else { return }
            do {
                let endpoint = Bundle.main.object(forInfoDictionaryKey: "ERRNO_PHOTON_ENDPOINT") as? String ?? "https://photon.komoot.io"
                var components = URLComponents(string: endpoint.trimmingCharacters(in: CharacterSet(charactersIn: "/")) + "/api/")!
                components.queryItems = [URLQueryItem(name: "q", value: value), URLQueryItem(name: "limit", value: "6"), URLQueryItem(name: "lang", value: "en")]
                let (data, _) = try await URLSession.shared.data(from: components.url!)
                let root = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                let features = root?["features"] as? [[String: Any]] ?? []
                let parsed = features.compactMap { feature -> PhotonSearchResult? in
                    guard let geometry = feature["geometry"] as? [String: Any], let coords = geometry["coordinates"] as? [Double], coords.count >= 2 else { return nil }
                    let props = feature["properties"] as? [String: Any] ?? [:]
                    let label = ["name", "street", "housenumber", "district", "city", "state", "country"].compactMap { props[$0] as? String }.filter { !$0.isEmpty }.reduce(into: [String]()) { if !$0.contains($1) { $0.append($1) } }.joined(separator: ", ")
                    guard !label.isEmpty else { return nil }
                    return PhotonSearchResult(label: label, latitude: coords[1], longitude: coords[0])
                }
                guard !Task.isCancelled else { return }
                await MainActor.run { results = parsed; message = nil }
            } catch { await MainActor.run { results = []; message = "Address search is unavailable. Enter the address or place the pin manually." } }
        }
    }
    private func useCurrentLocation() {
        ForegroundSingleLocation.shared.request { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let point): latitude = point.coordinate.latitude; longitude = point.coordinate.longitude; message = nil
                case .failure(let error): message = error.localizedDescription
                }
            }
        }
    }
    private func resolveAddress(latitude: Double, longitude: Double) {
        reverseRequestID += 1
        let requestID = reverseRequestID
        let addressAtStart = address
        Task {
            do {
                try await Task.sleep(for: .milliseconds(500))
                let endpoint = Bundle.main.object(forInfoDictionaryKey: "ERRNO_PHOTON_ENDPOINT") as? String ?? "https://photon.komoot.io"
                var components = URLComponents(string: endpoint.trimmingCharacters(in: CharacterSet(charactersIn: "/")) + "/reverse")!
                components.queryItems = [URLQueryItem(name: "lat", value: String(latitude)), URLQueryItem(name: "lon", value: String(longitude))]
                let (data, response) = try await URLSession.shared.data(from: components.url!)
                guard (response as? HTTPURLResponse)?.statusCode == 200,
                      let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let feature = (root["features"] as? [[String: Any]])?.first else { throw URLError(.badServerResponse) }
                let props = feature["properties"] as? [String: Any] ?? [:]
                let label = ["name", "housenumber", "street", "district", "locality", "city", "state", "postcode", "country"]
                    .compactMap { props[$0] as? String }.filter { !$0.isEmpty }
                    .reduce(into: [String]()) { if !$0.contains($1) { $0.append($1) } }.joined(separator: ", ")
                await MainActor.run {
                    guard requestID == reverseRequestID, self.latitude == latitude, self.longitude == longitude,
                          address == addressAtStart else { return }
                    if !label.isEmpty { address = label; message = nil }
                }
            } catch {
                await MainActor.run {
                    guard requestID == reverseRequestID, self.latitude == latitude, self.longitude == longitude,
                          address == addressAtStart else { return }
                    message = "Address lookup is unavailable. Edit the address manually if needed."
                }
            }
        }
    }
}

private struct GoogleShopPinMap: UIViewRepresentable {
    @Binding var address: String
    @Binding var latitude: Double?
    @Binding var longitude: Double?
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeUIView(context: Context) -> GMSMapView {
        let initial = validPoint(latitude, longitude) ?? CLLocationCoordinate2D(latitude: 28.6139, longitude: 77.2090)
        let options = GMSMapViewOptions(); options.camera = GMSCameraPosition.camera(withTarget: initial, zoom: validPoint(latitude, longitude) == nil ? 10 : 16)
        let map = GMSMapView(options: options)
        map.delegate = context.coordinator; map.settings.compassButton = true; map.settings.myLocationButton = false
        context.coordinator.map = map; context.coordinator.updatePin()
        return map
    }
    func updateUIView(_ map: GMSMapView, context: Context) {
        context.coordinator.parent = self
        context.coordinator.updatePin()
    }
    private func validPoint(_ latitude: Double?, _ longitude: Double?) -> CLLocationCoordinate2D? {
        guard let latitude, let longitude, latitude.isFinite, longitude.isFinite, (-90...90).contains(latitude), (-180...180).contains(longitude) else { return nil }
        return CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }
    final class Coordinator: NSObject, GMSMapViewDelegate {
        var parent: GoogleShopPinMap
        weak var map: GMSMapView?
        var marker: GMSMarker?
        var cameraTarget: CLLocationCoordinate2D?
        var lastAddress: String?
        init(_ parent: GoogleShopPinMap) { self.parent = parent }
        func updatePin() {
            guard let map, let point = parent.validPoint(parent.latitude, parent.longitude) else { marker?.map = nil; marker = nil; return }
            if let lastAddress, lastAddress != parent.address { cameraTarget = cameraTarget ?? point }
            self.lastAddress = parent.address
            if let marker { marker.position = point; marker.title = "Shop location"; marker.snippet = parent.address }
            else { let marker = GMSMarker(position: point); marker.title = "Shop location"; marker.snippet = parent.address; marker.isDraggable = true; marker.map = map; self.marker = marker }
            if let target = cameraTarget, target.latitude != point.latitude || target.longitude != point.longitude {
                map.animate(to: GMSCameraPosition.camera(withTarget: point, zoom: max(map.camera.zoom, 16)))
            }
            cameraTarget = point
        }
        func mapView(_ mapView: GMSMapView, didTapAt coordinate: CLLocationCoordinate2D) { set(coordinate) }
        func mapView(_ mapView: GMSMapView, didEndDragging marker: GMSMarker) { set(marker.position) }
        private func set(_ point: CLLocationCoordinate2D) {
            cameraTarget = point
            parent.latitude = point.latitude; parent.longitude = point.longitude
            marker?.position = point; marker?.snippet = parent.address
        }
    }
}

@MainActor final class ForegroundSingleLocation: NSObject, CLLocationManagerDelegate {
    static let shared = ForegroundSingleLocation()
    private let manager = CLLocationManager()
    private var completion: ((Result<CLLocation, Error>) -> Void)?
    func request(_ completion: @escaping (Result<CLLocation, Error>) -> Void) {
        self.completion = completion; manager.delegate = self; manager.desiredAccuracy = kCLLocationAccuracyBest
        guard CLLocationManager.locationServicesEnabled() else {
            completion(.failure(LocationRequestError("Location Services are off. Select a pin or enter the address manually."))); self.completion = nil; return
        }
        switch manager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse: manager.requestLocation()
        case .notDetermined: manager.requestWhenInUseAuthorization()
        case .denied, .restricted: completion(.failure(LocationRequestError("Location permission is denied. Select a pin or enter the address manually."))); self.completion = nil
        @unknown default: completion(.failure(LocationRequestError("Location access is unavailable."))); self.completion = nil
        }
    }
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        if manager.authorizationStatus == .authorizedWhenInUse || manager.authorizationStatus == .authorizedAlways { manager.requestLocation() }
        else if manager.authorizationStatus == .denied || manager.authorizationStatus == .restricted { completion?(.failure(LocationRequestError("Location permission is denied. Select a pin or enter the address manually."))); completion = nil }
    }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last, Date().timeIntervalSince(location.timestamp) < 120 else { completion?(.failure(LocationRequestError("No recent GPS fix. Select a pin or enter the address manually."))); completion = nil; return }
        completion?(.success(location)); completion = nil
    }
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) { completion?(.failure(LocationRequestError("GPS is unavailable. Select a pin or enter the address manually."))); completion = nil }
}
struct LocationRequestError: LocalizedError { let message: String; init(_ message: String) { self.message = message }; var errorDescription: String? { message } }
