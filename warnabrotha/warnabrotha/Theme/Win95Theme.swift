//
//  Win95Theme.swift
//  warnabrotha
//
//  Windows 95 aesthetic - classic gray, beveled borders, W95FA font.
//

import SwiftUI

// MARK: - Windows 95 Colors

struct Win95Colors {
    // Classic Windows grays
    static let windowBackground = Color(red: 0.75, green: 0.75, blue: 0.75)  // #C0C0C0
    static let desktop = Color(red: 0.0, green: 0.5, blue: 0.5)  // Teal desktop
    static let buttonFace = Color(red: 0.75, green: 0.75, blue: 0.75)
    static let buttonHighlight = Color.white
    static let buttonShadow = Color(red: 0.5, green: 0.5, blue: 0.5)  // #808080
    static let buttonDarkShadow = Color.black

    // Title bar
    static let titleBarActive = Color(red: 0.0, green: 0.0, blue: 0.5)  // Navy blue
    static let titleBarInactive = Color(red: 0.5, green: 0.5, blue: 0.5)
    static let titleBarText = Color.white

    // Text colors
    static let textPrimary = Color.black
    static let textDisabled = Color(red: 0.5, green: 0.5, blue: 0.5)
    static let textHighlight = Color.white

    // Accent colors (simple, accessible)
    static let dangerRed = Color(red: 0.8, green: 0.0, blue: 0.0)
    static let safeGreen = Color(red: 0.0, green: 0.5, blue: 0.0)
    // Changed to darker olive/brown for better contrast on gray
    static let warningYellow = Color(red: 0.6, green: 0.5, blue: 0.0)
    static let infoBlue = Color(red: 0.0, green: 0.0, blue: 0.8)
    // Neutral gray for secondary actions
    static let neutralGray = Color(red: 0.6, green: 0.6, blue: 0.6)

    // Selection
    static let selectionBackground = Color(red: 0.0, green: 0.0, blue: 0.5)
    static let selectionText = Color.white

    // Input fields
    static let inputBackground = Color.white
    static let inputBorder = Color(red: 0.5, green: 0.5, blue: 0.5)
}

// MARK: - Windows 95 Font (W95FA)

struct Win95Font: ViewModifier {
    let size: CGFloat
    let weight: Font.Weight

    func body(content: Content) -> some View {
        // Use W95FA custom font - PostScript name is W95FARegular
        content
            .font(.custom("W95FARegular", size: size))
    }
}

extension View {
    func win95Font(size: CGFloat = 14, weight: Font.Weight = .regular) -> some View {
        modifier(Win95Font(size: size, weight: weight))
    }
}

// MARK: - Beveled Border (Classic 3D Effect)

struct BeveledBorder: ViewModifier {
    let raised: Bool
    let width: CGFloat

    func body(content: Content) -> some View {
        content
            .overlay(
                GeometryReader { geo in
                    // Top and left edges (light when raised, dark when sunken)
                    Path { path in
                        path.move(to: CGPoint(x: 0, y: geo.size.height))
                        path.addLine(to: CGPoint(x: 0, y: 0))
                        path.addLine(to: CGPoint(x: geo.size.width, y: 0))
                    }
                    .stroke(raised ? Win95Colors.buttonHighlight : Win95Colors.buttonDarkShadow, lineWidth: width)

                    // Inner top-left highlight
                    Path { path in
                        path.move(to: CGPoint(x: width, y: geo.size.height - width))
                        path.addLine(to: CGPoint(x: width, y: width))
                        path.addLine(to: CGPoint(x: geo.size.width - width, y: width))
                    }
                    .stroke(raised ? Win95Colors.buttonHighlight.opacity(0.7) : Win95Colors.buttonShadow, lineWidth: width)

                    // Bottom and right edges (dark when raised, light when sunken)
                    Path { path in
                        path.move(to: CGPoint(x: 0, y: geo.size.height))
                        path.addLine(to: CGPoint(x: geo.size.width, y: geo.size.height))
                        path.addLine(to: CGPoint(x: geo.size.width, y: 0))
                    }
                    .stroke(raised ? Win95Colors.buttonDarkShadow : Win95Colors.buttonHighlight, lineWidth: width)

                    // Inner bottom-right shadow
                    Path { path in
                        path.move(to: CGPoint(x: width, y: geo.size.height - width))
                        path.addLine(to: CGPoint(x: geo.size.width - width, y: geo.size.height - width))
                        path.addLine(to: CGPoint(x: geo.size.width - width, y: width))
                    }
                    .stroke(raised ? Win95Colors.buttonShadow : Win95Colors.buttonHighlight.opacity(0.7), lineWidth: width)
                }
            )
    }
}

extension View {
    func beveledBorder(raised: Bool = true, width: CGFloat = 2) -> some View {
        modifier(BeveledBorder(raised: raised, width: width))
    }
}

// MARK: - Windows 95 Title Button

struct Win95TitleButton: View {
    let symbol: String

    var body: some View {
        Text(symbol)
            .win95Font(size: 12)
            .foregroundColor(Win95Colors.textPrimary)
            .frame(width: 18, height: 16)
            .background(Win95Colors.buttonFace)
            .beveledBorder(raised: true, width: 1)
    }
}

// MARK: - Windows 95 Button

struct Win95Button: View {
    let title: String
    let color: Color
    let textColor: Color
    let action: () -> Void

    @State private var isPressed = false

    init(title: String, color: Color = Win95Colors.buttonFace, textColor: Color = Win95Colors.textPrimary, action: @escaping () -> Void) {
        self.title = title
        self.color = color
        self.textColor = textColor
        self.action = action
    }

    var body: some View {
        Button(action: {
            let generator = UIImpactFeedbackGenerator(style: .medium)
            generator.impactOccurred()
            action()
        }) {
            Text(title)
                .win95Font(size: 14)
                .foregroundColor(textColor)
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .frame(maxWidth: .infinity)
                .background(color)
                .beveledBorder(raised: !isPressed, width: 2)
        }
        .buttonStyle(PlainButtonStyle())
        .simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in isPressed = true }
                .onEnded { _ in isPressed = false }
        )
    }
}

// MARK: - Big Action Button (Configurable Size)

struct Win95BigButton: View {
    let title: String
    let subtitle: String?
    let color: Color
    let height: CGFloat
    let action: () -> Void

    @State private var isPressed = false

    // Determine text color based on background
    private var textColor: Color {
        // Use white for dark colors, black for light colors
        if color == Win95Colors.dangerRed || color == Win95Colors.safeGreen ||
           color == Win95Colors.infoBlue || color == Win95Colors.neutralGray ||
           color == Win95Colors.warningYellow {
            return .white
        }
        return .black
    }

    init(title: String, subtitle: String? = nil, color: Color, height: CGFloat = 120, action: @escaping () -> Void) {
        self.title = title
        self.subtitle = subtitle
        self.color = color
        self.height = height
        self.action = action
    }

    var body: some View {
        Button(action: {
            let generator = UIImpactFeedbackGenerator(style: .medium)
            generator.impactOccurred()
            action()
        }) {
            VStack(spacing: 6) {
                Text(title)
                    .win95Font(size: 18)
                    .foregroundColor(textColor)
                    .multilineTextAlignment(.center)

                if let subtitle = subtitle {
                    Text(subtitle)
                        .win95Font(size: 13)
                        .foregroundColor(textColor.opacity(0.85))
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: height)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(color)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .strokeBorder(
                        isPressed ? Color.black.opacity(0.3) : Color.white.opacity(0.3),
                        lineWidth: 2
                    )
            )
            .scaleEffect(isPressed ? 0.98 : 1.0)
        }
        .buttonStyle(PlainButtonStyle())
        .animation(.easeInOut(duration: 0.1), value: isPressed)
        .simultaneousGesture(
            DragGesture(minimumDistance: 0)
                .onChanged { _ in isPressed = true }
                .onEnded { _ in isPressed = false }
        )
    }
}

// MARK: - Windows 95 Alert Popup

struct Win95Popup<Content: View>: View {
    let title: String
    let icon: String
    let content: () -> Content

    var body: some View {
        VStack(spacing: 0) {
            // Title bar
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .foregroundColor(Win95Colors.titleBarText)

                Text(title)
                    .win95Font(size: 12)
                    .foregroundColor(Win95Colors.titleBarText)

                Spacer()

                // Close button
                Text("×")
                    .win95Font(size: 12)
                    .foregroundColor(Win95Colors.textPrimary)
                    .frame(width: 16, height: 14)
                    .background(Win95Colors.buttonFace)
                    .beveledBorder(raised: true, width: 1)
            }
            .padding(.horizontal, 4)
            .padding(.vertical, 2)
            .background(Win95Colors.titleBarActive)

            // Content
            content()
                .padding(8)
                .background(Win95Colors.windowBackground)
        }
        .background(Win95Colors.windowBackground)
        .beveledBorder(raised: true, width: 2)
    }
}

