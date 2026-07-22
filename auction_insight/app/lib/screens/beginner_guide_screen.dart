import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:auction_insight_app/theme.dart';

/// Beginner-oriented playbook for onbid / auction research.
/// Educational only — not legal advice.
class BeginnerGuideScreen extends StatelessWidget {
  const BeginnerGuideScreen({super.key});

  Future<void> _open(String url) async {
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('초보 가이드')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 40),
        children: [
          Text(
            '경·공매, 뭐부터 보면 될까',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: AppTheme.ink,
              letterSpacing: -0.4,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '이 앱은 온비드 공매 데이터를 지도·시세·권리 요약으로 보여줍니다. '
            '법률 자문이나 확정 권리분석이 아닙니다.',
            style: TextStyle(
              height: 1.45,
              color: AppTheme.ink.withValues(alpha: 0.65),
            ),
          ),
          const SizedBox(height: 22),
          _h('1. 온비드에서 볼 수 있는 것'),
          _p(
            '물건목록·물건상세로 주소, 용도, 감정가, 최저가, 유찰, 이용현황, '
            '명도책임, 임대차·점유·등기 관련 목록, 감정평가서 링크를 받을 수 있습니다.',
          ),
          _p(
            '회차별 입찰 참여팀 수·개찰 상세는 별도 API 활용신청이 필요한 경우가 많습니다.',
          ),
          const SizedBox(height: 16),
          _h('2. 앱만으로 부족한 것'),
          _bullet('실제 최신 등기부등본 (갑구·을구)'),
          _bullet('말소기준권리 / 인수 vs 말소 최종 판단'),
          _bullet('유치권·법정지상권 확정 (감정평가서·현장·등기 교차확인)'),
          _bullet('법원 경매 전용 권리분석 (공매와 절차가 다름)'),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => _open('https://www.iros.go.kr'),
            icon: const Icon(Icons.account_balance_outlined),
            label: const Text('인터넷등기소에서 등기 열람'),
          ),
          const SizedBox(height: 22),
          _h('3. 초보가 따라할 전략 (실무 순서)'),
          _step(
            '① 후보 좁히기',
            '지역·용도·예산으로 후보를 고르고, 유찰만 보고 고르지 마세요.',
          ),
          _step(
            '② 권리 레드플래그',
            '유치권·가처분·가등기·법정지상권·복잡한 임차면 초보 단계에서는 보류.',
          ),
          _step(
            '③ 필수 3종 세트',
            '등기부등본 + 감정평가서 + 온비드 원문 특약(명도·부대조건).',
          ),
          _step(
            '④ 총원가 계산',
            '낙찰예정가 + 취득세·중개·명도·수리·미납관리비까지 합산.',
          ),
          _step(
            '⑤ 시세 안전마진',
            '국토부 시세·실거래와 비교해 “팔려도 남는가”를 확인.',
          ),
          _step(
            '⑥ 입찰 전날 재확인',
            '등기·공고가 바뀌었을 수 있습니다. 원문과 등기를 다시 엽니다.',
          ),
          const SizedBox(height: 22),
          _h('4. 물건 상세에서 보는 법'),
          _p('· 권리 칩: 키워드 경고 (확정 아님)'),
          _p('· 임대차/점유/등기 목록: 온비드가 준 공고 요약 행'),
          _p('· 체크리스트: 입찰 전 할 일'),
          _p('· 전략 팁: 그 물건 상황에 맞춘 초보용 메모'),
          const SizedBox(height: 22),
          _h('5. 안전한 마음가짐'),
          _p(
            '한 건을 깊게 보는 편이, 열 건을 대충 보는 것보다 낫습니다. '
            '확신이 없으면 입찰하지 않는 것도 전략입니다.',
          ),
          const SizedBox(height: 12),
          Text(
            '면책: 본 가이드와 앱 정보는 참고용이며, 투자·법률 자문이 아닙니다.',
            style: TextStyle(
              fontSize: 11,
              height: 1.4,
              color: AppTheme.ink.withValues(alpha: 0.4),
            ),
          ),
        ],
      ),
    );
  }

  Widget _h(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(
          t,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
      );

  Widget _p(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(
          t,
          style: TextStyle(
            height: 1.45,
            color: AppTheme.ink.withValues(alpha: 0.72),
          ),
        ),
      );

  Widget _bullet(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 6, left: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('· ', style: TextStyle(color: AppTheme.ink.withValues(alpha: 0.5))),
            Expanded(child: _p(t)),
          ],
        ),
      );

  Widget _step(String title, String body) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.7),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppTheme.line),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text(
              body,
              style: TextStyle(
                height: 1.4,
                fontSize: 13,
                color: AppTheme.ink.withValues(alpha: 0.65),
              ),
            ),
          ],
        ),
      );
}
