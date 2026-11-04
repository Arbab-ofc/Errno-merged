import Foundation
import FirebaseMessaging
import FirebaseCore
import UserNotifications
import UIKit
import SwiftUI

extension Notification.Name { static let errnoNotificationTapped = Notification.Name("errno.notification.tapped") }

struct InboxNotification: Decodable, Identifiable, Sendable {
    let id: String; let eventType: String; let title: String; let body: String; let category: String
    let priority: String; let data: [String: String]; let createdAt: String; let readAt: String?
}
struct InboxPage: Decodable, Sendable { let items: [InboxNotification]; let nextCursor: String? }

@MainActor enum ErrnoNotifications {
    static let installKey = "errno.notifications.installation"
    static let serverIDKey = "errno.notifications.device-id"
    static var installationID: String {
        if let value = UserDefaults.standard.string(forKey: installKey) { return value }
        let value = UUID().uuidString; UserDefaults.standard.set(value, forKey: installKey); return value
    }
    static func authorizationAndRegister() async {
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()
        guard settings.authorizationStatus == .authorized || settings.authorizationStatus == .provisional else { return }
        await MainActor.run { UIApplication.shared.registerForRemoteNotifications() }
        if let token = try? await Messaging.messaging().token() { await register(token: token) }
    }
    static func register(token: String) async {
        guard let auth = await bearer(), let config = try? BackendConfiguration.bundled() else { return }
        var request = URLRequest(url: config.baseURL.appendingPathComponent("api/v1/devices/register"))
        request.httpMethod = "POST"; request.setValue("Bearer \(auth)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["platform":"ios", "deviceId":installationID, "fcmToken":token,
            "appVersion":Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? ""])
        guard let (data,response) = try? await URLSession.shared.data(for: request), (response as? HTTPURLResponse)?.statusCode == 200,
              let value = try? JSONSerialization.jsonObject(with:data) as? [String:Any], let id = value["deviceId"] as? String else { return }
        UserDefaults.standard.set(id, forKey: serverIDKey)
    }
    static func unregisterCurrent() async {
        guard let id = UserDefaults.standard.string(forKey: serverIDKey), let auth = await bearer(), let config = try? BackendConfiguration.bundled() else { return }
        var request = URLRequest(url: config.baseURL.appendingPathComponent("api/v1/devices/\(id)")); request.httpMethod="DELETE"
        request.setValue("Bearer \(auth)", forHTTPHeaderField:"Authorization")
        _ = try? await URLSession.shared.data(for: request); UserDefaults.standard.removeObject(forKey: serverIDKey)
    }
    private static func bearer() async -> String? {
        if let token = BackendTokenStore.readToken() { return token }
        return try? await FirebaseGoogleAuth.currentIDToken()
    }
    static func inbox(cursor: String? = nil) async throws -> InboxPage {
        let path = cursor.map { "api/v1/notifications?cursor=\($0)&limit=30" } ?? "api/v1/notifications?limit=30"
        return try await send(path:path, method:"GET")
    }
    static func unreadCount() async throws -> Int {
        let result: [String:Int] = try await send(path:"api/v1/notifications/unread-count", method:"GET")
        return result["count"] ?? 0
    }
    static func marketingPreference() async throws -> Bool {
        let result: [String:Bool] = try await send(path:"api/v1/notifications/preferences", method:"GET")
        return result["marketing_enabled"] ?? false
    }
    static func setMarketingPreference(_ value: Bool) async throws {
        let _: [String:Bool] = try await send(path:"api/v1/notifications/preferences", method:"PATCH", body:["marketing_enabled":value])
    }
    static func markRead(_ id: String) async throws {
        let _: [String:String] = try await send(path:"api/v1/notifications/\(id)/read", method:"PATCH", body:[:])
    }
    static func markAllRead() async throws {
        let _: [String:Int] = try await send(path:"api/v1/notifications/read-all", method:"PATCH", body:[:])
    }
    private static func send<T: Decodable>(path: String, method: String, body: [String:Any]? = nil) async throws -> T {
        guard let auth = await bearer(), let config = try? BackendConfiguration.bundled() else { throw APIError.unauthorized }
        let pathParts=path.split(separator:"?",maxSplits:1,omittingEmptySubsequences:false)
        var url=config.baseURL
        for segment in pathParts[0].split(separator:"/") { url.appendPathComponent(String(segment)) }
        var components=URLComponents(url:url,resolvingAgainstBaseURL:false)
        if pathParts.count>1 { components?.percentEncodedQuery=String(pathParts[1]) }
        guard let finalURL=components?.url else { throw APIError.configuration }
        var request=URLRequest(url:finalURL); request.httpMethod=method
        request.setValue("Bearer \(auth)",forHTTPHeaderField:"Authorization"); request.setValue("application/json",forHTTPHeaderField:"Accept")
        if let body { request.httpBody=try JSONSerialization.data(withJSONObject:body); request.setValue("application/json",forHTTPHeaderField:"Content-Type") }
        let (data,response)=try await URLSession.shared.data(for:request)
        guard let response=response as? HTTPURLResponse,(200..<300).contains(response.statusCode) else { throw APIError.server }
        return try JSONDecoder().decode(T.self,from:data)
    }
}

final class ErrnoAppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate, MessagingDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        if FirebaseApp.app() == nil { FirebaseApp.configure() }
        UNUserNotificationCenter.current().delegate = self; Messaging.messaging().delegate = self
        return true
    }
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) { Messaging.messaging().apnsToken = deviceToken }
    func messaging(_ messaging: Messaging, didReceiveRegistrationToken fcmToken: String?) {
        guard let fcmToken else { return }; Task { await ErrnoNotifications.register(token:fcmToken) }
    }
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.banner,.badge,.sound])
    }
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        let info = response.notification.request.content.userInfo
        UserDefaults.standard.set(info["route"] as? String ?? "inbox", forKey:"errno.notifications.pending-route")
        UserDefaults.standard.set(info["notification_id"] as? String, forKey:"errno.notifications.pending-id")
        NotificationCenter.default.post(name:.errnoNotificationTapped, object:nil)
        completionHandler()
    }
}

struct NotificationInboxView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var items: [InboxNotification] = []
    @State private var error: String?
    @State private var permissionExplanation = false
    @State private var marketingEnabled = false
    @State private var nextCursor: String?
    var body: some View {
        NavigationStack {
            Group {
                if let error { ContentUnavailableView("Notifications unavailable", systemImage:"bell.slash", description:Text(error)) }
                else if items.isEmpty { ContentUnavailableView("You're all caught up", systemImage:"bell") }
                else { List {
                    Section("Optional notifications") { Toggle("Promotions", isOn:$marketingEnabled).onChange(of:marketingEnabled) { _, value in Task { try? await ErrnoNotifications.setMarketingPreference(value) } } }
                    Section("Inbox") { ForEach(items) { item in Button { Task { try? await ErrnoNotifications.markRead(item.id); await load() } } label: {
                    VStack(alignment:.leading,spacing:5) { Text(item.title).font(.headline); Text(item.body).font(.subheadline); Text("\(item.category.capitalized) · \(item.createdAt)").font(.caption).foregroundStyle(.secondary) }
                        .opacity(item.readAt == nil ? 1 : 0.65)
                    }.buttonStyle(.plain) } }
                    if let nextCursor { Button("Load more") { Task { await loadMore(nextCursor) } } }
                } // List
                } // else
            }.navigationTitle("Notifications").toolbar {
                ToolbarItem(placement:.topBarLeading) { Button("Done") { dismiss() } }
                ToolbarItem(placement:.topBarTrailing) { Button("Read all") { Task { try? await ErrnoNotifications.markAllRead(); await load() } } }
            }.refreshable { await load() }
        }.task {
            await load()
            let settings = await UNUserNotificationCenter.current().notificationSettings()
            if settings.authorizationStatus == .notDetermined { permissionExplanation = true }
        }.alert("Stay updated", isPresented:$permissionExplanation) {
            Button("Continue") { Task { _ = try? await UNUserNotificationCenter.current().requestAuthorization(options:[.alert,.badge,.sound]); await ErrnoNotifications.authorizationAndRegister() } }
            Button("Not now", role:.cancel) { }
        } message: { Text("Allow notifications for booking, job, payment and verification updates. Your in-app inbox remains available if you skip.") }
    }
    @MainActor private func load() async { do { error=nil; let page=try await ErrnoNotifications.inbox(); items=page.items; nextCursor=page.nextCursor; marketingEnabled=try await ErrnoNotifications.marketingPreference() } catch { self.error=error.localizedDescription } }
    @MainActor private func loadMore(_ cursor:String) async { do { let page=try await ErrnoNotifications.inbox(cursor:cursor); items += page.items; nextCursor=page.nextCursor } catch { self.error=error.localizedDescription } }
}
