import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:map_estate_app/models/models.dart';
import 'package:map_estate_app/theme.dart';

class ComplexMap extends StatelessWidget {
  const ComplexMap({
    super.key,
    required this.items,
    this.focus,
    this.workLat,
    this.workLng,
    this.onTapComplex,
    this.height = 280,
  });

  final List<ComplexSummary> items;
  final ComplexSummary? focus;
  final double? workLat;
  final double? workLng;
  final ValueChanged<ComplexSummary>? onTapComplex;
  final double height;

  @override
  Widget build(BuildContext context) {
    final withCoords = items.where((e) => e.lat != null && e.lng != null).toList();
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
            initialZoom: focus != null ? 15 : 11.5,
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'com.mapestate.app',
            ),
            MarkerLayer(
              markers: [
                ...withCoords.map(
                  (c) => Marker(
                    point: LatLng(c.lat!, c.lng!),
                    width: 40,
                    height: 40,
                    child: GestureDetector(
                      onTap: () => onTapComplex?.call(c),
                      child: Icon(
                        Icons.location_on,
                        color: focus?.id == c.id ? AppTheme.clay : AppTheme.moss,
                        size: 36,
                        shadows: const [
                          Shadow(blurRadius: 4, color: Colors.black26),
                        ],
                      ),
                    ),
                  ),
                ),
                if (workLat != null && workLng != null)
                  Marker(
                    point: LatLng(workLat!, workLng!),
                    width: 36,
                    height: 36,
                    child: const Icon(
                      Icons.work,
                      color: AppTheme.clay,
                      size: 30,
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
