import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/theme.dart';

class LotMap extends StatefulWidget {
  const LotMap({
    super.key,
    required this.items,
    this.focus,
    this.onTapLot,
    this.height = 280,
    this.expand = false,
    this.sidoPreset,
  });

  final List<LotSummary> items;
  final LotSummary? focus;
  final ValueChanged<LotSummary>? onTapLot;
  final double height;
  /// When true, fills parent instead of fixed [height].
  final bool expand;
  /// Optional sido key for fallback camera (서울특별시 / 경기도 / 인천광역시).
  final String? sidoPreset;

  @override
  State<LotMap> createState() => _LotMapState();
}

class _LotMapState extends State<LotMap> {
  final MapController _controller = MapController();
  String? _lastFitKey;

  static const _sidoCameras = <String, (LatLng, double)>{
    '서울특별시': (LatLng(37.5665, 126.9780), 11.5),
    '경기도': (LatLng(37.4138, 127.5183), 9.5),
    '인천광역시': (LatLng(37.4563, 126.7052), 11.0),
  };

  @override
  void didUpdateWidget(covariant LotMap oldWidget) {
    super.didUpdateWidget(oldWidget);
    WidgetsBinding.instance.addPostFrameCallback((_) => _fitIfNeeded());
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _fitIfNeeded());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String _fitKey() {
    final ids = widget.items
        .where((e) => e.lat != null && e.lng != null)
        .map((e) => e.id)
        .take(40)
        .join(',');
    return '${widget.sidoPreset}|${widget.focus?.id}|$ids|${widget.items.length}';
  }

  void _fitIfNeeded() {
    if (!mounted) return;
    final key = _fitKey();
    if (key == _lastFitKey) return;
    _lastFitKey = key;

    final focus = widget.focus;
    if (focus?.lat != null && focus?.lng != null) {
      _controller.move(LatLng(focus!.lat!, focus.lng!), 14.5);
      return;
    }

    final withCoords =
        widget.items.where((e) => e.lat != null && e.lng != null).toList();
    if (withCoords.isEmpty) {
      final preset = _sidoCameras[widget.sidoPreset];
      if (preset != null) {
        _controller.move(preset.$1, preset.$2);
      }
      return;
    }

    if (withCoords.length == 1) {
      _controller.move(
        LatLng(withCoords.first.lat!, withCoords.first.lng!),
        13.5,
      );
      return;
    }

    var minLat = withCoords.first.lat!;
    var maxLat = withCoords.first.lat!;
    var minLng = withCoords.first.lng!;
    var maxLng = withCoords.first.lng!;
    for (final c in withCoords.skip(1)) {
      minLat = minLat < c.lat! ? minLat : c.lat!;
      maxLat = maxLat > c.lat! ? maxLat : c.lat!;
      minLng = minLng < c.lng! ? minLng : c.lng!;
      maxLng = maxLng > c.lng! ? maxLng : c.lng!;
    }
    // Avoid degenerate bounds
    if ((maxLat - minLat).abs() < 0.002) {
      minLat -= 0.01;
      maxLat += 0.01;
    }
    if ((maxLng - minLng).abs() < 0.002) {
      minLng -= 0.01;
      maxLng += 0.01;
    }

    try {
      _controller.fitCamera(
        CameraFit.bounds(
          bounds: LatLngBounds(
            LatLng(minLat, minLng),
            LatLng(maxLat, maxLng),
          ),
          padding: const EdgeInsets.all(48),
          maxZoom: 14,
        ),
      );
    } catch (_) {
      _controller.move(
        LatLng((minLat + maxLat) / 2, (minLng + maxLng) / 2),
        11,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final withCoords =
        widget.items.where((e) => e.lat != null && e.lng != null).toList();
    final preset = _sidoCameras[widget.sidoPreset];
    final center = (widget.focus?.lat != null && widget.focus?.lng != null)
        ? LatLng(widget.focus!.lat!, widget.focus!.lng!)
        : withCoords.isNotEmpty
            ? LatLng(withCoords.first.lat!, withCoords.first.lng!)
            : (preset?.$1 ?? const LatLng(37.5665, 126.9780));
    final zoom = widget.focus != null
        ? 14.5
        : (preset?.$2 ?? (withCoords.isNotEmpty ? 10.5 : 10.0));

    final map = ClipRRect(
      borderRadius: BorderRadius.circular(widget.expand ? 0 : 14),
      child: Stack(
        children: [
          FlutterMap(
            mapController: _controller,
            options: MapOptions(
              initialCenter: center,
              initialZoom: zoom,
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
                          onTap: () => widget.onTapLot?.call(c),
                          child: Icon(
                            c.source == 'court'
                                ? Icons.gavel
                                : Icons.storefront,
                            color: widget.focus?.id == c.id
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
          if (widget.items.isNotEmpty && withCoords.isEmpty)
            Positioned.fill(
              child: ColoredBox(
                color: Colors.black.withValues(alpha: 0.35),
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24),
                    child: Text(
                      '지도 핀이 아직 없어요\n목록은 아래 · 잠시 후 새로고침해 주세요',
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
          else if (withCoords.isNotEmpty && withCoords.length < widget.items.length)
            Positioned(
              left: 10,
              bottom: 10,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.55),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  child: Text(
                    '지도 ${withCoords.length}/${widget.items.length}',
                    style: const TextStyle(color: Colors.white, fontSize: 12),
                  ),
                ),
              ),
            ),
        ],
      ),
    );

    if (widget.expand) {
      return map;
    }
    return SizedBox(height: widget.height, child: map);
  }
}
