from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np


def analyze_user_growth(users):
    # Returns months, counts, and predicted next month
    df = pd.DataFrame(users)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['month'] = df['created_at'].dt.to_period('M')
    monthly = df.groupby('month').size().reset_index(name='count')
    monthly['month_num'] = np.arange(len(monthly))

    model = LinearRegression()
    if len(monthly) > 1:
        model.fit(monthly[['month_num']], monthly['count'])
        next_month = monthly['month_num'].iloc[-1] + 1
        predicted = model.predict([[next_month]])[0]
    else:
        predicted = monthly['count'].iloc[-1] if not monthly.empty else 0

    return {'months': monthly['month'].astype(str).tolist(),
            'counts': monthly['count'].tolist(),
            'predicted_next': round(predicted)}


def college_distribution_by_state(colleges):
    df = pd.DataFrame(colleges)
    if 'state' not in df.columns or df.empty:
        return {'states': [], 'counts': []}
    top_states = df['state'].value_counts().head(10)
    return {'states': top_states.index.tolist(), 'counts': top_states.values.tolist()}


def top_courses(courses):
    df = pd.DataFrame(courses)
    if 'course_name' not in df.columns or df.empty:
        return {'courses': [], 'counts': []}
    top = df['course_name'].value_counts().head(5)
    return {'courses': top.index.tolist(), 'counts': top.values.tolist()}


def top_ranked_colleges(colleges, top_n=10):
    df = pd.DataFrame(colleges)
    if 'ranking' not in df.columns or df.empty:
        return {'colleges': [], 'rankings': []}
    df = df.dropna(subset=['ranking'])
    df = df.sort_values('ranking', ascending=True).head(top_n)
    return {'colleges': df['college_name'].tolist(), 'rankings': df['ranking'].tolist()}


def evaluate_user_growth_accuracy(users):
    """
    Evaluate Linear Regression model predicting user growth.
    Returns R² and RMSE.
    """
    df = pd.DataFrame(users)
    df['created_at'] = pd.to_datetime(df['created_at'])

    if df.empty:
        return {'r2_score': None, 'rmse': None}

    # Group by month
    df['month'] = df['created_at'].dt.to_period('M')
    monthly = df.groupby('month').size().reset_index(name='count')

    if len(monthly) <= 1:
        return {'r2_score': None, 'rmse': None}

    # Convert month to ordinal numeric values for regression
    monthly['month_ordinal'] = monthly['month'].apply(lambda x: x.start_time.toordinal())
    X = monthly[['month_ordinal']]
    y = monthly['count']

    model = LinearRegression()
    model.fit(X, y)

    preds = model.predict(X)
    rmse = np.sqrt(np.mean((preds - y) ** 2))
    r2 = model.score(X, y)

    return {'r2_score': round(r2, 2), 'rmse': round(rmse, 2)}


def course_placement_data(courses, users):
    """
    Returns data for bubble chart:
    x-axis: course_name
    y-axis: avg placement rating
    size: number of students enrolled
    """
    import pandas as pd
    df_courses = pd.DataFrame(courses)

    if df_courses.empty or 'course_name' not in df_courses.columns:
        return {'courses': [], 'avg_rating': [], 'num_students': []}

    # Count number of students per course
    course_counts = df_courses['course_name'].value_counts().to_dict()

    avg_ratings = []
    student_counts = []
    course_names = []

    for course_name, count in course_counts.items():
        course_df = df_courses[df_courses['course_name'] == course_name]
        avg_rating = course_df['placement_rating'].mean() if 'placement_rating' in course_df.columns else 0
        course_names.append(course_name)
        avg_ratings.append(round(avg_rating, 2))
        student_counts.append(count)

    return {'courses': course_names, 'avg_rating': avg_ratings, 'num_students': student_counts}
