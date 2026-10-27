//
//  ErrnoApp.swift
//  Errno
//
//  Created by Aryam on 13/09/26.
//

import SwiftUI

@main
struct ErrnoApp: App {
    @State private var router = AppRouter()

    var body: some Scene {
        WindowGroup {
            AppRootView()
                .environment(router)
                .environment(router.marketplace)
                .tint(.errnoGreen)
                .preferredColorScheme(.light)
        }
    }
}
