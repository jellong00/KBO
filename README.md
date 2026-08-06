# ⚾ KBO 기록 분석 대시보드

Streamlit + Plotly 기반 KBO 선수 기록 분석 대시보드입니다.

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 데이터

`data/KBO.dta` 경로에 데이터 파일을 위치시켜야 합니다. (이미 포함되어 있다면 그대로 사용)

## 구조

```
app.py                        # 메인 홈 (시즌 KPI, 타율vs홈런 / ERA vs WHIP 산점도)
pages/
  1_Player_Search.py          # 선수 선택(구단→포지션→선수, 검색 병행) → 통산 추이(소multiples) + 포지션 대비 백분위 레이더
  2_Batter_Rank.py            # 타자 순위 테이블 + wOBA 랭킹 바차트 + 주루 4분면 + 포지션별 수비율 Box Plot
  3_Pitcher_Rank.py           # 투수 순위 테이블 + K9 혼합차트(Bar+Line) + 3D 구위 분석(SO·BB·ERA)
  4_Team_Analysis.py          # 구단 요약 + 승리기여 투수 Top5 / 홈런 타자 Top5 + 전체 구단 성적 비교
  5_Head_to_Head.py           # 1:1 선수 비교 (출전 선수만 필터링, 중첩 레이더 차트, 한글 라벨 비교표)
  6_League_Trends.py          # [심화] 리그 타고/투고 추이, 구단 타율-홈런 애니메이션, 구단별 ERA 히트맵, 역대 리더보드
utils/
  data_loader.py              # .dta 로드/전처리, 포지션 중복행 병합(선수-시즌 단위 dedup), 파생 세이버메트릭스 계산
  style.py                    # Plotly 공통 레이아웃/색상 테마 (범례 글자색 등)
  glossary.py                 # ERA/WHIP 등 지표 약어에 대한 한글 설명 모음 (화면 expander로도 노출)
requirements.txt
```

## 데이터 업데이트 (KBO_1.dta 반영)

기존 KBO.dta에 누락되어 있던 기록을 보완한 새 데이터(KBO_1.dta, 90개 컬럼)로 교체했습니다.
`data/KBO.dta`가 바로 이 새 데이터입니다. 주요 추가 변수:
- 타자: 볼넷(hit_BB, 2001년만), 사구(hit_HBP, 2001년만), **출루율/장타율/OPS(2002~2025년 실제 제공값)**,
  득점권타율(hit_RISP), 대타타율(hit_PH_BA) 등
- 투수: 땅볼/뜬공비율(pit_GO_AO), BABIP(pit_BABIP), 세이브기회(pit_SVO), 선발/구원승(pit_Wgs/pit_Wgr),
  이미 계산된 K/9·BB/9(pit_K_9, pit_BB_9), 피출루율/피장타율/피OPS 등

이에 따라 `utils/data_loader.py`의 출루율/OPS/wOBA 계산 로직이 개선되었습니다:
실제 제공된 값(hit_OBP/SLG/OPS) → 있으면 그대로 사용 → 없으면 실제 볼넷/사구로 직접 계산(2001년) →
그마저 없으면 이전처럼 PA 기반 근사치. 대부분의 시즌(2002~2025)은 이제 추정이 아닌 실제 제공값을 사용합니다.

## 데이터 처리에 관한 중요 노트: 포지션 중복행 병합

원본 KBO.dta는 한 선수가 시즌 중 여러 포지션을 겸하면, 완전히 같은 타격 기록이 포지션 개수만큼
반복된 행으로 저장되어 있습니다 (예: 좌익수/우익수를 겸한 선수는 타격 기록이 똑같은 행이 2번 등장).
`utils/data_loader.py`의 `load_data()`는 이를 자동으로 감지해 선수-시즌(-팀) 단위 한 줄로 합치고,
겸한 포지션은 `def_POS` 컬럼에 `좌익수/우익수`처럼 표기합니다. (포지션별 수비 기록처럼 포지션 단위
구분이 꼭 필요한 분석에서는 `load_position_level_data()`로 원본 그래뉼래러티를 그대로 사용합니다.)
이 병합 덕분에 순위/집계 차트에서 같은 선수가 여러 번 중복 표기되던 문제가 해결되었습니다.

## 세이버메트릭스 추정치에 관한 유의사항

이 데이터셋에는 타자의 볼넷(BB)·사구(HBP) 컬럼이 별도로 존재하지 않습니다.
`hit_PA = AB + BB + HBP + SF + SAC` 공식을 역이용해
`BB+HBP ≈ PA - AB - SF - SAC` 로 근사한 뒤 출루율(OBP)/OPS/wOBA를 추정합니다.
실제 공식 기록과 다소 차이가 있을 수 있으며, 대시보드 내 해당 지표 옆에 "(추정)" 표기와 안내 문구를 함께 표시했습니다.

## 배포 시 알려진 이슈 (해결됨)

Streamlit Community Cloud에 배포 시 헬스체크가 500 에러를 반환하며 배포가 실패하는 경우가 있었습니다.
원인은 최신 `starlette`(1.4.0)에서 `GZipResponder`에 `thread_minimum_size`라는 필수 키워드 인자가 추가되었는데,
Streamlit 1.60.0/1.61.0의 자체 gzip 미들웨어 래퍼(`MediaAwareGZipMiddleware`)가 이 인자를 전달하지 않아
`Accept-Encoding: gzip` 헤더가 포함된 요청(브라우저/헬스체크 등)에서 예외가 발생하는 **Streamlit 자체의 호환성 버그**였습니다.
`requirements.txt`에 `starlette<1.4`를 명시해 이전 버전으로 고정함으로써 해결했습니다.
(추후 Streamlit이 패치를 배포하면 이 핀을 제거해도 됩니다.)

## 규정 타석/이닝 관련 유의사항

KBO의 공식 규정 타석/이닝 기준은 시즌별 경기 수(126경기~144경기 등 시대별 상이)에 따라 달라집니다.
이 대시보드에서는 별도의 공식 계수를 하드코딩하는 대신, 사용자가 직접 조정할 수 있는 슬라이더/체크박스(상위 %ile 기준)를 제공합니다.
