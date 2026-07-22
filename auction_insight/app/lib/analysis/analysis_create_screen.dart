import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/theme.dart';

/// Manual Phase-1 registration for deep analysis items.
class AnalysisCreateScreen extends ConsumerStatefulWidget {
  const AnalysisCreateScreen({super.key, this.initialSource = 'onbid'});

  final String initialSource;

  @override
  ConsumerState<AnalysisCreateScreen> createState() =>
      _AnalysisCreateScreenState();
}

class _AnalysisCreateScreenState extends ConsumerState<AnalysisCreateScreen> {
  late String _source;
  final _address = TextEditingController();
  final _title = TextEditingController();
  final _usage = TextEditingController(text: '아파트');
  final _caseNo = TextEditingController();
  final _appraisalMan = TextEditingController();
  final _minBidMan = TextEditingController();
  final _plannedMan = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _source = widget.initialSource;
  }

  @override
  void dispose() {
    _address.dispose();
    _title.dispose();
    _usage.dispose();
    _caseNo.dispose();
    _appraisalMan.dispose();
    _minBidMan.dispose();
    _plannedMan.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_address.text.trim().isEmpty) {
      setState(() => _error = '주소는 필수입니다.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      double? man(String s) =>
          s.trim().isEmpty ? null : double.tryParse(s.replaceAll(',', ''));
      final item = await ref.read(apiProvider).createAnalysisItem({
        'source': _source,
        'address': _address.text.trim(),
        'title': _title.text.trim().isEmpty
            ? _address.text.trim()
            : _title.text.trim(),
        'usage': _usage.text.trim(),
        'case_no': _caseNo.text.trim(),
        if (man(_appraisalMan.text) != null)
          'appraisal_manwon': man(_appraisalMan.text),
        if (man(_minBidMan.text) != null) 'min_bid_manwon': man(_minBidMan.text),
        if (man(_plannedMan.text) != null)
          'planned_price_manwon': man(_plannedMan.text),
      });
      if (!mounted) return;
      context.push('/analysis/${item.id}');
    } catch (e) {
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('분석 물건 수동 등록')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            '금액은 만원 단위로 입력하세요. 서버가 원·만원·억을 함께 표시하고 자릿수 오류를 검사합니다.',
            style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.6)),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            children: [
              ChoiceChip(
                label: const Text('법원경매'),
                selected: _source == 'court',
                onSelected: (_) => setState(() => _source = 'court'),
              ),
              ChoiceChip(
                label: const Text('온비드공매'),
                selected: _source == 'onbid',
                onSelected: (_) => setState(() => _source = 'onbid'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _address,
            decoration: const InputDecoration(labelText: '주소 *'),
          ),
          TextField(
            controller: _title,
            decoration: const InputDecoration(labelText: '제목'),
          ),
          TextField(
            controller: _usage,
            decoration: const InputDecoration(labelText: '용도'),
          ),
          TextField(
            controller: _caseNo,
            decoration: const InputDecoration(labelText: '사건/관리번호'),
          ),
          TextField(
            controller: _appraisalMan,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '감정가 (만원)'),
          ),
          TextField(
            controller: _minBidMan,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '최저가 (만원)'),
          ),
          TextField(
            controller: _plannedMan,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: '공매예정가 등 (만원)'),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!, style: const TextStyle(color: Colors.red)),
          ],
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _saving ? null : _submit,
            child: Text(_saving ? '저장 중…' : '등록 후 분석 상세'),
          ),
        ],
      ),
    );
  }
}
