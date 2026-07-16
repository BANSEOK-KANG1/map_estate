import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:map_estate_app/models/models.dart';
import 'package:map_estate_app/theme.dart';
import 'package:map_estate_app/utils/format.dart';

class PriceTrendChart extends StatelessWidget {
  const PriceTrendChart({super.key, required this.points});

  final List<TrendPoint> points;

  @override
  Widget build(BuildContext context) {
    if (points.isEmpty) {
      return const SizedBox(
        height: 180,
        child: Center(child: Text('추이 데이터 없음')),
      );
    }

    final spots = <FlSpot>[];
    for (var i = 0; i < points.length; i++) {
      spots.add(FlSpot(i.toDouble(), points[i].medianPriceManwon));
    }

    return SizedBox(
      height: 220,
      child: LineChart(
        LineChartData(
          minY: spots.map((s) => s.y).reduce((a, b) => a < b ? a : b) * 0.92,
          maxY: spots.map((s) => s.y).reduce((a, b) => a > b ? a : b) * 1.08,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (v) => FlLine(
              color: AppTheme.line.withValues(alpha: 0.7),
              strokeWidth: 1,
            ),
          ),
          borderData: FlBorderData(show: false),
          titlesData: FlTitlesData(
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            leftTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 42,
                getTitlesWidget: (v, meta) => Text(
                  '${v.toStringAsFixed(0)}만',
                  style: const TextStyle(fontSize: 10, color: AppTheme.ink),
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                interval: (points.length / 4).clamp(1, 6).toDouble(),
                getTitlesWidget: (v, meta) {
                  final i = v.toInt();
                  if (i < 0 || i >= points.length) return const SizedBox.shrink();
                  final ym = points[i].yearMonth;
                  return Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      ym.substring(2),
                      style: const TextStyle(fontSize: 10),
                    ),
                  );
                },
              ),
            ),
          ),
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (touched) => touched.map((t) {
                final p = points[t.x.toInt()];
                return LineTooltipItem(
                  '${p.yearMonth}\n${formatManwon(p.medianPriceManwon.round())}',
                  const TextStyle(color: Colors.white, fontSize: 12),
                );
              }).toList(),
            ),
          ),
          lineBarsData: [
            LineChartBarData(
              spots: spots,
              isCurved: true,
              color: AppTheme.moss,
              barWidth: 3,
              dotData: const FlDotData(show: false),
              belowBarData: BarAreaData(
                show: true,
                color: AppTheme.moss.withValues(alpha: 0.12),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
