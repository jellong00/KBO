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
  1_Player_Search.py          # 선수 검색 → 통산 추이(Line) + 포지션 대비 백분위 레이더
  2_Batter_Rank.py            # 타자 랭킹 + 세이버메트릭스 버블차트 + 주루 4분면 + 수비율 바이올린
  3_Pitcher_Rank.py           # 투수 랭킹 + K9 혼합차트(Bar+Line) + 3D 구위 분석(SO·BB·ERA)
  4_Team_Analysis.py          # 구단 요약 + 승리기여 투수 Top5 / 홈런 타자 Top5
  5_Head_to_Head.py           # 1:1 선수 비교 (중첩 레이더 차트)
utils/
  data_loader.py              # .dta 로드 및 전처리, 파생 세이버메트릭스 계산
  style.py                    # Plotly 공통 레이아웃/색상 테마
requirements.txt
```

## 세이버메트릭스 추정치에 관한 유의사항

이 데이터셋에는 타자의 볼넷(BB)·사구(HBP) 컬럼이 별도로 존재하지 않습니다.
`hit_PA = AB + BB + HBP + SF + SAC` 공식을 역이용해
`BB+HBP ≈ PA - AB - SF - SAC` 로 근사한 뒤 출루율(OBP)/OPS/wOBA를 추정합니다.
실제 공식 기록과 다소 차이가 있을 수 있으며, 대시보드 내 해당 지표 옆에 "(추정)" 표기와 안내 문구를 함께 표시했습니다.

## 규정 타석/이닝 관련 유의사항

KBO의 공식 규정 타석/이닝 기준은 시즌별 경기 수(126경기~144경기 등 시대별 상이)에 따라 달라집니다.
이 대시보드에서는 별도의 공식 계수를 하드코딩하는 대신, 사용자가 직접 조정할 수 있는 슬라이더/체크박스(상위 %ile 기준)를 제공합니다.
