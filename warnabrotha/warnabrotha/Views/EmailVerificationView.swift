//
//  EmailVerificationView.swift
//  warnabrotha
//
//  Windows 95 style email verification - fullscreen layout.
//

import SwiftUI

struct EmailVerificationView: View {
    @ObservedObject var viewModel: AppViewModel
    @State private var email = ""
    @State private var isValidating = false

    var body: some View {
        VStack(spacing: 0) {
            // Title bar
            HStack(spacing: 6) {
                Image(systemName: "envelope.fill")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(Win95Colors.titleBarText)

                Text("Verify Email")
                    .win95Font(size: 14)
                    .foregroundColor(Win95Colors.titleBarText)

                Spacer()

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

            // Content
            VStack(spacing: 0) {
                Spacer()

                VStack(spacing: 24) {
                    // Header
                    VStack(spacing: 8) {
                        Image(systemName: "envelope.fill")
                            .font(.system(size: 40))
                            .foregroundColor(Win95Colors.titleBarActive)

                        Text("Email Verification")
                            .win95Font(size: 18)
                            .foregroundColor(Win95Colors.textPrimary)

                        Text("Enter your UC Davis email to continue")
                            .win95Font(size: 13)
                            .foregroundColor(Win95Colors.textDisabled)
                    }

                    // Email input
                    VStack(alignment: .leading, spacing: 8) {
                        Text("UC Davis Email:")
                            .win95Font(size: 13)
                            .foregroundColor(Win95Colors.textPrimary)

                        TextField("you@ucdavis.edu", text: $email)
                            .win95Font(size: 15)
                            .foregroundColor(Win95Colors.textPrimary)
                            .textInputAutocapitalization(.never)
                            .keyboardType(.emailAddress)
                            .autocorrectionDisabled()
                            .padding(12)
                            .background(Win95Colors.inputBackground)
                            .beveledBorder(raised: false, width: 1)

                        // Validation
                        if !email.isEmpty {
                            HStack(spacing: 6) {
                                Image(systemName: isValidEmail ? "checkmark.circle.fill" : "xmark.circle.fill")
                                    .font(.system(size: 12))
                                Text(isValidEmail ? "Valid email" : "Must end with @ucdavis.edu")
                                    .win95Font(size: 12)
                            }
                            .foregroundColor(isValidEmail ? Win95Colors.safeGreen : Win95Colors.dangerRed)
                        }
                    }
                    .padding(.horizontal, 24)

                    // Verify button
                    Button {
                        Task {
                            isValidating = true
                            _ = await viewModel.verifyEmail(email)
                            isValidating = false
                        }
                    } label: {
                        Text(isValidating ? "Verifying..." : "Verify Email")
                            .win95Font(size: 16)
                            .foregroundColor(.white)
                            .frame(width: 200, height: 48)
                            .background(
                                RoundedRectangle(cornerRadius: 6)
                                    .fill(isValidEmail ? Win95Colors.titleBarActive : Win95Colors.buttonShadow)
                            )
                    }
                    .buttonStyle(PlainButtonStyle())
                    .disabled(!isValidEmail || isValidating)
                }

                Spacer()

                // Privacy notice
                HStack(spacing: 8) {
                    Image(systemName: "lock.fill")
                        .font(.system(size: 12))
                    Text("We don't store your email address")
                        .win95Font(size: 11)
                }
                .foregroundColor(Win95Colors.textDisabled)
                .padding(.bottom, 24)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Win95Colors.windowBackground)
        }
    }

    private var isValidEmail: Bool {
        email.lowercased().hasSuffix("@ucdavis.edu") && email.count > 12
    }
}

#Preview {
    EmailVerificationView(viewModel: AppViewModel())
}
