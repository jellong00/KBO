# ⚾ KBO 기록 분석 대시보드


## 실행 방법

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

`data/KBO.dta` 파일이 필요합니다. 이 배포 묶음에는 제공된 데이터셋이 포함되어 있습니다.

## 구조

```text
kbo_streamlit_dashboard/
├── app.py
├── data/KBO.dta
├── pages/
│   ├── 1_리그_개요.py
│   ├── 2_타자_분석.py
│   ├── 3_투수_분석.py
│   ├── 4_선수_탐색.py
│   └── 5_확률_시뮬레이터.py
├── utils/
│   ├── __init__.py
│   ├── data.py
│   └── ui.py
└── requirements.txt
```
