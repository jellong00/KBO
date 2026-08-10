"""
utils/style.py
----------------
모든 페이지에서 공통으로 쓰는 Plotly 레이아웃 스타일과 색상 팔레트.
"""

COLOR_SEQUENCE = [
    "#2563EB",  # blue
    "#F97316",  # orange
    "#10B981",  # green
    "#EF4444",  # red
    "#8B5CF6",  # violet
    "#F59E0B",  # amber
    "#06B6D4",  # cyan
    "#EC4899",  # pink
    "#84CC16",  # lime
    "#6366F1",  # indigo
]


def apply_common_layout(fig, title=None, height=None):
    """모든 차트에 일관된 폰트/배경/여백 스타일 적용 (검은 글씨 강제)"""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Pretendard, Malgun Gothic, sans-serif", size=13, color="#111827"),
        title=dict(text=title, font=dict(size=16, color="#111827")) if title else None,
        margin=dict(l=40, r=30, t=60 if title else 30, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color="#111827")),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(showgrid=True, gridcolor="#F1F5F9", zeroline=False,
                      tickfont=dict(color="#111827"), title_font=dict(color="#111827"))
    fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9", zeroline=False,
                      tickfont=dict(color="#111827"), title_font=dict(color="#111827"))
    # 레이더/극좌표 차트도 검은 글씨로
    fig.update_polars(
        radialaxis=dict(tickfont=dict(color="#374151")),
        angularaxis=dict(tickfont=dict(color="#111827")),
    )
    return fig
