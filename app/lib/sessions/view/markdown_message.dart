import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

class MarkdownMessage extends StatelessWidget {
  final String data;

  const MarkdownMessage({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final textColor = theme.colorScheme.onSurface;

    return MarkdownBody(
      data: data,
      selectable: true,
      shrinkWrap: true,
      onTapLink: (text, href, title) {
        if (href != null) {
          launchUrl(Uri.parse(href), mode: LaunchMode.externalApplication);
        }
      },
      styleSheet: MarkdownStyleSheet(
        // Base text
        p: TextStyle(fontSize: 14, color: textColor),

        // Headings
        h1: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: textColor),
        h2: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: textColor),
        h3: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: textColor),
        h4: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: textColor),
        h5: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: textColor),
        h6: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: textColor),

        // Code
        code: TextStyle(
          fontSize: 13,
          fontFamily: 'monospace',
          color: textColor,
          backgroundColor: isDark ? Colors.white10 : Colors.black.withValues(alpha: 0.06),
        ),
        codeblockDecoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1E1E) : const Color(0xFFF5F5F5),
          borderRadius: BorderRadius.circular(8),
        ),
        codeblockPadding: const EdgeInsets.all(12),

        // Links
        a: TextStyle(
          color: isDark ? Colors.lightBlue.shade300 : Colors.blue,
          decoration: TextDecoration.underline,
          decorationColor: isDark ? Colors.lightBlue.shade300 : Colors.blue,
        ),

        // Blockquote
        blockquoteDecoration: BoxDecoration(
          border: Border(
            left: BorderSide(
              color: isDark ? Colors.white24 : Colors.black26,
              width: 3,
            ),
          ),
        ),
        blockquotePadding: const EdgeInsets.only(left: 12, top: 4, bottom: 4),

        // Table
        tableHead: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: textColor),
        tableBody: TextStyle(fontSize: 13, color: textColor),
        tableBorder: TableBorder.all(
          color: isDark ? Colors.white24 : Colors.black26,
          width: 0.5,
        ),
        tableCellsPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),

        // List
        listBullet: TextStyle(fontSize: 14, color: textColor),

        // Spacing
        h1Padding: const EdgeInsets.only(top: 8, bottom: 4),
        h2Padding: const EdgeInsets.only(top: 8, bottom: 4),
        h3Padding: const EdgeInsets.only(top: 6, bottom: 2),
        pPadding: const EdgeInsets.only(bottom: 4),
        blockSpacing: 8,
      ),
    );
  }
}
