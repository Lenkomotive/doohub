import 'package:flutter/material.dart';
import 'package:liquid_glass_renderer/liquid_glass_renderer.dart';

// ─── Settings ────────────────────────────────────────────────────────────────

const kGlassSettings = LiquidGlassSettings(
  thickness: 12,
  blur: 10,
  glassColor: Color(0x22FFFFFF),
  lightIntensity: 0.55,
  lightAngle: -0.6,
  saturation: 1.15,
);

const kSubtleGlassSettings = LiquidGlassSettings(
  thickness: 8,
  blur: 7,
  glassColor: Color(0x18FFFFFF),
  lightIntensity: 0.4,
  lightAngle: -0.6,
  saturation: 1.1,
);

// ─── Background ──────────────────────────────────────────────────────────────

/// Dark gradient background with colour blobs that make glass effects visible.
class GlassBackground extends StatelessWidget {
  final Widget child;

  const GlassBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Container(color: const Color(0xFF080810)),
        // Top-right blue glow
        Positioned(
          top: -100,
          right: -80,
          child: Container(
            width: 280,
            height: 280,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [Color(0x40007AFF), Colors.transparent],
              ),
            ),
          ),
        ),
        // Bottom-left purple glow
        Positioned(
          bottom: -80,
          left: -60,
          child: Container(
            width: 240,
            height: 240,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              gradient: RadialGradient(
                colors: [Color(0x30BF5AF2), Colors.transparent],
              ),
            ),
          ),
        ),
        child,
      ],
    );
  }
}

// ─── Card ─────────────────────────────────────────────────────────────────────

/// A glass card. Must be inside a [GlassScreenLayer] (or any LiquidGlassLayer).
class GlassCard extends StatelessWidget {
  final Widget child;
  final double borderRadius;
  final EdgeInsetsGeometry padding;

  const GlassCard({
    super.key,
    required this.child,
    this.borderRadius = 14,
    this.padding = const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
  });

  @override
  Widget build(BuildContext context) {
    return LiquidGlass(
      shape: LiquidRoundedSuperellipse(borderRadius: borderRadius),
      child: Padding(padding: padding, child: child),
    );
  }
}

// ─── Screen Layer ─────────────────────────────────────────────────────────────

/// Wraps a screen body so all [GlassCard] / [LiquidGlass] widgets inside it
/// can see through to the [GlassBackground] behind them.
class GlassScreenLayer extends StatelessWidget {
  final Widget child;

  const GlassScreenLayer({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return GlassBackground(
      child: LiquidGlassLayer(
        settings: kSubtleGlassSettings,
        child: child,
      ),
    );
  }
}

// ─── Bottom Sheet ─────────────────────────────────────────────────────────────

/// Show a glass-styled modal bottom sheet.
Future<T?> showGlassSheet<T>({
  required BuildContext context,
  required Widget child,
}) {
  return showModalBottomSheet<T>(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    builder: (_) => _GlassSheetContainer(child: child),
  );
}

class _GlassSheetContainer extends StatelessWidget {
  final Widget child;

  const _GlassSheetContainer({required this.child});

  @override
  Widget build(BuildContext context) {
    return LiquidGlassLayer(
      settings: kGlassSettings,
      child: LiquidGlass(
        shape: LiquidRoundedSuperellipse(borderRadius: 20),
        child: child,
      ),
    );
  }
}

// ─── Bar (nav / input) ────────────────────────────────────────────────────────

/// A glass bar — use for bottom nav and input bars.
/// Has its own layer so it can see through whatever is behind it.
class GlassBar extends StatelessWidget {
  final Widget child;
  final double borderRadius;
  final EdgeInsetsGeometry padding;

  const GlassBar({
    super.key,
    required this.child,
    this.borderRadius = 0,
    this.padding = EdgeInsets.zero,
  });

  @override
  Widget build(BuildContext context) {
    return LiquidGlassLayer(
      settings: kGlassSettings,
      child: LiquidGlass(
        shape: LiquidRoundedSuperellipse(borderRadius: borderRadius),
        child: Padding(padding: padding, child: child),
      ),
    );
  }
}
