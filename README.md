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
│   ├── data_loader.py          # 데이터 로딩/캐싱/파생변수
│   ├── style.py                # 공통 Plotly 스타일
│   └── glossary.py             # 통계 용어 설명(글로서리)
└── pages/
    ├── 1_기초통계.py            # 평균/중앙값/분포/이상치
    ├── 2_선수검색.py            # 개인 커리어 추이 + 레이더
    ├── 3_랭킹.py                # 타자/투수 탭 랭킹
    ├── 4_선수비교.py            # 1:1 Head-to-Head
    ├── 5_리그트렌드.py          # 리그 전체 시대 흐름
    └── 6_승률시뮬레이터.py      # 피타고리안 승률
```

## 로컬 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 배포
1. 이 폴더 전체를 GitHub 저장소에 업로드 (data/ 폴더의 parquet 파일 포함)
2. share.streamlit.io에서 저장소 연결, main file은 `app.py`로 지정

## 원본 데이터 재생성이 필요하면
`clean_data.py`가 `KBO.dta` 원본을 읽어서 `data/kbo_clean.dta`를 다시 만듭니다.
(중복 포지션 행 병합, 문자열 숫자 컬럼 변환, 구단명 매핑, Stata variable label 부착 로직 포함)
