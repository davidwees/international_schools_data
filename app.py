import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Set Streamlit layout configuration
st.set_page_config(
    page_title="International School Finder",
    page_icon="🏫",
    layout="wide"
)

st.title("🏫 International School Explorer & Rating Dashboard")
st.markdown("Filter international school reviews, average ratings across criteria, salary ranges, and view Cost of Living metrics per country.")

# ----------------------------------------------------
# 1. DATA LOADING AND CLEANING
# ----------------------------------------------------
@st.cache_data
def load_and_process_data():
    # Load review dataset
    df = pd.read_csv("extracted_reviews.csv")
    
    # Load Cost of Living dataset
    try:
        df_col = pd.read_csv("cost_of_living.csv")
    except Exception:
        df_col = pd.DataFrame() # Fallback if missing
    
    # Identify numerical rating categories
    rating_cols = [
        'Academic integrity of school',
        'Effectiveness of administration',
        'Academic and disciplinary support provided',
        "Director's involvement in academics",
        'Fair and equitable treatment by board and director',
        'School has adequate educational materials on hand',
        'Attitude of local community towards foreigners',
        'Cost of living in relation to salary (10 = most favorable)',
        'Satisfaction with housing',
        'Community offers a variety of activities',
        'Availability and quality of local health care',
        'Satisfaction with school health insurance policy',
        'Family friendly / child friendly school and community',
        'Assistance with visas, shipping and air travel',
        'Extra curricular load is reasonable',
        'Security / personal safety (10 = very safe in and out of school)',
        'Average Score for Review'
    ]
    
    # Convert rating columns to numeric values
    for col in rating_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Ensure Minimum and Maximum Salary are numeric
    if 'Minimum Salary' in df.columns:
        df['Minimum Salary'] = pd.to_numeric(df['Minimum Salary'], errors='coerce')
    if 'Maximum Salary' in df.columns:
        df['Maximum Salary'] = pd.to_numeric(df['Maximum Salary'], errors='coerce')

    # Aggregating data by School Name and Country
    agg_dict = {col: 'mean' for col in rating_cols if col in df.columns}
    agg_dict['Review Count'] = 'max' # total count reported
    agg_dict['File Name'] = 'first'
    
    if 'School Website' in df.columns:
        agg_dict['School Website'] = 'first'
    
    if 'Minimum Salary' in df.columns:
        agg_dict['Minimum Salary'] = 'min'  # Min salary reported across reviews
    if 'Maximum Salary' in df.columns:
        agg_dict['Maximum Salary'] = 'max'  # Max salary reported across reviews

    school_data = df.groupby(['Country', 'School Name']).agg(agg_dict).reset_index()

    # Create formatted salary range string from Minimum Salary and Maximum Salary
    def format_salary_range(row):
        min_sal = row.get('Minimum Salary', np.nan)
        max_sal = row.get('Maximum Salary', np.nan)
        
        has_min = pd.notnull(min_sal) and not np.isnan(min_sal)
        has_max = pd.notnull(max_sal) and not np.isnan(max_sal)
        
        if has_min and has_max:
            if min_sal == max_sal:
                return f"${int(min_sal):,}"
            return f"${int(min_sal):,} - ${int(max_sal):,}"
        elif has_min:
            return f"${int(min_sal):,}+"
        elif has_max:
            return f"Up to ${int(max_sal):,}"
        else:
            return "N/A"

    school_data['Yearly salary range for teachers in US dollars'] = school_data.apply(format_salary_range, axis=1)

    # Merge Cost of Living details by Country
    if not df_col.empty and 'Country' in df_col.columns:
        school_data = pd.merge(school_data, df_col, on='Country', how='left')

    return df, school_data, rating_cols

df_raw, df_schools, rating_cols = load_and_process_data()

# Determine overall salary limits for the slider
min_sal_val = int(df_schools['Minimum Salary'].min()) if 'Minimum Salary' in df_schools.columns and pd.notnull(df_schools['Minimum Salary'].min()) else 10000
max_sal_val = int(df_schools['Maximum Salary'].max()) if 'Maximum Salary' in df_schools.columns and pd.notnull(df_schools['Maximum Salary'].max()) else 150000

# ----------------------------------------------------
# 2. SIDEBAR FILTERS
# ----------------------------------------------------
st.sidebar.header("🔍 Filter Schools")

# Country Filter
countries = sorted(df_schools['Country'].dropna().unique())
selected_country = st.sidebar.multiselect("Select Country", options=countries, default=[])

# Continuous Salary Range Slider
st.sidebar.subheader("💵 Salary Filter ($ USD)")
selected_salary_range = st.sidebar.slider(
    "Select Desired Teacher Salary Range",
    min_value=min_sal_val,
    max_value=max_sal_val,
    value=(min_sal_val, max_sal_val),
    step=2500,
    format="$%d"
)

# Minimum Overall Score Threshold
min_avg_score = st.sidebar.slider(
    "Minimum Overall Average Rating",
    min_value=1.0,
    max_value=10.0,
    value=5.0,
    step=0.5
)

# Focus Category Minimum Threshold Filter
focus_category = st.sidebar.selectbox("Filter by Specific High-Performing Metric", ["None"] + rating_cols)
min_category_score = 1.0
if focus_category != "None":
    min_category_score = st.sidebar.slider(
        f"Minimum score for '{focus_category}'",
        min_value=1.0,
        max_value=10.0,
        value=8.0,
        step=0.5
    )

# ----------------------------------------------------
# APPLY FILTERING LOGIC
# ----------------------------------------------------
filtered_df = df_schools.copy()

if selected_country:
    filtered_df = filtered_df[filtered_df['Country'].isin(selected_country)]

# Numerical Salary Range Filter Logic
user_min, user_max = selected_salary_range
salary_filter = (
    (filtered_df['Minimum Salary'].isna() & filtered_df['Maximum Salary'].isna()) |
    (
        (filtered_df['Minimum Salary'].fillna(user_min) <= user_max) & 
        (filtered_df['Maximum Salary'].fillna(user_max) >= user_min)
    )
)
filtered_df = filtered_df[salary_filter]

if 'Average Score for Review' in filtered_df.columns:
    filtered_df = filtered_df[filtered_df['Average Score for Review'] >= min_avg_score]

if focus_category != "None":
    filtered_df = filtered_df[filtered_df[focus_category] >= min_category_score]

# ----------------------------------------------------
# 3. MAIN DASHBOARD CONTENT
# ----------------------------------------------------
st.subheader(f"Matching Schools ({len(filtered_df)} Found)")

if filtered_df.empty:
    st.warning("No schools match your search criteria. Try relaxing your filters in the sidebar!")
else:
    # Display table of filtered schools with clickable URL and formatted salary range
    display_cols = ['School Name', 'Country', 'School Website', 'Average Score for Review', 'Yearly salary range for teachers in US dollars']
    
    st.dataframe(
        filtered_df[display_cols].sort_values(by='Average Score for Review', ascending=False),
        column_config={
            "School Website": st.column_config.LinkColumn(
                "School Website",
                help="Click to open school website in a new tab",
                display_text="Visit Website 🔗"
            )
        },
        width="stretch"
    )

    st.markdown("---")
    st.subheader("🎯 Detailed School & Country Analysis")

    # Select a specific school to visualize
    school_options = filtered_df['School Name'].unique()
    selected_school_name = st.selectbox("Select a School to Inspect Profile & Spoke Chart:", school_options)

    # Extract single school data row
    school_row = filtered_df[filtered_df['School Name'] == selected_school_name].iloc[0]

    # Display Clickable Link for the selected school
    website_url = school_row.get('School Website', None)
    if pd.notnull(website_url) and str(website_url).strip() != "":
        st.markdown(f"🔗 **Official Website:** [{website_url}]({website_url}) *(opens in a new tab)*")
    else:
        st.info("No website link available for this school.")

    # ----------------------------------------------------
    # COST OF LIVING INDEX CARD
    # ----------------------------------------------------
    st.markdown(f"### 🌍 Country Living Context: **{school_row['Country']}**")
    if 'Cost of Living Index' in school_row and pd.notnull(school_row['Cost of Living Index']):
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Cost of Living Index", f"{school_row['Cost of Living Index']}")
        col_b.metric("Rent Index", f"{school_row.get('Rent Index', 'N/A')}")
        col_c.metric("Groceries Index", f"{school_row.get('Groceries Index', 'N/A')}")
        col_d.metric("Local Purchasing Power", f"{school_row.get('Local Purchasing Power Index', 'N/A')}")
        st.caption("*Note: Cost of Living indices are relative to New York City (Base = 100).*")
    else:
        st.info(f"Cost of living data is not available for {school_row['Country']}.")

    st.markdown("---")

    # Prepare criteria metrics for Spoke Chart
    spoke_categories = [c for c in rating_cols if c != 'Average Score for Review']
    scores = [school_row[c] for c in spoke_categories]

    # Create Spoke Chart using Plotly Polar Coordinates
    palette = px.colors.qualitative.Plotly + px.colors.qualitative.Set2
    colors = [palette[i % len(palette)] for i in range(len(spoke_categories))]

    fig = go.Figure()

    # Add Barpolar traces (Colored spokes)
    for cat, score, color in zip(spoke_categories, scores, colors):
        r_val = 0 if pd.isna(score) else score
        fig.add_trace(
            go.Barpolar(
                r=[r_val],
                theta=[cat],
                name=cat,
                marker_color=color,
                opacity=0.85,
                hoverinfo="theta+r"
            )
        )

    # Plot line connector
    plot_scores = [0 if pd.isna(s) else s for s in scores]
    fig.add_trace(
        go.Scatterpolar(
            r=plot_scores + [plot_scores[0]],
            theta=spoke_categories + [spoke_categories[0]],
            mode='lines+markers',
            name='Profile Connect',
            line=dict(color='black', width=2),
            marker=dict(size=6, color='black'),
            showlegend=False
        )
    )

    # Layout styling with Plotly compatibility
    fig.update_layout(
        title=f"Category Breakdown Spoke Chart: <b>{selected_school_name}</b> ({school_row['Country']})",
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=10)),
            angularaxis=dict(tickfont=dict(size=11, color="black"), rotation=90, direction="clockwise")
        ),
        showlegend=True,
        legend=dict(title=dict(text="Categories"), x=1.1, y=1, xref="paper", yref="paper"),
        height=650,
        margin=dict(l=80, r=180, t=80, b=80)
    )

    st.plotly_chart(fig, width="stretch")

    # ----------------------------------------------------
    # 4. DETAILED CATEGORY RATING SCORES TABLE
    # ----------------------------------------------------
    st.subheader("📋 Category Score Summary")
    
    score_summary = pd.DataFrame({
        "Category": spoke_categories,
        "Average Rating (out of 10)": [round(float(s), 2) if pd.notnull(s) else np.nan for s in scores]
    })
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(
            score_summary,
            column_config={
                "Average Rating (out of 10)": st.column_config.NumberColumn(
                    "Average Rating (out of 10)",
                    format="%.2f"
                )
            },
            width="stretch"
        )
    with col2:
        overall_score = school_row['Average Score for Review']
        score_display = f"{round(overall_score, 2)} / 10" if pd.notnull(overall_score) else "N/A"
        st.metric("Overall Average Score", score_display)
        st.metric("Salary Range", f"{school_row['Yearly salary range for teachers in US dollars']}")