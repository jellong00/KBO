"""
style.py
--------
모든 페이지에서 공통으로 사용하는 Plotly 레이아웃 스타일 및 색상 팔레트.
"""

PLOTLY_TEMPLATE = "plotly_white"

COLOR_SEQUENCE = [
    "#2563EB", "#F97316", "#10B981", "#EF4444", "#8B5CF6",
    "#F59E0B", "#06B6D4", "#EC4899", "#84CC16", "#6366F1",
]

FONT_FAMILY = "Pretendard, 'Noto Sans KR', -apple-system, sans-serif"


def apply_common_layout(fig, title=None, height=480, legend_title=None):
    """모든 차트에 공통으로 적용하는 모던/클린 레이아웃."""
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        font=dict(family=FONT_FAMILY, size=13, color="#1F2937"),
        title=dict(text=title, font=dict(size=18, family=FONT_FAMILY, color="#111827")) if title else None,
        height=height,
        margin=dict(l=40, r=30, t=60 if title else 30, b=40),
        hoverlabel=dict(
            bgcolor="white",
            font_size=13,
            font_family=FONT_FAMILY,
            bordercolor="#E5E7EB",
        ),
        legend=dict(
            title=legend_title,
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        colorway=COLOR_SEQUENCE,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#F1F5F9", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9", zeroline=False)
    return fig
