//
//  ContentView.swift
//  warnabrotha
//
//  Windows 95 style main content view.
//

import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel = AppViewModel()
    @State private var selectedTab = 0

    var body: some View {
        ZStack {
            // Fullscreen gray background
            Win95Colors.windowBackground
                .ignoresSafeArea()

            Group {
                if !viewModel.isAuthenticated {
                    WelcomeView(viewModel: viewModel)
                } else if viewModel.showEmailVerification && !viewModel.isEmailVerified {
                    EmailVerificationView(viewModel: viewModel)
                } else {
                    // Main app layout - title bar at top, content fills screen
                    VStack(spacing: 0) {
                        // Title bar - extends edge to edge
                        Win95TitleBar(title: "WarnABrotha", icon: "car.fill")

                        // Tab content
                        Group {
                            if selectedTab == 0 {
                                ButtonsTab(viewModel: viewModel)
                            } else {
                                ProbabilityTab(viewModel: viewModel)
                            }
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)

                        // Tab bar at bottom
                        Win95TabBar(selectedTab: $selectedTab)
                    }
                    .background(Win95Colors.windowBackground)
                }
            }
            .overlay {
                if viewModel.isLoading {
                    Win95LoadingOverlay()
                }
            }
        }
    }
}

// MARK: - Windows 95 Title Bar (Standalone)

struct Win95TitleBar: View {
    let title: String
    let icon: String?

    init(title: String, icon: String? = nil) {
        self.title = title
        self.icon = icon
    }

    var body: some View {
        HStack(spacing: 6) {
            if let icon = icon {
                Image(systemName: icon)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(Win95Colors.titleBarText)
            }

            Text(title)
                .win95Font(size: 14)
                .foregroundColor(Win95Colors.titleBarText)

            Spacer()

            // Window buttons (decorative)
            HStack(spacing: 2) {
                Win95TitleButton(symbol: "−")
                Win95TitleButton(symbol: "□")
                Win95TitleButton(symbol: "×")
            }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(
            LinearGradient(
                colors: [Win95Colors.titleBarActive, Win95Colors.titleBarActive.opacity(0.85)],
                startPoint: .leading,
                endPoint: .trailing
            )
        )
    }
}

// MARK: - Windows 95 Tab Bar

struct Win95TabBar: View {
    @Binding var selectedTab: Int

    var body: some View {
        HStack(spacing: 0) {
            Win95Tab(
                title: "Actions",
                icon: "hand.tap.fill",
                isSelected: selectedTab == 0
            ) {
                selectedTab = 0
            }

            Rectangle()
                .fill(Win95Colors.buttonShadow)
                .frame(width: 1)

            Win95Tab(
                title: "Radar",
                icon: "chart.bar.fill",
                isSelected: selectedTab == 1
            ) {
                selectedTab = 1
            }
        }
        .frame(height: 44)
        .background(Win95Colors.buttonFace)
        .overlay(
            Rectangle()
                .fill(Win95Colors.buttonHighlight)
                .frame(height: 1),
            alignment: .top
        )
    }
}

struct Win95Tab: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .medium))
                Text(title)
                    .win95Font(size: 14)
            }
            .foregroundColor(isSelected ? Win95Colors.titleBarActive : Win95Colors.textPrimary)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(
                isSelected ? Win95Colors.windowBackground : Win95Colors.buttonFace
            )
            .overlay(
                // Selected indicator
                Group {
                    if isSelected {
                        VStack {
                            Rectangle()
                                .fill(Win95Colors.titleBarActive)
                                .frame(height: 3)
                            Spacer()
                        }
                    }
                }
            )
        }
        .buttonStyle(PlainButtonStyle())
    }
}

// MARK: - Welcome View (Clean Fullscreen Style)

struct WelcomeView: View {
    @ObservedObject var viewModel: AppViewModel
    @State private var isRegistering = false

    var body: some View {
        VStack(spacing: 0) {
            // Title bar
            Win95TitleBar(title: "Welcome", icon: "car.fill")

            VStack(spacing: 0) {
                Spacer()

                // Logo area
                VStack(spacing: 12) {
                    Text("🚗")
                        .font(.system(size: 48))

                    Text("WARNABROTHA")
                        .win95Font(size: 24)
                        .foregroundColor(Win95Colors.textPrimary)

                    Text("TAPS Alert System for UC Davis")
                        .win95Font(size: 14)
                        .foregroundColor(Win95Colors.textDisabled)
                }

                Spacer()
                    .frame(height: 40)

                // Features
                VStack(alignment: .leading, spacing: 12) {
                    Win95FeatureRow(icon: "bell.fill", text: "Real-time TAPS alerts")
                    Win95FeatureRow(icon: "person.2.fill", text: "Community reports")
                    Win95FeatureRow(icon: "chart.bar.fill", text: "AI probability predictions")
                    Win95FeatureRow(icon: "hand.thumbsup.fill", text: "Vote on reliability")
                }
                .padding(20)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Win95Colors.inputBackground)
                .beveledBorder(raised: false, width: 1)
                .padding(.horizontal, 24)

                Spacer()

                // Start button
                VStack(spacing: 16) {
                    Button {
                        Task {
                            isRegistering = true
                            await viewModel.register()
                            isRegistering = false
                        }
                    } label: {
                        Text(isRegistering ? "Please wait..." : "Get Started")
                            .win95Font(size: 16)
                            .foregroundColor(.white)
                            .frame(width: 200, height: 48)
                            .background(
                                RoundedRectangle(cornerRadius: 6)
                                    .fill(Win95Colors.titleBarActive)
                            )
                            .overlay(
                                RoundedRectangle(cornerRadius: 6)
                                    .strokeBorder(Color.white.opacity(0.2), lineWidth: 1)
                            )
                    }
                    .buttonStyle(PlainButtonStyle())
                    .disabled(isRegistering)
                    .opacity(isRegistering ? 0.7 : 1)

                    Text("For UC Davis students only")
                        .win95Font(size: 12)
                        .foregroundColor(Win95Colors.textDisabled)
                }
                .padding(.bottom, 40)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Win95Colors.windowBackground)
        }
    }
}

struct Win95FeatureRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 14))
                .foregroundColor(Win95Colors.titleBarActive)
                .frame(width: 20)

            Text(text)
                .win95Font(size: 14)
                .foregroundColor(Win95Colors.textPrimary)
        }
    }
}

// MARK: - Loading Overlay (Windows 95 Style)

struct Win95LoadingOverlay: View {
    @State private var dots = ""

    var body: some View {
        ZStack {
            Color.black.opacity(0.3)
                .ignoresSafeArea()

            Win95Popup(title: "Please Wait", icon: "hourglass") {
                HStack(spacing: 16) {
                    // Hourglass animation
                    Image(systemName: "hourglass")
                        .font(.system(size: 32))
                        .foregroundColor(Win95Colors.textPrimary)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Loading\(dots)")
                            .win95Font(size: 14)
                            .foregroundColor(Win95Colors.textPrimary)

                        Text("Please wait while the operation completes.")
                            .win95Font(size: 12)
                            .foregroundColor(Win95Colors.textDisabled)
                    }
                }
                .padding(8)
            }
            .frame(width: 300)
        }
        .onAppear {
            Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { _ in
                if dots.count >= 3 {
                    dots = ""
                } else {
                    dots += "."
                }
            }
        }
    }
}

#Preview {
    ContentView()
}
