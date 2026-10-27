import SwiftUI

struct SplashView: View {
    @Environment(AppRouter.self) private var router
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var scale = 0.7
    @State private var opacity = 0.0
    var body: some View {
        VStack(spacing: 0) {
            Spacer()
            ErrnoLogo(size: .large)
                .padding(24).frame(maxWidth: 400)
                .background(.white.opacity(0.05), in: RoundedRectangle(cornerRadius: 24))
                .scaleEffect(scale).opacity(opacity)
            Text("Connecting Local Shops & Workers")
                .font(.system(size: 20, weight: .bold)).padding(.top, 32)
            Text("Find reliable shift help • Work when you need it")
                .font(.system(size: 14)).foregroundStyle(.white.opacity(0.75)).padding(.top, 8)
            Spacer()
            PrimaryButton(title: "Get Started") { router.transitionToAuth() }
                .padding(.bottom, 16)
        }.multilineTextAlignment(.center).foregroundStyle(.white).padding(32)
            .marketplacePage(dark: true)
            .task {
                if reduceMotion { scale = 1; opacity = 1; return }
                withAnimation(.easeInOut(duration: 0.8)) { scale = 1 }
                do { try await Task.sleep(for: .milliseconds(800)) } catch { return }
                withAnimation(.easeInOut(duration: 0.6)) { opacity = 1 }
            }
    }
}
