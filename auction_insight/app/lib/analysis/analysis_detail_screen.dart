import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:auction_insight_app/analysis/analysis_models.dart';
import 'package:auction_insight_app/providers/providers.dart';
import 'package:auction_insight_app/theme.dart';
import 'package:auction_insight_app/utils/format.dart';

final _analysisProvider =
    FutureProvider.autoDispose.family<AnalysisItemDetail, int>((ref, id) {
  return ref.watch(apiProvider).fetchAnalysisItem(id);
});

class AnalysisDetailScreen extends ConsumerWidget {
  const AnalysisDetailScreen({super.key, required this.itemId});

  final int itemId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(_analysisProvider(itemId));
    return async.when(
      loading: () => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => Scaffold(
        appBar: AppBar(),
        body: Center(child: Text('$e')),
      ),
      data: (item) => DefaultTabController(
        length: 7,
        child: Scaffold(
          appBar: AppBar(
            title: Text(item.title, maxLines: 1, overflow: TextOverflow.ellipsis),
            bottom: const TabBar(
              isScrollable: true,
              tabs: [
                Tab(text: '한눈에'),
                Tab(text: '권리'),
                Tab(text: '대출·현금'),
                Tab(text: '시세·수익'),
                Tab(text: '문서함'),
                Tab(text: '현장'),
                Tab(text: '가이드'),
              ],
            ),
          ),
          body: TabBarView(
            children: [
              _OverviewTab(item: item),
              _RightsTab(item: item, itemId: itemId),
              _LoanTab(item: item, itemId: itemId),
              _MarketTab(item: item),
              _DocsTab(item: item, itemId: itemId),
              _SiteTab(item: item),
              _GuideTab(source: item.source),
            ],
          ),
        ),
      ),
    );
  }
}

class _OverviewTab extends StatelessWidget {
  const _OverviewTab({required this.item});
  final AnalysisItemDetail item;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _verdictBanner(item),
        const SizedBox(height: 12),
        _moneyCard('감정가', item.appraisal),
        _moneyCard('최저가', item.minBid),
        _moneyCard('공매예정가 등', item.plannedPrice),
        if (item.digitWarnings.isNotEmpty) ...[
          const SizedBox(height: 8),
          ...item.digitWarnings.map(
            (w) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text(
                '⚠ ${w['message']}',
                style: TextStyle(color: AppTheme.amber.withValues(alpha: 0.95)),
              ),
            ),
          ),
        ],
        const SizedBox(height: 12),
        Text(
          '총투입액 ${formatManwon(((item.costBreakdown['total_cost_won'] as num?)?.round()))}',
          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
        ),
        if (item.bidCeiling != null)
          Text(
            '적정 입찰 상한 ${formatManwon((item.bidCeiling!['bid_ceiling_won'] as num?)?.round())}',
            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
          ),
        const SizedBox(height: 12),
        const Text('다음에 확인할 것', style: TextStyle(fontWeight: FontWeight.w700)),
        ...item.checkNext.map((c) => Text('· $c')),
      ],
    );
  }
}

Widget _verdictBanner(AnalysisItemDetail item) {
  final ban = item.beginnerBan || item.verdict == 'BEGINNER_BAN';
  return Container(
    width: double.infinity,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: ban
          ? const Color(0xFF8B4513).withValues(alpha: 0.12)
          : AppTheme.slate.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(12),
      border: Border.all(color: AppTheme.line),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          verdictLabelKo(item.verdict),
          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
        ),
        if (ban)
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text(
              '초보자 입찰 금지/보류: 필수문서 또는 자금계획이 부족합니다. AI가 입찰을 권하지 않으며, 확정 권리분석도 아닙니다.',
            ),
          ),
      ],
    ),
  );
}

Widget _moneyCard(String label, MoneyTriple? m) {
  if (m == null) {
    return ListTile(
      dense: true,
      title: Text(label),
      subtitle: const Text('미입력 (UNKNOWN)'),
    );
  }
  return Card(
    child: ListTile(
      title: Text(label, style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text('${m.labelWon}\n${m.labelManwon}\n${m.labelEok}'),
      isThreeLine: true,
    ),
  );
}

class _RightsTab extends ConsumerStatefulWidget {
  const _RightsTab({required this.item, required this.itemId});
  final AnalysisItemDetail item;
  final int itemId;

  @override
  ConsumerState<_RightsTab> createState() => _RightsTabState();
}

class _RightsTabState extends ConsumerState<_RightsTab> {
  bool _busy = false;
  String? _msg;
  final _rightLabel = TextEditingController();
  final _rightAmount = TextEditingController();
  final _rightDate = TextEditingController();
  String _rightKind = 'mortgage';
  bool _asBaseline = false;

  final _occLabel = TextEditingController();
  final _occDeposit = TextEditingController();
  final _moveIn = TextEditingController();
  final _fixed = TextEditingController();
  final _bizReg = TextEditingController();
  String _occKind = 'housing';
  bool _taxOk = true;

  @override
  void dispose() {
    _rightLabel.dispose();
    _rightAmount.dispose();
    _rightDate.dispose();
    _occLabel.dispose();
    _occDeposit.dispose();
    _moveIn.dispose();
    _fixed.dispose();
    _bizReg.dispose();
    super.dispose();
  }

  Future<void> _addRight() async {
    setState(() => _busy = true);
    try {
      final docs = widget.item.documents;
      await ref.read(apiProvider).createAnalysisRight(widget.itemId, {
        'kind': _rightKind,
        'label': _rightLabel.text.trim().isEmpty
            ? _rightKind
            : _rightLabel.text.trim(),
        if (_rightAmount.text.trim().isNotEmpty)
          'amount_won': int.tryParse(_rightAmount.text.replaceAll(',', '')),
        if (_rightDate.text.trim().isNotEmpty) 'event_date': _rightDate.text.trim(),
        'is_malso_baseline': _asBaseline,
        if (docs.isNotEmpty) 'evidence_doc_id': docs.first['id'],
        'evidence_excerpt': docs.isEmpty
            ? ''
            : (docs.first['text_preview'] as String? ?? '수동 입력'),
        'evidence_page': 1,
      });
      ref.invalidate(_analysisProvider(widget.itemId));
      setState(() => _msg = '권리 항목 추가됨');
    } catch (e) {
      setState(() => _msg = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addOcc() async {
    setState(() => _busy = true);
    try {
      final docs = widget.item.documents;
      await ref.read(apiProvider).createAnalysisOccupancy(widget.itemId, {
        'claim_kind': _occKind,
        'occupant_label': _occLabel.text.trim(),
        if (_occDeposit.text.trim().isNotEmpty)
          'deposit_won': int.tryParse(_occDeposit.text.replaceAll(',', '')),
        if (_occKind == 'housing') ...{
          if (_moveIn.text.trim().isNotEmpty) 'move_in_date': _moveIn.text.trim(),
          if (_fixed.text.trim().isNotEmpty) 'fixed_date': _fixed.text.trim(),
        } else ...{
          if (_bizReg.text.trim().isNotEmpty)
            'business_reg_date': _bizReg.text.trim(),
          'tax_invoice_ok': _taxOk ? 1 : 0,
        },
        if (docs.isNotEmpty) 'evidence_doc_id': docs.first['id'],
        'evidence_excerpt': docs.isEmpty ? '' : '점유·임차 수동 입력',
        'evidence_page': 1,
      });
      ref.invalidate(_analysisProvider(widget.itemId));
      setState(() => _msg = '점유/임차 추가됨');
    } catch (e) {
      setState(() => _msg = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _evaluate({bool applyFinance = false}) async {
    setState(() => _busy = true);
    try {
      await ref.read(apiProvider).evaluateAnalysisTimeline(
            widget.itemId,
            applyFinanceSuggest: applyFinance,
          );
      ref.invalidate(_analysisProvider(widget.itemId));
      setState(() => _msg = applyFinance ? '평가 + 인수금액 제안 반영' : '타임라인 평가 완료');
    } catch (e) {
      setState(() => _msg = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    final eval = item.timelineEval;
    final timeline = (eval['timeline'] as List?) ?? const [];
    final flags = ((eval['risk_flags'] as List?) ?? const []).cast<String>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(item.rightsStatusNote),
        const SizedBox(height: 8),
        Text(
          item.source == 'court'
              ? '트랙: 법원경매 말소기준권리 (court_malso). 등기일 선후순위로 말소/인수 후보만 제시합니다.'
              : '트랙: 온비드 조세·배분 (onbid_tax_distribute). 법원 말소 자동소멸 로직을 쓰지 않습니다.',
          style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.7), fontSize: 12),
        ),
        if (eval['malso_date'] != null) ...[
          const SizedBox(height: 6),
          Text('말소기준일 후보: ${eval['malso_date']}'),
        ],
        if (flags.isNotEmpty) ...[
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            children: flags.map((f) => Chip(label: Text(f), visualDensity: VisualDensity.compact)).toList(),
          ),
        ],
        const SizedBox(height: 8),
        Text(
          eval['disclaimer'] as String? ??
              '법률 자문이 아닙니다. 자동평가는 입찰을 결정하지 않습니다.',
          style: const TextStyle(fontSize: 12),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          children: [
            FilledButton(
              onPressed: _busy ? null : () => _evaluate(),
              child: Text(_busy ? '평가 중…' : '타임라인 평가'),
            ),
            OutlinedButton(
              onPressed: _busy ? null : () => _evaluate(applyFinance: true),
              child: const Text('평가+인수금액 반영'),
            ),
          ],
        ),
        if (_msg != null) ...[
          const SizedBox(height: 6),
          Text(_msg!),
        ],
        const Divider(),
        const Text('타임라인', style: TextStyle(fontWeight: FontWeight.w700)),
        if (timeline.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text('권리·점유를 추가한 뒤 평가하세요.'),
          )
        else
          ...timeline.map((e) {
            final m = Map<String, dynamic>.from(e as Map);
            return ListTile(
              dense: true,
              leading: Text(m['date'] as String? ?? '—'),
              title: Text('${m['status']} · ${m['label']}'),
              subtitle: Text('${m['kind']} · ${m['track']}\n${m['note'] ?? ''}'),
              isThreeLine: true,
            );
          }),
        const Divider(),
        const Text('권리 추가', style: TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        Wrap(
          spacing: 6,
          children: [
            for (final k in const [
              'mortgage',
              'seize',
              'lease_reg',
              'tax',
              'other',
            ])
              ChoiceChip(
                label: Text(k),
                selected: _rightKind == k,
                onSelected: (_) => setState(() => _rightKind = k),
              ),
          ],
        ),
        TextField(
          controller: _rightLabel,
          decoration: const InputDecoration(labelText: '라벨'),
        ),
        TextField(
          controller: _rightAmount,
          decoration: const InputDecoration(labelText: '금액(원)'),
          keyboardType: TextInputType.number,
        ),
        TextField(
          controller: _rightDate,
          decoration: const InputDecoration(labelText: '등기·법정일 YYYY-MM-DD'),
        ),
        if (item.source == 'court')
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('말소기준권리로 지정'),
            value: _asBaseline,
            onChanged: (v) => setState(() => _asBaseline = v),
          ),
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.tonal(
            onPressed: _busy ? null : _addRight,
            child: const Text('권리 저장'),
          ),
        ),
        if (item.rights.isNotEmpty) ...[
          const SizedBox(height: 8),
          ...item.rights.map(
            (r) => ListTile(
              dense: true,
              title: Text(
                '${r['status']} · ${r['label']}'
                '${r['is_malso_baseline'] == true ? ' ★말소기준' : ''}',
              ),
              subtitle: Text(
                '${r['kind']} · ${r['event_date'] ?? '일자없음'} · '
                '${r['rule_track']}\n${r['notes'] ?? ''}',
              ),
              isThreeLine: true,
              trailing: IconButton(
                icon: const Icon(Icons.delete_outline),
                onPressed: _busy
                    ? null
                    : () async {
                        await ref
                            .read(apiProvider)
                            .deleteAnalysisRight(r['id'] as int);
                        ref.invalidate(_analysisProvider(widget.itemId));
                      },
              ),
            ),
          ),
        ],
        const Divider(),
        const Text('점유·임차 (주택/상가 분리)', style: TextStyle(fontWeight: FontWeight.w700)),
        Row(
          children: [
            ChoiceChip(
              label: const Text('주택'),
              selected: _occKind == 'housing',
              onSelected: (_) => setState(() => _occKind = 'housing'),
            ),
            const SizedBox(width: 8),
            ChoiceChip(
              label: const Text('상가'),
              selected: _occKind == 'commercial',
              onSelected: (_) => setState(() => _occKind = 'commercial'),
            ),
          ],
        ),
        TextField(
          controller: _occLabel,
          decoration: const InputDecoration(labelText: '점유자 라벨'),
        ),
        TextField(
          controller: _occDeposit,
          decoration: const InputDecoration(labelText: '보증금(원)'),
          keyboardType: TextInputType.number,
        ),
        if (_occKind == 'housing') ...[
          TextField(
            controller: _moveIn,
            decoration: const InputDecoration(labelText: '전입일 YYYY-MM-DD'),
          ),
          TextField(
            controller: _fixed,
            decoration: const InputDecoration(labelText: '확정일자 YYYY-MM-DD'),
          ),
        ] else ...[
          TextField(
            controller: _bizReg,
            decoration: const InputDecoration(labelText: '사업자등록일 YYYY-MM-DD'),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('세금계산서 등 요건 OK'),
            value: _taxOk,
            onChanged: (v) => setState(() => _taxOk = v),
          ),
        ],
        Align(
          alignment: Alignment.centerLeft,
          child: FilledButton.tonal(
            onPressed: _busy ? null : _addOcc,
            child: const Text('점유/임차 저장'),
          ),
        ),
        if (item.occupancies.isNotEmpty) ...[
          const SizedBox(height: 8),
          ...item.occupancies.map(
            (c) => ListTile(
              dense: true,
              title: Text('${c['status']} · ${c['claim_kind']} · ${c['occupant_label']}'),
              subtitle: Text(
                '보증금 ${c['deposit_won'] ?? '-'} · '
                '${c['move_in_date'] ?? c['business_reg_date'] ?? ''}\n'
                '${c['notes'] ?? ''}',
              ),
              isThreeLine: true,
              trailing: IconButton(
                icon: const Icon(Icons.delete_outline),
                onPressed: _busy
                    ? null
                    : () async {
                        await ref
                            .read(apiProvider)
                            .deleteAnalysisOccupancy(c['id'] as int);
                        ref.invalidate(_analysisProvider(widget.itemId));
                      },
              ),
            ),
          ),
        ],
        if (item.missingDocs.isNotEmpty) ...[
          const Divider(),
          ...item.missingDocs.map((d) => Text('· 필수문서 결여: $d')),
        ],
      ],
    );
  }
}

class _LoanTab extends ConsumerStatefulWidget {
  const _LoanTab({required this.item, required this.itemId});
  final AnalysisItemDetail item;
  final int itemId;

  @override
  ConsumerState<_LoanTab> createState() => _LoanTabState();
}

class _LoanTabState extends ConsumerState<_LoanTab> {
  late final TextEditingController _repair;
  late final TextEditingController _deposit;
  late final TextEditingController _exit;
  late final TextEditingController _tax;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final f = widget.item.finance;
    _repair = TextEditingController(text: '${f['repair_won'] ?? 0}');
    _deposit = TextEditingController(text: '${f['assume_deposit_won'] ?? 0}');
    _exit = TextEditingController(text: '${f['conservative_exit_won'] ?? ''}');
    _tax = TextEditingController(text: '${f['acquisition_tax_won'] ?? 0}');
  }

  @override
  void dispose() {
    _repair.dispose();
    _deposit.dispose();
    _exit.dispose();
    _tax.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      int? p(String s) => int.tryParse(s.replaceAll(',', ''));
      await ref.read(apiProvider).patchAnalysisFinance(widget.itemId, {
        'repair_won': p(_repair.text) ?? 0,
        'assume_deposit_won': p(_deposit.text) ?? 0,
        'conservative_exit_won': p(_exit.text),
        'acquisition_tax_won': p(_tax.text) ?? 0,
      });
      ref.invalidate(_analysisProvider(widget.itemId));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    final cost = item.costBreakdown;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          '총투입액 구성 (원)',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        ...[
          'bid_won',
          'assume_deposit_won',
          'assume_other_rights_won',
          'acquisition_tax_won',
          'vat_won',
          'registry_legal_won',
          'unpaid_mgmt_won',
          'repair_won',
          'eviction_won',
          'loan_interest_won',
          'disposal_cost_won',
          'contingency_won',
          'total_cost_won',
        ].map((k) => Text('$k: ${cost[k] ?? 0}')),
        const SizedBox(height: 12),
        const Text('대출 범위 (확정 아님 · RuleConfig)', style: TextStyle(fontWeight: FontWeight.w700)),
        ...item.loanScenarios.map(
          (s) => ListTile(
            dense: true,
            title: Text('${s['label']}'),
            subtitle: Text(
              '한도 ${formatManwon((s['max_loan_won'] as num?)?.round())} · '
              '필요현금 ${formatManwon((s['cash_needed_won'] as num?)?.round())}\n'
              '${s['is_range_note'] ?? ''}',
            ),
            isThreeLine: true,
          ),
        ),
        const Divider(),
        TextField(
          controller: _exit,
          decoration: const InputDecoration(labelText: '보수적 처분가 (원)'),
          keyboardType: TextInputType.number,
        ),
        TextField(
          controller: _deposit,
          decoration: const InputDecoration(labelText: '인수 임차보증금 (원)'),
          keyboardType: TextInputType.number,
        ),
        TextField(
          controller: _tax,
          decoration: const InputDecoration(
            labelText: '취득세 (원) — 0이면 UNKNOWN, 입찰 금지 요인',
          ),
          keyboardType: TextInputType.number,
        ),
        TextField(
          controller: _repair,
          decoration: const InputDecoration(labelText: '수리비 (원)'),
          keyboardType: TextInputType.number,
        ),
        const SizedBox(height: 8),
        FilledButton(
          onPressed: _busy ? null : _save,
          child: Text(_busy ? '계산 중…' : '저장·재계산'),
        ),
        const SizedBox(height: 16),
        const Text('What-if 시나리오', style: TextStyle(fontWeight: FontWeight.w700)),
        ...item.whatIf.entries.map((e) {
          final ceiling = (e.value as Map?)?['ceiling'] as Map?;
          return ListTile(
            dense: true,
            title: Text(e.key),
            subtitle: Text(
              '입찰상한 ${formatManwon((ceiling?['bid_ceiling_won'] as num?)?.round())}',
            ),
          );
        }),
      ],
    );
  }
}

class _MarketTab extends StatelessWidget {
  const _MarketTab({required this.item});
  final AnalysisItemDetail item;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          '시세·수익성 (Phase 1 stub)',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        const Text(
          '국토부 실거래·낙찰통계 연동은 Phase 5. 지금은 보수적 처분가와 총투입액·입찰상한으로 안전마진을 봅니다.',
        ),
        if (item.bidCeiling != null)
          Text('공식: ${item.bidCeiling!['formula']}'),
      ],
    );
  }
}

class _DocsTab extends ConsumerStatefulWidget {
  const _DocsTab({required this.item, required this.itemId});
  final AnalysisItemDetail item;
  final int itemId;

  @override
  ConsumerState<_DocsTab> createState() => _DocsTabState();
}

class _DocsTabState extends ConsumerState<_DocsTab> {
  bool _busy = false;
  String? _msg;
  Map<String, dynamic>? _selectedDoc;
  int _page = 1;

  Future<void> _upload({String? docType}) async {
    final pick = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf', 'txt'],
      withData: true,
    );
    if (pick == null || pick.files.isEmpty) return;
    final f = pick.files.first;
    final bytes = f.bytes;
    if (bytes == null) {
      setState(() => _msg = '웹에서는 파일 바이트를 읽지 못했습니다. 다시 시도하세요.');
      return;
    }
    setState(() {
      _busy = true;
      _msg = null;
    });
    try {
      await ref.read(apiProvider).uploadAnalysisDocument(
            widget.itemId,
            bytes: bytes,
            filename: f.name,
            docType: docType,
          );
      ref.invalidate(_analysisProvider(widget.itemId));
      setState(() => _msg = '업로드·추출·마스킹 완료');
    } catch (e) {
      setState(() => _msg = '실패: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openDoc(Map<String, dynamic> d) async {
    setState(() => _busy = true);
    try {
      final full = await ref.read(apiProvider).fetchAnalysisDocument(d['id'] as int);
      setState(() {
        _selectedDoc = full;
        _page = 1;
      });
    } catch (e) {
      setState(() => _msg = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _setType(String type) async {
    final id = _selectedDoc?['id'] as int?;
    if (id == null) return;
    setState(() => _busy = true);
    try {
      final updated = await ref.read(apiProvider).correctAnalysisDocument(
            id,
            docType: type,
            confirm: false,
          );
      setState(() => _selectedDoc = updated);
      ref.invalidate(_analysisProvider(widget.itemId));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _confirm() async {
    final id = _selectedDoc?['id'] as int?;
    if (id == null) return;
    setState(() => _busy = true);
    try {
      final updated = await ref.read(apiProvider).correctAnalysisDocument(
            id,
            confirm: true,
          );
      setState(() => _selectedDoc = updated);
      ref.invalidate(_analysisProvider(widget.itemId));
      setState(() => _msg = '문서 확인 처리됨 (confirmed_at)');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _attachRight() async {
    final id = _selectedDoc?['id'] as int?;
    if (id == null) return;
    setState(() => _busy = true);
    try {
      final ev = await ref.read(apiProvider).documentEvidence(id, page: _page);
      await ref.read(apiProvider).rightFromEvidence(
            widget.itemId,
            docId: id,
            page: _page,
            label: '${_selectedDoc?['doc_type']} p.$_page',
            kind: 'other',
          );
      ref.invalidate(_analysisProvider(widget.itemId));
      setState(() => _msg = '권리 항목 HOLD/UNKNOWN으로 연결 · 발췌 ${(ev['excerpt'] as String? ?? '').length}자');
    } catch (e) {
      setState(() => _msg = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    final pages = (_selectedDoc?['pages'] as List?) ?? const [];
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          '문서함 · PDF 업로드 / 유형 분류 / 페이지 근거 / 교정',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 6),
        Text(
          '주민번호·연락처는 저장 전 마스킹됩니다. 필수문서가 없으면 권리 확정·입찰이 막힙니다.',
          style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.6), fontSize: 12),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton.tonal(
              onPressed: _busy ? null : () => _upload(),
              child: Text(_busy ? '처리 중…' : 'PDF/TXT 업로드'),
            ),
            OutlinedButton(
              onPressed: _busy ? null : () => _upload(docType: 'registry'),
              child: const Text('등기로 업로드'),
            ),
            OutlinedButton(
              onPressed: _busy ? null : () => _upload(docType: 'appraisal'),
              child: const Text('감정으로 업로드'),
            ),
          ],
        ),
        if (_msg != null) ...[
          const SizedBox(height: 8),
          Text(_msg!),
        ],
        const SizedBox(height: 12),
        Text('결여: ${item.missingDocs.join(', ').ifEmpty('없음')}'),
        const Divider(),
        if (item.documents.isEmpty)
          const Text('등록된 문서 없음')
        else
          ...item.documents.map((d) {
            return ListTile(
              dense: true,
              title: Text('${d['doc_type']} · ${d['filename']}'),
              subtitle: Text(
                'p.${d['page_count']} · 확신 ${d['classify_confidence']}'
                '${d['masked'] == true ? ' · 마스킹됨' : ''}'
                '${d['confirmed_at'] != null ? ' · 확인됨' : ''}\n'
                '${d['classify_note'] ?? ''}',
              ),
              isThreeLine: true,
              onTap: () => _openDoc(d),
            );
          }),
        if (_selectedDoc != null) ...[
          const Divider(),
          Text(
            '선택 문서: ${_selectedDoc!['filename']}',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            children: [
              for (final t in const [
                'registry',
                'appraisal',
                'sale_spec',
                'onbid_notice',
                'other',
              ])
                ChoiceChip(
                  label: Text(t),
                  selected: _selectedDoc!['doc_type'] == t,
                  onSelected: (_) => _setType(t),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              const Text('페이지'),
              const SizedBox(width: 8),
              DropdownButton<int>(
                value: _page.clamp(1, (pages.isEmpty ? 1 : pages.length)),
                items: [
                  for (var i = 1; i <= (pages.isEmpty ? 1 : pages.length); i++)
                    DropdownMenuItem(value: i, child: Text('$i')),
                ],
                onChanged: (v) => setState(() => _page = v ?? 1),
              ),
              const Spacer(),
              TextButton(onPressed: _busy ? null : _confirm, child: const Text('문서 확인')),
              FilledButton(
                onPressed: _busy ? null : _attachRight,
                child: const Text('이 페이지→권리 연결'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (pages.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                border: Border.all(color: AppTheme.line),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                (() {
                  final hit = pages.cast<dynamic>().firstWhere(
                        (p) => (p as Map)['page'] == _page,
                        orElse: () => pages.first,
                      ) as Map;
                  return (hit['text_preview'] as String?) ?? '';
                })(),
                style: const TextStyle(fontSize: 12, height: 1.35),
              ),
            ),
        ],
        if (item.rights.isNotEmpty) ...[
          const Divider(),
          const Text('근거 연결 권리', style: TextStyle(fontWeight: FontWeight.w700)),
          ...item.rights.map(
            (r) => ListTile(
              dense: true,
              title: Text('${r['status']} · ${r['label']}'),
              subtitle: Text(
                'doc=${r['evidence_doc_id']} p.${r['evidence_page']}\n'
                '${r['evidence_excerpt'] ?? ''}',
              ),
              isThreeLine: true,
            ),
          ),
        ],
      ],
    );
  }
}

class _SiteTab extends StatelessWidget {
  const _SiteTab({required this.item});
  final AnalysisItemDetail item;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: const [
        Text(
          '현장조사 체크 (초안)',
          style: TextStyle(fontWeight: FontWeight.w700),
        ),
        SizedBox(height: 8),
        Text('· 점유·사용 상태 사진'),
        Text('· 누수·불법건축·주차'),
        Text('· 관리비 체납 확인'),
        Text('· 주변 시세 체감'),
        Text('현장조사 메모는 다음 단계에서 저장합니다. 권리·점유는 「권리」탭에서 평가하세요.'),
      ],
    );
  }
}

class _GuideTab extends StatelessWidget {
  const _GuideTab({required this.source});
  final String source;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          source == 'court' ? '법원경매 초보 순서' : '온비드공매 초보 순서',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
        ),
        const SizedBox(height: 8),
        const Text('1. 공식 문서 수집'),
        const Text('2. 권리 (근거 없으면 UNKNOWN)'),
        const Text('3. 점유 (주택/상가 입력 분리)'),
        const Text('4. 대출 범위 (RuleConfig)'),
        const Text('5. 필요현금'),
        const Text('6. 총투입액'),
        const Text('7. 적정 입찰 상한'),
        const Text('8. 현장조사'),
        const SizedBox(height: 12),
        TextButton(
          onPressed: () => context.push('/guide'),
          child: const Text('앱 초보 가이드 열기'),
        ),
      ],
    );
  }
}

extension on String {
  String ifEmpty(String alt) => isEmpty ? alt : this;
}
