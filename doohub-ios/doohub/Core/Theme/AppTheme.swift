import SwiftUI

enum AppTheme {
    static func primaryColor(for colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? AppColors.doohubBlue : AppColors.doohubIndigo
    }

    static func surfaceColor(for colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? AppColors.surfaceDark : AppColors.surfaceLight
    }

    static func cardColor(for colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? AppColors.cardDark : AppColors.cardLight
    }

    static func textPrimaryColor(for colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? AppColors.textPrimaryDark : AppColors.textPrimaryLight
    }

    static func textSecondaryColor(for colorScheme: ColorScheme) -> Color {
        colorScheme == .dark ? AppColors.textSecondaryDark : AppColors.textSecondaryLight
    }

    static func pipelineStatusColor(for status: String) -> Color {
        switch status {
        case "planning", "planned":
            return AppColors.planning
        case "developing", "developed":
            return AppColors.developing
        case "reviewing":
            return AppColors.reviewing
        case "done", "merged":
            return AppColors.done
        case "failed":
            return AppColors.failed
        case "cancelled":
            return AppColors.cancelled
        default:
            return AppColors.info
        }
    }

    static func sessionStatusColor(for status: String) -> Color {
        switch status {
        case "busy":
            return AppColors.warning
        case "idle":
            return AppColors.success
        default:
            return AppColors.textSecondaryLight
        }
    }
}
