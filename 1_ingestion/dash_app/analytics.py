from pathlib import Path
import json

import dash
from dash import Input, Output, dcc, html, dash_table
import pandas as pd
import plotly.express as px


DATA_PATH = Path(__file__).with_name("ml_zoomcamp_metadata.json")


def load_data() -> pd.DataFrame:
    with DATA_PATH.open("r") as f:
        metadata = json.load(f)

    rows = [
        {
            "id": item["id"],
            "title": item["title"],
            "duration": item["duration"],
            "view_count": item["view_count"],
            "url": item.get("url"),
        }
        for item in metadata
    ]

    df = pd.DataFrame(rows)

    df["cleaned_title"] = df["title"]

    phrases_to_remove = ["ML Zoomcamp 2025", "ML Zoomcamp "]
    for phrase in phrases_to_remove:
        df["cleaned_title"] = df["cleaned_title"].str.replace(
            phrase,
            "",
            regex=False,
        )

    df["module"] = df["cleaned_title"].str.extract(r"^(\d+)")

    # Match notebook logic: first two videos are pre-course/module 0.
    df.loc[[0, 1], "module"] = "0"

    # Notebook used 11 for the Kubernetes video or uncategorized items.
    df["module"] = df["module"].fillna(11).astype(int)

    df["duration_minutes"] = (df["duration"] / 60).round(1)

    return df


df = load_data()
modules = sorted(df["module"].unique())

app = dash.Dash(__name__)
server = app.server

app.layout = html.Div(
    style={
        "fontFamily": "Arial, sans-serif",
        "maxWidth": "1200px",
        "margin": "0 auto",
        "padding": "24px",
    },
    children=[
        html.H1("ML Zoomcamp Video Analytics"),

        html.Div(
            style={
                "display": "grid",
                "gridTemplateColumns": "repeat(3, 1fr)",
                "gap": "16px",
                "marginBottom": "24px",
            },
            children=[
                html.Div(id="video-count"),
                html.Div(id="total-duration"),
                html.Div(id="total-views"),
            ],
        ),

        html.Label("Filter by module"),
        dcc.Checklist(
            id="module-filter",
            options=[
                {"label": f"Module {module}", "value": module}
                for module in modules
            ],
            value=modules,
            inline=True,
            style={"marginBottom": "24px"},
        ),

        dcc.Tabs(
            value="duration",
            children=[
                dcc.Tab(label="Duration", value="duration"),
                dcc.Tab(label="View Count", value="views"),
                dcc.Tab(label="Correlation", value="correlation"),
                dcc.Tab(label="Data", value="data"),
            ],
            id="tabs",
        ),

        html.Div(id="tab-content", style={"marginTop": "24px"}),
    ],
)


def metric_card(label: str, value: str) -> html.Div:
    return html.Div(
        style={
            "border": "1px solid #ddd",
            "borderRadius": "6px",
            "padding": "16px",
            "background": "#fafafa",
        },
        children=[
            html.Div(label, style={"fontSize": "14px", "color": "#555"}),
            html.Div(value, style={"fontSize": "28px", "fontWeight": "700"}),
        ],
    )


@app.callback(
    Output("video-count", "children"),
    Output("total-duration", "children"),
    Output("total-views", "children"),
    Output("tab-content", "children"),
    Input("module-filter", "value"),
    Input("tabs", "value"),
)
def update_dashboard(selected_modules, selected_tab):
    filtered = df[df["module"].isin(selected_modules)]

    video_count = metric_card("Videos", f"{len(filtered):,}")
    total_duration = metric_card(
        "Total duration",
        f"{filtered['duration_minutes'].sum():,.1f} min",
    )
    total_views = metric_card(
        "Total views",
        f"{filtered['view_count'].sum():,}",
    )

    if selected_tab == "duration":
        fig = px.box(
            filtered,
            x="module",
            y="duration_minutes",
            color="module",
            hover_name="title",
            points="all",
            labels={
                "module": "Module",
                "duration_minutes": "Duration, minutes",
            },
            title="Video Duration by Module",
        )
        content = dcc.Graph(figure=fig)

    elif selected_tab == "views":
        fig = px.box(
            filtered,
            x="module",
            y="view_count",
            color="module",
            hover_name="title",
            points="all",
            labels={
                "module": "Module",
                "view_count": "View count",
            },
            title="View Count by Module",
        )
        content = dcc.Graph(figure=fig)

    elif selected_tab == "correlation":
        fig = px.scatter(
            filtered,
            x="duration_minutes",
            y="view_count",
            color="module",
            hover_name="title",
            hover_data={
                "duration_minutes": True,
                "view_count": True,
                "title": False,
            },
            labels={
                "duration_minutes": "Duration, minutes",
                "view_count": "View count",
                "module": "Module",
            },
            title="Duration vs View Count",
        )
        content = dcc.Graph(figure=fig)

    else:
        table_df = filtered[
            [
                "title",
                "duration_minutes",
                "view_count",
                "module",
                "url",
            ]
        ].sort_values(["module", "title"])

        content = dash_table.DataTable(
            data=table_df.to_dict("records"),
            columns=[
                {"name": "Title", "id": "title"},
                {"name": "Duration (minutes)", "id": "duration_minutes"},
                {"name": "View Count", "id": "view_count"},
                {"name": "Module", "id": "module"},
                {"name": "URL", "id": "url"},
            ],
            page_size=15,
            sort_action="native",
            filter_action="native",
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "padding": "8px",
                "whiteSpace": "normal",
                "height": "auto",
            },
            style_header={"fontWeight": "700", "backgroundColor": "#f2f2f2"},
        )

    return video_count, total_duration, total_views, content



if __name__ == "__main__":
    app.run(debug=True)