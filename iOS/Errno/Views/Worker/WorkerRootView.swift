// WorkerRootView.swift
// Errno — Views/Worker
//
// Placeholder for Phase 4.

import SwiftUI

struct WorkerRootView: View {
    @Environment(AppRouter.self) private var router

    var body: some View {
        VStack {
            Text("Worker Home")
                .errnoHeadlineLarge()
            
            PrimaryButton(title: "Sign Out", style: .secondary) {
                router.signOut()
            }
            .padding()
        }
    }
}
