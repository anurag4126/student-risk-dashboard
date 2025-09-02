import dash
from dash import dcc, html, dash_table, Input, Output
import pandas as pd
import plotly.express as px

# --------------------------
# Load data
# --------------------------
scores_df = pd.read_csv("data/tests.csv")
fees_df = pd.read_csv("data/fees.csv")
attendance_df = pd.read_csv("data/attendance.csv")
students_df = pd.read_csv("data/students.csv")

# --------------------------
# Preprocess
# --------------------------
# Average score
scores_df = scores_df.groupby("student_id")["score"].mean().reset_index()
scores_df.rename(columns={"score": "avg_score"}, inplace=True)

# Merge all
df = scores_df.merge(fees_df, on="student_id", how="left")
df = df.merge(
    attendance_df.groupby("student_id")["attendance_percentage"].mean().reset_index(),
    on="student_id",
    how="left"
)
df = df.merge(students_df, on="student_id", how="left")

# Fill missing values
df["pending_amount"] = df["pending_amount"].fillna(0)
df["attendance_percentage"] = df["attendance_percentage"].fillna(0)

# Risk status
def risk_status(row):
    if row["avg_score"] < 60 or row["pending_amount"] > 0 or row["attendance_percentage"] < 75:
        return "At Risk"
    return "Safe"

df["status"] = df.apply(risk_status, axis=1)

# Normalize column names
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

# Round attendance
df["attendance_percentage"] = df["attendance_percentage"].round(2)

# --------------------------
# Dash app
# --------------------------
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("🎓 Student Risk Dashboard", style={"textAlign": "center", "color": "#2C3E50"}),

    # Search bar
    dcc.Input(
        id="search-input",
        type="text",
        placeholder="🔍 Search by Student ID or Name...",
        style={
            "width": "100%",
            "padding": "12px",
            "marginBottom": "20px",
            "fontSize": "16px",
            "borderRadius": "8px",
            "border": "1px solid #ccc"
        }
    ),

    # --------------------------
    # Grade Filter Dropdown (Multi-select) ✅ moved to top
    # --------------------------
    html.Div([
        html.Label("Filter by Grade:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="grade-dropdown",
            options=[{"label": g, "value": g} for g in sorted(df["class"].dropna().unique())],
            value=[],  # Start with empty = all grades
            multi=True,  # multi-select enabled
            clearable=True,
            style={"width": "60%"}
        )
    ], style={"marginBottom": "20px"}),

    # --------------------------
    # Risk / Status Filter ✅ moved below grade filter
    # --------------------------
    html.Div([
        html.Label("Filter Students:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="filter-dropdown",
            options=[
                {"label": "All Students", "value": "all"},
                {"label": "At Risk", "value": "at_risk"},
                {"label": "Safe", "value": "safe"},
                {"label": "Fees Pending", "value": "fees_pending"},
                {"label": "Low Attendance (<75%)", "value": "low_attendance"},
                {"label": "Low Scores (<60)", "value": "low_scores"},
            ],
            value="all",
            clearable=False,
            style={"width": "60%"}
        )
    ], style={"marginBottom": "20px"}),

    # --------------------------
    # Table
    # --------------------------
    dash_table.DataTable(
        id="student-table",
        columns=[
            {"name": "Student ID", "id": "student_id"},
            {"name": "Name", "id": "name"},
            {"name": "Class", "id": "class"},
            {"name": "Average Score", "id": "avg_score"},
            {"name": "Pending Amount", "id": "pending_amount"},
            {"name": "Attendance %", "id": "attendance_percentage"},
            {"name": "Status", "id": "status"}
        ],
        page_size=15,
        sort_action="native",
        filter_action="none",
        style_table={"overflowX": "auto", "maxWidth": "100%"},
        style_cell={"textAlign": "center", "padding": "8px"},
        style_header={"backgroundColor": "#2C3E50", "color": "white", "fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"filter_query": "{status} = 'At Risk'", "column_id": "student_id"},
             "backgroundColor": "#E74C3C", "color": "white", "fontWeight": "bold"},
            {"if": {"filter_query": "{avg_score} > 80", "column_id": "avg_score"},
             "backgroundColor": "#2ECC71", "color": "white", "fontWeight": "bold"},
            {"if": {"filter_query": "{attendance_percentage} < 75", "column_id": "attendance_percentage"},
             "backgroundColor": "#E74C3C", "color": "white", "fontWeight": "bold"},
            {"if": {"filter_query": "{pending_amount} > 0", "column_id": "pending_amount"},
             "backgroundColor": "#E74C3C", "color": "white", "fontWeight": "bold"},
            {"if": {"filter_query": "{status} = 'At Risk'", "column_id": "status"},
             "backgroundColor": "#E74C3C", "color": "white", "fontWeight": "bold"},
        ]
    ),

    # --------------------------
    # Graph
    # --------------------------
    dcc.Graph(id="risk-graph", style={"height": "400px"}),

    # Footer
    html.Footer(
        "📊 Student Risk Dashboard – Helping institutions identify students who may need academic, financial, or attendance support.",
        style={"textAlign": "center", "marginTop": "20px", "padding": "10px", "backgroundColor": "#ECF0F1"}
    )
])

# --------------------------
# Callbacks
# --------------------------
@app.callback(
    [Output("student-table", "data"),
     Output("risk-graph", "figure")],
    [Input("filter-dropdown", "value"),
     Input("grade-dropdown", "value"),
     Input("search-input", "value")]
)
def update_dashboard(filter_value, grade_values, search_value):
    filtered_df = df.copy()

    # Apply risk/attendance/fees filters
    if filter_value == "at_risk":
        filtered_df = filtered_df[filtered_df["status"] == "At Risk"]
    elif filter_value == "safe":
        filtered_df = filtered_df[filtered_df["status"] == "Safe"]
    elif filter_value == "fees_pending":
        filtered_df = filtered_df[filtered_df["pending_amount"] > 0]
    elif filter_value == "low_attendance":
        filtered_df = filtered_df[filtered_df["attendance_percentage"] < 75]
    elif filter_value == "low_scores":
        filtered_df = filtered_df[filtered_df["avg_score"] < 60]

    # Apply grade filter (multi-select)
    if grade_values:  # list not empty
        filtered_df = filtered_df[filtered_df["class"].isin(grade_values)]

    # Apply search
    if search_value and search_value.strip() != "":
        search_value = search_value.lower()
        filtered_df = filtered_df[
            filtered_df["student_id"].astype(str).str.contains(search_value, case=False) |
            filtered_df["name"].str.lower().str.contains(search_value)
        ]

    # Table data
    table_data = filtered_df.to_dict("records")

    # Graph
    fig = px.histogram(
        filtered_df,
        x="status",
        color="status",
        title="Distribution of Students",
        text_auto=True,
        color_discrete_map={"Safe": "#27AE60", "At Risk": "#E74C3C"}
    )

    return table_data, fig


# --------------------------
# Run
# --------------------------
if __name__ == "__main__":
    app.run(debug=True)
