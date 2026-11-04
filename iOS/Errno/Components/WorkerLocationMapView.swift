import SwiftUI
import WebKit
import CoreLocation
import Combine

/// Requests foreground location only while an assigned job detail is visible.
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

/// Embedded Leaflet/OpenFreeMap view. An absent coordinate is rendered as a neutral India overview, never a fabricated user position.
struct WorkerLocationMapView: View {
    let locationName: String
    var distanceText = "Job location"
    var isDarkTheme = true
    var mapHeight: CGFloat = 200
    var latitude: Double? = nil
    var longitude: Double? = nil
    var nearbyWorkers: [NearbyWorkerLocation] = []
    var workerLatitude: Double? = nil
    var workerLongitude: Double? = nil
    var route: OSRMRouteResponse? = nil
    @State private var failed = false
    var body: some View {
        ZStack(alignment: .bottomLeading) {
            EmbeddedJobMap(latitude: latitude, longitude: longitude, nearbyWorkers: nearbyWorkers, workerLatitude: workerLatitude, workerLongitude: workerLongitude, route: route, failed: $failed).frame(height: mapHeight)
            Text(locationName.isEmpty ? "Map location not set" : locationName).font(.system(size: 11, weight: .semibold)).lineLimit(1)
                .padding(8).background(.white.opacity(0.92), in: Capsule()).padding(8)
        }.clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay { if failed { Text("Map unavailable • \(locationName)").font(.caption).padding(8).frame(maxWidth: .infinity, maxHeight: .infinity).background(.gray.opacity(0.2)) } }
    }
}

private struct EmbeddedJobMap: UIViewRepresentable {
    let latitude: Double?; let longitude: Double?; let nearbyWorkers: [NearbyWorkerLocation]; let workerLatitude: Double?; let workerLongitude: Double?; let route: OSRMRouteResponse?; @Binding var failed: Bool
    func makeUIView(context: Context) -> WKWebView {
        let config=WKWebViewConfiguration()
        let photon=Bundle.main.object(forInfoDictionaryKey:"ERRNO_PHOTON_ENDPOINT") as? String ?? "https://photon.komoot.io"
        let osrm=Bundle.main.object(forInfoDictionaryKey:"ERRNO_OSRM_ENDPOINT") as? String ?? "https://router.project-osrm.org/route/v1/driving"
        let tiles=Bundle.main.object(forInfoDictionaryKey:"ERRNO_TILE_ENDPOINT") as? String ?? "https://tiles.openfreemap.org/planet"
        let style=Bundle.main.object(forInfoDictionaryKey:"ERRNO_MAP_STYLE_URL") as? String ?? "https://tiles.openfreemap.org/styles/liberty"
        config.userContentController.addUserScript(WKUserScript(source:"window.ERRNO_PHOTON_ENDPOINT=\(Self.js(photon));window.ERRNO_OSRM_ENDPOINT=\(Self.js(osrm));window.ERRNO_TILE_ENDPOINT=\(Self.js(tiles));window.ERRNO_MAP_STYLE_URL=\(Self.js(style));",injectionTime:.atDocumentStart,forMainFrameOnly:true))
        let view=WKWebView(frame:.zero,configuration:config); view.scrollView.isScrollEnabled=false; view.navigationDelegate=context.coordinator
        if let file=Bundle.main.url(forResource:"index",withExtension:"html") { view.loadFileURL(file,allowingReadAccessTo:file.deletingLastPathComponent()) } else { failed=true }
        return view
    }
    func updateUIView(_ view:WKWebView,context:Context) {
        context.coordinator.apply = { [self] webView in self.apply(to: webView) }
        apply(to: view)
    }
    private func apply(to view: WKWebView) {
        if let lat=latitude,let lng=longitude { view.evaluateJavaScript("ErrnoMapAPI&&ErrnoMapAPI.setLocation(\(lat),\(lng),'Job location')") }
        if let data=try? JSONEncoder().encode(nearbyWorkers),let json=String(data:data,encoding:.utf8) { view.evaluateJavaScript("ErrnoMapAPI&&ErrnoMapAPI.setWorkers(\(json))") }
        if let lat=workerLatitude,let lng=workerLongitude { view.evaluateJavaScript("ErrnoMapAPI&&ErrnoMapAPI.setWorker(\(lat),\(lng))") }
        if let route,let data=try? JSONEncoder().encode(route.geometry.coordinates),let json=String(data:data,encoding:.utf8) {
            let coords = "(\(json)).map(c=>[c[1],c[0]])"
            view.evaluateJavaScript("ErrnoMapAPI&&ErrnoMapAPI.setRoute(\(coords),\(route.distance_km),\(Double(route.duration_minutes)))")
        }
    }
    func makeCoordinator()->Coordinator { Coordinator(failed:$failed) }
    private static func js(_ value:String)->String { let d=try? JSONSerialization.data(withJSONObject:[value]); let s=d.flatMap{String(data:$0,encoding:.utf8)} ?? "[\"\"]"; return String(s.dropFirst().dropLast()) }
    final class Coordinator:NSObject,WKNavigationDelegate { @Binding var failed:Bool; var apply: ((WKWebView)->Void)?; init(failed:Binding<Bool>){_failed=failed}; func webView(_ webView:WKWebView,didFinish navigation:WKNavigation!){apply?(webView)}; func webView(_ webView:WKWebView,didFail navigation:WKNavigation!,withError error:Error){failed=true} }
}
