import os
import pandas as pd
import dash
from dash import dcc, html, dash_table, Input, Output
import plotly.express as px

# --------------------------
# Auto-increment version
# --------------------------
VERSION_FILE = "version.txt"

def get_next_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            number = int(f.read().strip())
    else:
        number = 0
    number += 1
    with open(VERSION_FILE, "w") as f:
        f.write(str(number))
    return f"beta_{number}"

VERSION_STRING = get_next_version()
print(f"🚀 Starting Student Risk Dashboard... Version: {VERSION_STRING}")

DATA_PATH = "data"

# --------------------------
# Helper to safely load CSV
# --------------------------
def safe_load_csv(filename, rename_cols=None, required_cols=None):
    filepath = os.path.join(DATA_PATH, filename)
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        if rename_cols:
            df = df.rename(columns=rename_cols)
        if required_cols:
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 0
        return df
    else:
        cols = list(rename_cols.values()) if rename_cols else required_cols
        return pd.DataFrame(columns=cols)

# --------------------------
# Load CSVs
# --------------------------
students = safe_load_csv("students.csv", rename_cols={"full_name": "name"}, required_cols=["student_id","name"])
attendance = safe_load_csv("attendance.csv", required_cols=["student_id","attendance_percentage"])
tests = safe_load_csv("tests.csv", rename_cols={"test_score":"score"}, required_cols=["student_id","score"])
fees = safe_load_csv("fees.csv", rename_cols={"pending_amount": "due_amount"}, required_cols=["student_id", "due_amount"])

# --------------------------
# Aggregate
# --------------------------
att_agg = attendance.groupby("student_id")["attendance_percentage"].mean().reset_index()
tests_agg = tests.groupby("student_id")["score"].mean().reset_index().rename(columns={"score":"avg_score"})
fees_agg = fees.groupby("student_id")["due_amount"].max().reset_index()

# --------------------------
# Merge
# --------------------------
merged = students.merge(att_agg, on="student_id", how="left")
merged = merged.merge(tests_agg, on="student_id", how="left")
merged = merged.merge(fees_agg, on="student_id", how="left")
merged = merged.fillna(0)

# --------------------------
# Ensure numeric types
# --------------------------
merged["attendance_percentage"] = pd.to_numeric(merged["attendance_percentage"], errors="coerce").fillna(0)
merged["avg_score"] = pd.to_numeric(merged["avg_score"], errors="coerce").fillna(0)
merged["due_amount"] = pd.to_numeric(merged["due_amount"], errors="coerce").fillna(0)

# --------------------------
# Risk rules
# --------------------------
def risk_status(row):
    reasons = []
    if row["attendance_percentage"] < 75:
        reasons.append("Low Attendance")
    elif row["attendance_percentage"] >= 90:
        reasons.append("Excellent Attendance ✅")
    if row["avg_score"] < 40:
        reasons.append("Low Test Score")
    elif row["avg_score"] >= 80:
        reasons.append("Strong Test Score ✅")
    if row["due_amount"] > 0:
        reasons.append("Pending Fees")
    if not reasons:
        return "Safe", "No issues"
    else:
        return "At Risk", "; ".join(reasons)

merged[["status", "reasons"]] = merged.apply(risk_status, axis=1, result_type="expand")

# --------------------------
# Dash App
# --------------------------
app = dash.Dash(__name__)
app.title = "Student Risk Dashboard"

app.layout = html.Div(
    style={"fontFamily": "Arial", "margin": "20px"},
    children=[
        html.H1("🎓 Student Risk Dashboard", style={"textAlign": "center"}),

        # Search bar full width
        dcc.Input(
            id="search-box",
            type="text",
            placeholder="Search by Name or ID...",
            style={"width":"100%","padding":"10px","marginBottom":"20px","borderRadius":"8px","fontSize":"16px"}
        ),

        # Filters
        html.Div(
            style={"display":"flex","flexWrap":"wrap","gap":"20px","marginBottom":"20px"},
            children=[
                html.Div([
                    html.Label("Attendance % Range:"),
                    dcc.RangeSlider(
                        id="attendance-filter",
                        min=0, max=100, step=1, value=[0,100],
                        marks={0:"0%",50:"50%",100:"100%"}
                    )
                ], style={"flex":"1 1 300px"}),

                html.Div([
                    html.Label("Test Score Range:"),
                    dcc.RangeSlider(
                        id="score-filter",
                        min=0, max=100, step=1, value=[0,100],
                        marks={0:"0",50:"50",100:"100"}
                    )
                ], style={"flex":"1 1 300px"}),

                html.Div([
                    html.Label("Fees Due Range:"),
                    dcc.RangeSlider(
                        id="fees-filter",
                        min=0, max=5000, step=100, value=[0,5000],
                        marks={0:"0",2500:"2500",5000:"5000"}
                    )
                ], style={"flex":"1 1 300px"}),

                html.Div([
                    html.Label("Status:"),
                    dcc.Dropdown(
                        id="status-filter",
                        options=[
                            {"label":"All","value":"All"},
                            {"label":"Safe","value":"Safe"},
                            {"label":"At Risk","value":"At Risk"}
                        ],
                        value="All",
                        clearable=False
                    )
                ], style={"flex":"1 1 200px"})
            ]
        ),

        # DataTable
        dash_table.DataTable(
            id="student-table",
            columns=[
                {"name":"ID","id":"student_id"},
                {"name":"Name","id":"name"},
                {"name":"Attendance %","id":"attendance_percentage"},
                {"name":"Avg Test Score","id":"avg_score"},
                {"name":"Fees Due","id":"due_amount"},
                {"name":"Status","id":"status"},
                {"name":"Reasons","id":"reasons"},
            ],
            data=merged.to_dict("records"),
            page_size=15,
            sort_action="native",
            style_table={"maxHeight":"500px","overflowY":"auto"},
            style_cell={"textAlign":"center","padding":"5px"},
            style_header={"backgroundColor":"#f8f9fa","fontWeight":"bold"},
            style_data_conditional=[
                # Attendance
                {"if":{"filter_query":"{attendance_percentage} >= 90","column_id":"attendance_percentage"},
                 "backgroundColor":"#d4edda","color":"#000"},
                {"if":{"filter_query":"{attendance_percentage} < 75","column_id":"attendance_percentage"},
                 "backgroundColor":"#f8d7da","color":"#000"},
                # Test Score
                {"if":{"filter_query":"{avg_score} >= 80","column_id":"avg_score"},
                 "backgroundColor":"#d4edda","color":"#000"},
                {"if":{"filter_query":"{avg_score} < 40","column_id":"avg_score"},
                 "backgroundColor":"#f8d7da","color":"#000"},
                # Fees
                {"if":{"filter_query":"{due_amount} > 0","column_id":"due_amount"},
                 "backgroundColor":"#fff3cd","color":"#000"},
                # Status
                {"if":{"filter_query":"{status} = 'At Risk'","column_id":"status"},
                 "backgroundColor":"#f8d7da","fontWeight":"bold"},
                {"if":{"filter_query":"{status} = 'Safe'","column_id":"status"},
                 "backgroundColor":"#d4edda","fontWeight":"bold"},
                # Row hover
                {"if":{"state":"active"},"backgroundColor":"#cce5ff"}
            ]
        ),

        # Graphs
        html.Div(
            style={"display":"flex","flexWrap":"wrap","gap":"20px","justifyContent":"center","marginTop":"20px"},
            children=[
                html.Div(style={"flex":"1 1 400px","maxWidth":"45%"}, children=[dcc.Graph(id="attendance-dist", style={"height":"400px"})]),
                html.Div(style={"flex":"1 1 400px","maxWidth":"45%"}, children=[dcc.Graph(id="score-dist", style={"height":"400px"})]),
            ]
        ),

        # Footer
        html.Div(
            style={"marginTop":"40px","padding":"20px","borderTop":"2px solid #ccc","textAlign":"center","backgroundColor":"#f8f9fa","borderRadius":"8px"},
            children=[
                html.H4("About This Dashboard"),
                html.P(
                    "This Student Risk Dashboard helps educators identify students who may be struggling academically or financially. "
                    "It consolidates attendance, test scores, and fee payment data for clear, rule-based insights. "
                    "Early interventions can improve engagement, performance, and reduce drop-outs.",
                    style={"fontSize":"16px","lineHeight":"1.6"}
                ),
                html.P(f"Version: {VERSION_STRING}", style={"fontSize":"14px","color":"#666"})
            ]
        )
    ]
)

# --------------------------
# Callbacks
# --------------------------
@app.callback(
    [Output("student-table","data"),
     Output("attendance-dist","figure"),
     Output("score-dist","figure")],
    [Input("search-box","value"),
     Input("attendance-filter","value"),
     Input("score-filter","value"),
     Input("fees-filter","value"),
     Input("status-filter","value")]
)
def update_dashboard(search_value, att_range, score_range, fees_range, status_value):
    filtered = merged.copy()

    # Search filter
    if search_value:
        filtered = filtered[
            filtered["name"].str.contains(search_value, case=False, na=False) |
            filtered["student_id"].astype(str).str.contains(search_value)
        ]
    # Attendance filter
    filtered = filtered[(filtered["attendance_percentage"] >= att_range[0]) & (filtered["attendance_percentage"] <= att_range[1])]
    # Score filter
    filtered = filtered[(filtered["avg_score"] >= score_range[0]) & (filtered["avg_score"] <= score_range[1])]
    # Fees filter
    filtered = filtered[(filtered["due_amount"] >= fees_range[0]) & (filtered["due_amount"] <= fees_range[1])]
    # Status filter
    if status_value != "All":
        filtered = filtered[filtered["status"] == status_value]

    # Graphs
    fig_att = px.histogram(filtered, x="attendance_percentage", nbins=10, title="Attendance % Distribution")
    fig_att.update_layout(margin=dict(l=20,r=20,t=40,b=20))
    fig_att.update_traces(marker_color="#4e79a7")

    fig_score = px.histogram(filtered, x="avg_score", nbins=10, title="Test Score Distribution")
    fig_score.update_layout(margin=dict(l=20,r=20,t=40,b=20))
    fig_score.update_traces(marker_color="#f28e2c")

    return filtered.to_dict("records"), fig_att, fig_score

# --------------------------
# Run App
# --------------------------
if __name__=="__main__":
    app.run(debug=True, dev_tools_hot_reload=True, port=8050)
