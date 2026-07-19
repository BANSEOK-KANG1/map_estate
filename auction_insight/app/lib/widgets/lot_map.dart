import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/theme.dart';

class LotMap extends StatelessWidget {
  const LotMap({
    super.key,
    required this.items,
    this.focus,
    this.onTapLot,
    this.height = 280,
  });

  final List<LotSummary> items;
  final LotSummary? focus;
  final ValueChanged<LotSummary>? onTapLot;
  final double height;

  @override
  Widget build(BuildContext context) {
    final withCoords =
        items.where((e) => e.lat != null && e.lng != null).toList();
    final center = (focus?.lat != null && focus?.lng != null)
        ? LatLng(focus!.lat!, focus!.lng!)
        : withCoords.isNotEmpty
            ? LatLng(withCoords.first.lat!, withCoords.first.lng!)
            : const LatLng(37.5665, 126.9780);

    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: SizedBox(
        height: height,
        child: Stack(
          children: [
            FlutterMap(
              options: MapOptions(
                initialCenter: center,
                initialZoom: focus != null ? 14.5 : 10.5,
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.auctioninsight.app',
                ),
                MarkerLayer(
                  markers: withCoords
                      .map(
                        (c) => Marker(
                          point: LatLng(c.lat!, c.lng!),
                          width: 40,
                          height: 40,
                          child: GestureDetector(
                            onTap: () => onTapLot?.call(c),
                            child: Icon(
                              c.source == 'court'
                                  ? Icons.gavel
                                  : Icons.storefront,
                              color: focus?.id == c.id
                                  ? AppTheme.amber
                                  : (c.source == 'court'
                                      ? AppTheme.slate
                                      : const Color(0xFF3D6B4F)),
                              size: 32,
                              shadows: const [
                                Shadow(blurRadius: 4, color: Colors.black26),
                              ],
                            ),
                          ),
                        ),
                      )
                      .toList(),
                ),
              ],
            ),
            if (items.isNotEmpty && withCoords.isEmpty)
              Positioned.fill(
                child: ColoredBox(
                  color: Colors.black.withValues(alpha: 0.35),
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 24),
                      child: Text(
                        '지도 좌표가 아직 없습니다\n설정 → 지도 좌표 붙이기를 실행해 주세요',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.95),
                          fontWeight: FontWeight.w600,
                          height: 1.35,
                        ),
                      ),
                    ),
                  ),
                ),
              )
            else if (withCoords.isNotEmpty && withCoords.length < items.length)
              Positioned(
                left: 10,
                bottom: 10,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: Colors.black.withValues(alpha: 0.55),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    child: Text(
                      '지도 ${withCoords.length}/${items.length}',
                      style: const TextStyle(color: Colors.white, fontSize: 12),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
