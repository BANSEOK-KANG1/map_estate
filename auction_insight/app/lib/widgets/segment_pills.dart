import 'package:flutter/material.dart';
import 'package:auction_insight_app/theme.dart';

/// Compact single-select pills — avoids M3 ChoiceChip checkmark + label clipping.
class SegmentPills extends StatelessWidget {
  const SegmentPills({
    super.key,
    required this.options,
    required this.selectedKey,
    required this.onSelected,
    this.dense = false,
  });

  final List<(String key, String label)> options;
  final String selectedKey;
  final ValueChanged<String> onSelected;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (var i = 0; i < options.length; i++) ...[
            if (i > 0) SizedBox(width: dense ? 6 : 8),
            _Pill(
              label: options[i].$2,
              selected: selectedKey == options[i].$1,
              dense: dense,
              onTap: () => onSelected(options[i].$1),
            ),
          ],
        ],
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({
    required this.label,
    required this.selected,
    required this.onTap,
    this.dense = false,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final hPad = dense ? 12.0 : 14.0;
    final vPad = dense ? 7.0 : 9.0;
    return Material(
      color: selected ? AppTheme.slate : Colors.white.withValues(alpha: 0.72),
      borderRadius: BorderRadius.circular(999),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(999),
        child: Container(
          padding: EdgeInsets.symmetric(horizontal: hPad, vertical: vPad),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected ? AppTheme.slate : AppTheme.line,
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: dense ? 12.5 : 13.5,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              color: selected ? Colors.white : AppTheme.ink.withValues(alpha: 0.72),
              height: 1.1,
            ),
          ),
        ),
      ),
    );
  }
}
