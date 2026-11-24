import plotly.express as px

COLORS=["#38BDF8","#6366F1","#22C55E","#F59E0B","#EF4444","#A78BFA"]

def style(fig, height=380):
    fig.update_layout(template="plotly_dark",paper_bgcolor="#111827",plot_bgcolor="#111827",font_color="#E2E8F0",
                      colorway=COLORS,height=height,margin=dict(l=25,r=20,t=55,b=30),legend_title_text="")
    return fig

