//
//  ErrnoApp.swift
//  Errno
//
//  Created by Aryam on 13/09/26.
//

import SwiftUI
import FirebaseCore
import GoogleSignIn

@main
struct ErrnoApp: App {
    @State private var router = AppRouter()

    init() {
        if FirebaseApp.app() == nil { FirebaseApp.configure() }
    }

    var body: some Scene {
        WindowGroup {
            AppRootView()
                .environment(router)
                .environment(router.marketplace)
                .tint(.errnoGreen)
                .onOpenURL { url in _ = FirebaseGoogleAuth.handle(url: url) }
        }
    }
}
