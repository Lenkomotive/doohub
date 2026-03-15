import SwiftUI

enum ThemeMode: String, CaseIterable {
    case system
    case light
    case dark
}

class SettingsStore: ObservableObject {
    private let defaults = UserDefaults.standard

    @Published var themeMode: ThemeMode {
        didSet { defaults.set(themeMode.rawValue, forKey: "theme_mode") }
    }

    init() {
        let savedTheme = UserDefaults.standard.string(forKey: "theme_mode") ?? ThemeMode.dark.rawValue
        self.themeMode = ThemeMode(rawValue: savedTheme) ?? .dark
    }

    var resolvedColorScheme: ColorScheme? {
        switch themeMode {
        case .system: return nil
        case .light: return .light
        case .dark: return .dark
        }
    }

    func toggleDarkMode() {
        switch themeMode {
        case .dark: themeMode = .light
        case .light: themeMode = .dark
        case .system: themeMode = .dark
        }
    }

    var isDarkMode: Bool {
        themeMode == .dark
    }
}
