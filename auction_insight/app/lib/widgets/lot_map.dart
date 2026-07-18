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
    final center = focus?.lat != null
        ? LatLng(focus!.lat!, focus!.lng!)
        : withCoords.isNotEmpty
            ? LatLng(withCoords.first.lat!, withCoords.first.lng!)
            : const LatLng(37.5665, 126.9780);

    return ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: SizedBox(
        height: height,
        child: FlutterMap(
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
      ),
    );
  }
}
