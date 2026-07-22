import 'package:flutter/material.dart';
import 'package:auction_insight_app/models/models.dart';
import 'package:auction_insight_app/services/lot_verdict_store.dart';
import 'package:auction_insight_app/theme.dart';

class PassWatchCard extends StatefulWidget {
  const PassWatchCard({super.key, required this.lot});

  final LotDetail lot;

  @override
  State<PassWatchCard> createState() => _PassWatchCardState();
}

class _PassWatchCardState extends State<PassWatchCard> {
  String _verdict = '';
  final _noteCtrl = TextEditingController();
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final data = await LotVerdictStore.load(
      widget.lot.source,
      widget.lot.externalId,
    );
    if (!mounted) return;
    setState(() {
      _verdict = data.verdict;
      _noteCtrl.text = data.note;
      _loading = false;
    });
  }

  Future<void> _persist() async {
    await LotVerdictStore.save(
      source: widget.lot.source,
      externalId: widget.lot.externalId,
      verdict: _verdict,
      note: _noteCtrl.text.trim(),
    );
  }

  @override
  void dispose() {
    _noteCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const SizedBox(
        height: 48,
        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
      );
    }
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '내 판단 (이 기기에만 저장)',
            style: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              ChoiceChip(
                label: const Text('Watch'),
                selected: _verdict == 'watch',
                onSelected: (_) async {
                  setState(() => _verdict = _verdict == 'watch' ? '' : 'watch');
                  await _persist();
                },
              ),
              const SizedBox(width: 8),
              ChoiceChip(
                label: const Text('Pass'),
                selected: _verdict == 'pass',
                onSelected: (_) async {
                  setState(() => _verdict = _verdict == 'pass' ? '' : 'pass');
                  await _persist();
                },
              ),
            ],
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _noteCtrl,
            maxLines: 2,
            decoration: const InputDecoration(
              hintText: '사유 메모 (예: 임차 복잡 / 할인 충분 / 현장 확인 필요)',
              isDense: true,
              border: OutlineInputBorder(),
            ),
            onChanged: (_) => _persist(),
          ),
        ],
      ),
    );
  }
}
