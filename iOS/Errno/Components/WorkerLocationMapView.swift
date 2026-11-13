import SwiftUI
import GoogleMaps
import CoreLocation
import Combine

/// Requests foreground location only while the assigned job detail is visible.
struct WorkerForegroundLocationPublisher: View {
    var jobID: String? = nil
    var available = false
    @StateObject private var publisher = ForegroundWorkerLocationManager()
    var body: some View {
        Text(publisher.message).font(.caption).foregroundStyle(.secondary)
            .onAppear { publisher.start(jobID: jobID, available: available) }
            .onDisappear { publisher.stop() }
    }
}

@MainActor private final class ForegroundWorkerLocationManager: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var message = "Sharing foreground location for this active job"
    private let manager = CLLocationManager()
    private var jobID: String?
    private var isAvailable = false
    private var lastSent = Date.distantPast
    override init() { super.init(); manager.delegate = self; manager.desiredAccuracy = kCLLocationAccuracyHundredMeters; manager.distanceFilter = 30 }
    func start(jobID: String?, available: Bool = false) { self.jobID = jobID; isAvailable = available; manager.requestWhenInUseAuthorization(); if manager.authorizationStatus == .authorizedWhenInUse || manager.authorizationStatus == .authorizedAlways { manager.startUpdatingLocation() } }
    func stop() { manager.stopUpdatingLocation(); jobID = nil; isAvailable = false }
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        if manager.authorizationStatus == .authorizedWhenInUse || manager.authorizationStatus == .authorizedAlways { manager.startUpdatingLocation() }
        else if manager.authorizationStatus == .denied || manager.authorizationStatus == .restricted { message = "Location permission denied. Live tracking is unavailable." }
    }
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard jobID != nil || isAvailable, let location = locations.last, abs(location.timestamp.timeIntervalSinceNow) < 120, location.horizontalAccuracy >= 0, location.horizontalAccuracy <= 250, Date().timeIntervalSince(lastSent) >= (jobID == nil ? 30 : 8) else { return }
        lastSent = Date(); message = "Updating worker location…"
        Task { do {
            let api = try AppDependencies.backendRepository()
            if let id = jobID { try await api.sendAssignedWorkerLocation(jobID: id, latitude: location.coordinate.latitude, longitude: location.coordinate.longitude) }
            else { try await api.sendAvailableWorkerLocation(latitude: location.coordinate.latitude, longitude: location.coordinate.longitude) }
            message = "Worker location updated"
        } catch { message = "Location update pending network" } }
    }
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) { message = "GPS unavailable. Check location services." }
}

struct WorkerLocationMapView: View {
    let locationName: String
    var distanceText = "Shop location"
    var isDarkTheme = true
    var mapHeight: CGFloat = 200
    var latitude: Double? = nil
    var longitude: Double? = nil
    var nearbyWorkers: [NearbyWorkerLocation] = []
    var workerLatitude: Double? = nil
    var workerLongitude: Double? = nil
    @State private var showUserLocation = false
    @State private var mapLoaded = false
    @State private var mapToken = UUID()
    @State private var message: String?
    @State private var failure: String?
    @State private var currentLocation: CLLocationCoordinate2D?
    var body: some View {
        VStack(spacing: 0) {
            Group {
                if GoogleMapsConfiguration.apiKey != nil && validDestination {
                    ZStack {
                        NativeJobMap(latitude: latitude, longitude: longitude, locationName: locationName, nearbyWorkers: nearbyWorkers,
                                    workerLatitude: workerLatitude, workerLongitude: workerLongitude, showUserLocation: showUserLocation,
                                    currentLocation: currentLocation, distanceText: distanceText,
                                    mapToken: mapToken, mapLoaded: $mapLoaded, failure: $failure)
                        if !mapLoaded { ProgressView().padding(12).background(.regularMaterial, in: Capsule()) }
                    }
                } else {
                    ContentUnavailableView("Map unavailable", systemImage: "map", description: Text(locationName.isEmpty ? "Shop coordinates are unavailable." : locationName))
                }
            }.frame(height: mapHeight)
            HStack {
                Button("Recenter shop", systemImage: "scope") { NotificationCenter.default.post(name: .errnoRecenterShopMap, object: mapToken) }
                    .disabled(!validDestination)
                Spacer()
                Button("My location", systemImage: "location") { requestForegroundLocation() }
            }.font(.caption.weight(.semibold)).padding(.horizontal, 10).padding(.vertical, 7)
            if let message { Text(message).font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 10) }
            if let failure { Text(failure).font(.caption).foregroundStyle(Color.errnoError).frame(maxWidth: .infinity, alignment: .leading).padding(.horizontal, 10) }
            if !validDestination { Text("Shop coordinates are unavailable. Use the saved address.").font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading).padding(10) }
        }.background(Color.white).clipShape(RoundedRectangle(cornerRadius: 14))
            .task { try? await Task.sleep(for: .seconds(15)); if !mapLoaded && GoogleMapsConfiguration.apiKey != nil { failure = "Map is taking longer to load. Check your connection or API key." } }
    }
    private var validDestination: Bool { guard let latitude, let longitude else { return false }; return latitude.isFinite && longitude.isFinite && (-90...90).contains(latitude) && (-180...180).contains(longitude) }
    private func requestForegroundLocation() {
        ForegroundSingleLocation.shared.request { result in
            DispatchQueue.main.async {
                switch result {
                case .success(let location): showUserLocation = true; currentLocation = location.coordinate; message = nil
                case .failure(let error): showUserLocation = false; message = error.localizedDescription
                }
            }
        }
    }
}

private extension Notification.Name { static let errnoRecenterShopMap = Notification.Name("errno.recenter-shop-map") }

private struct NativeJobMap: UIViewRepresentable {
    let latitude: Double?; let longitude: Double?; let locationName: String
    let nearbyWorkers: [NearbyWorkerLocation]; let workerLatitude: Double?; let workerLongitude: Double?
    let showUserLocation: Bool; let currentLocation: CLLocationCoordinate2D?; let distanceText: String
    let mapToken: UUID; @Binding var mapLoaded: Bool; @Binding var failure: String?
    func makeCoordinator() -> Coordinator { Coordinator(mapLoaded: $mapLoaded, failure: $failure) }
    func makeUIView(context: Context) -> GMSMapView {
        let options = GMSMapViewOptions()
        if let point = validPoint(latitude, longitude) { options.camera = GMSCameraPosition.camera(withTarget: point, zoom: 15) }
        let map = GMSMapView(options: options)
        map.delegate = context.coordinator; map.settings.compassButton = true; map.settings.myLocationButton = false
        context.coordinator.map = map; context.coordinator.update(self)
        context.coordinator.recenterObserver = NotificationCenter.default.addObserver(forName: .errnoRecenterShopMap, object: mapToken, queue: .main) { [weak map] _ in
            guard let coordinate = validPoint(latitude, longitude) else { return }
            map?.animate(to: GMSCameraPosition.camera(withTarget: coordinate, zoom: 16))
        }
        return map
    }
    func updateUIView(_ map: GMSMapView, context: Context) { context.coordinator.update(self) }
    static func dismantleUIView(_ map: GMSMapView, coordinator: Coordinator) { if let observer = coordinator.recenterObserver { NotificationCenter.default.removeObserver(observer) } }
    private func validPoint(_ lat: Double?, _ lng: Double?) -> CLLocationCoordinate2D? {
        guard let lat, let lng, lat.isFinite, lng.isFinite, (-90...90).contains(lat), (-180...180).contains(lng) else { return nil }
        return CLLocationCoordinate2D(latitude: lat, longitude: lng)
    }
    final class Coordinator: NSObject, GMSMapViewDelegate {
        @Binding var mapLoaded: Bool; @Binding var failure: String?; weak var map: GMSMapView?; var markers: [GMSMarker] = []; var recenterObserver: NSObjectProtocol?
        init(mapLoaded: Binding<Bool>, failure: Binding<String?>) { _mapLoaded = mapLoaded; _failure = failure }
        func update(_ parent: NativeJobMap) {
            guard let map else { return }
            let authorization = CLLocationManager().authorizationStatus
            map.isMyLocationEnabled = parent.showUserLocation && (authorization == .authorizedWhenInUse || authorization == .authorizedAlways)
            markers.forEach { $0.map = nil }; markers = []
            if let point = parent.validPoint(parent.latitude, parent.longitude) {
                let marker = GMSMarker(position: point); marker.title = parent.locationName.isEmpty ? "Shop" : parent.locationName; marker.snippet = parent.distanceText; marker.map = map; markers.append(marker)
            }
            if let current = parent.currentLocation { map.animate(toLocation: current) }
            if let lat = parent.workerLatitude, let lng = parent.workerLongitude, let point = parent.validPoint(lat, lng) {
                let marker = GMSMarker(position: point); marker.title = "Worker location"; marker.map = map; markers.append(marker)
            }
            for worker in parent.nearbyWorkers {
                guard let point = parent.validPoint(worker.latitude, worker.longitude) else { continue }
                let marker = GMSMarker(position: point); marker.title = "Available worker"; marker.snippet = "\(worker.distance_km) km away"; marker.map = map; markers.append(marker)
            }
        }
        func mapViewDidFinishTileRendering(_ mapView: GMSMapView) { mapLoaded = true; failure = nil }
        func mapView(_ mapView: GMSMapView, didFailToLoadMapWithError error: Error) { mapLoaded = true; failure = "Map could not load. Shop address is still available." }
    }
}
