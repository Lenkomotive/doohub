import SwiftUI

enum AppColors {
    // Surface colors
    static let surfaceLight = Color(hex: 0xFFFFFF)
    static let surfaceDark = Color(hex: 0x000000)
    static let cardLight = Color(hex: 0xF5F5F5)
    static let cardDark = Color(hex: 0x141414)

    // Text colors
    static let textPrimaryLight = Color(hex: 0x111111)
    static let textPrimaryDark = Color(hex: 0xEEEEEE)
    static let textSecondaryLight = Color(hex: 0x666666)
    static let textSecondaryDark = Color(hex: 0x999999)

    // Brand
    static let doohubBlue = Color(hex: 0x2196F3)
    static let doohubIndigo = Color(hex: 0x3F51B5)

    // Status colors
    static let success = Color(hex: 0x34C759)
    static let error = Color(hex: 0xFF3B30)
    static let warning = Color(hex: 0xFFCC00)
    static let info = Color(hex: 0x2196F3)

    // Pipeline status colors
    static let planning = Color(hex: 0x2196F3)   // blue
    static let developing = Color(hex: 0xFF9800)  // orange
    static let reviewing = Color(hex: 0x9C27B0)   // purple
    static let done = Color(hex: 0x4CAF50)        // green
    static let failed = Color(hex: 0xFF3B30)      // red
    static let cancelled = Color(hex: 0x9E9E9E)   // grey
}

extension Color {
    init(hex: UInt, alpha: Double = 1.0) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: alpha
        )
    }
}
