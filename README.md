# ⚾ KBO 리그 데이터 대시보드

수업용 KBO 선수 데이터(2001~2025) 탐색 대시보드입니다. 

## 폴더 구조
```
kbo_dashboard/
├── app.py                     # 🏠 홈: 데이터 소개
├── requirements.txt
├── data/
│   └── kbo_clean.dta           # 선수-시즌 단위 정제 데이터 (학생 배포용, variable label 부착)
├── utils/
│   ├── data_loader.py          # 데이터 로딩/캐싱/파생변수(K9·BB9는 클리닝 단계에서 이미 계산됨)
│   ├── style.py                # 공통 Plotly 스타일 (검은 글씨 고정 등)
│   └── glossary.py             # 통계 용어 설명(글로서리)
└── pages/
    ├── 1_기초통계.py            # 타자/투수 탭: 기술통계표, 히스토그램, 박스플롯, 표본기준 민감도
    ├── 2_상관관계.py            # 타자/투수 탭: 상관관계, 팀별·시대별 비교(평균±95%CI, ANOVA)
    ├── 3_선수검색.py            # 개인 커리어: KPI 카드, 추이(통산평균·리그평균·최고시즌 표시)
    ├── 4_랭킹.py                # 타자/투수 탭: 순위 테이블 + 지표별 Top 10 막대
    ├── 5_선수비교.py            # 1:1 Head-to-Head 레이더 비교
    ├── 6_리그트렌드.py          # 리그 전체 시대 흐름(타고투저/투고타저)
    └── 7_승률시뮬레이터.py      # 피타고리안 승률
```

## 로컬 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 배포
1. 이 폴더 전체를 GitHub 저장소에 업로드 (data/kbo_clean.dta 포함)
2. share.streamlit.io에서 저장소 연결, main file은 `app.py`로 지정

## 데이터 안내
- `data/kbo_clean.dta`는 이미 정제 완료된 최종 데이터입니다 (선수-시즌 1행 병합,
  이닝·비율 지표 숫자 변환, 구단명 매핑, K9/BB9 계산 등).
- ⚠️ 현대(2001~2007) 소속 선수 일부는 OPS/OBP/SLG/BB가 결측입니다. KBO 공식 세부기록
  페이지가 해체 구단인 현대의 타자 세부기록을 제공하지 않기 때문입니다(원자료 자체의 한계이며,
  전체 관측치 대비 극소수입니다).
