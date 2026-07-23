from app.ingest.onbid_html import build_bid_history_notes, parse_bid_history_html


SAMPLE = """
<h2 class="tit">이전 입찰내역</h2>
<ul class="before_bid_box01">
  <li class="item"><span class="tit01">이전 입찰 결과</span><span class="txt01">유찰</span></li>
  <li class="item"><span class="tit01">이전 입찰 최저입찰가격</span><span class="txt01">201,000,000원</span></li>
  <li class="item"><span class="tit01">전체 입찰내역</span><span class="txt01">유찰 2회 / 취소 1회</span></li>
</ul>
<div class="bid_history_box01">
  <div class="history_item">
    <div class="history_stat"><span class="stat_txt01">낙찰</span></div>
    <span class="history_stat_date">개찰일시 : 2025-04-03 11:00</span>
    <ul class="dot_list01">
      <li><span class="tit01">회차</span><span class="txt01">012/001</span></li>
      <li><span class="tit01">공매예정가격</span><span class="txt01">241,200,000원</span></li>
      <li><span class="tit01">낙찰금액</span><span class="txt02">241,400,000원(100.08%)</span></li>
    </ul>
    <button type="button">상세보기</button>
  </div>
  <div class="history_item">
    <div class="history_stat"><span class="stat_txt01">유찰</span></div>
    <span class="history_stat_date">개찰일시 : 2024-08-16 11:00</span>
    <ul class="dot_list01">
      <li><span class="tit01">회차</span><span class="txt01">034/001</span></li>
      <li><span class="tit01">공매예정가격</span><span class="txt01">281,400,000원</span></li>
      <li><span class="tit01">낙찰금액</span><span class="txt02">-</span></li>
    </ul>
    <button type="button">상세보기</button>
  </div>
</div>
인근 시세
"""


def test_parse_bid_history_with_win_and_fail():
    hist = parse_bid_history_html(SAMPLE)
    assert hist["summary"] == "유찰 2회 / 취소 1회"
    assert len(hist["rounds"]) == 2
    assert hist["rounds"][0]["result"] == "낙찰"
    assert hist["rounds"][0]["win_manwon"] == 24140
    assert hist["rounds"][1]["result"] == "유찰"
    assert any("낙찰 이후" in n for n in hist["notes"])


def test_build_notes_cancel_mix():
    notes = build_bid_history_notes(
        [
            {"result": "유찰", "open_at": "2024-01-01", "round_label": "1"},
            {"result": "취소", "open_at": "2024-02-01", "round_label": "2"},
        ],
        summary="유찰 1회 / 취소 1회",
    )
    assert any("취소" in n for n in notes)
