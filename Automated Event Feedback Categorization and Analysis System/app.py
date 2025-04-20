from flask import Flask, request, render_template
import pandas as pd

app = Flask(__name__)

positive_keywords = ['good', 'great', 'excellent', 'helpful', 'informative', 'loved']
negative_keywords = ['bad', 'boring', 'poor', 'not', 'waste', 'confusing']

def is_feedback_column(col_name):
    col_name = col_name.lower()
    ignore_keywords = ['timestamp', 'email', 'name', 'roll', 'co', 'po', 'sno', 'slno', 'sr no', 'attainment', 'class', 'branch', 'div']
    return not any(key in col_name for key in ignore_keywords)

def is_datetime_column(series):
    try:
        pd.to_datetime(series, errors='raise')
        return True
    except:
        return False

def classify_comment(comment):
    comment = str(comment).lower()
    if any(neg in comment for neg in negative_keywords):
        return "Negative"
    elif any(pos in comment for pos in positive_keywords):
        return "Positive"
    return "Neutral"

def analyze_data(df):
    summary = []
    for column in df.columns:
        if not is_feedback_column(column):
            continue

        col_data = df[column].dropna().astype(str).str.strip()
        if col_data.empty or is_datetime_column(col_data):
            continue

        # Binary Feedback
        if col_data.str.lower().isin(['yes', 'no']).all():
            yes_count = (col_data.str.lower() == 'yes').sum()
            total = len(col_data)
            summary.append({
                "question": column,
                "type": "Binary Feedback",
                "display_summary": f"Yes: {round((yes_count / total) * 100, 2)}% ({yes_count}/{total})"
            })

        # Categorical Feedback
        elif col_data.str.lower().isin(['excellent', 'very good', 'good', 'average', 'bad', 'poor', 'fair']).any():
            counts = col_data.value_counts()
            summary.append({
                "question": column,
                "type": "Categorical Feedback",
                "display_summary": ', '.join([f"{k}: {v}" for k, v in counts.items()])
            })

        # Range Feedback
        elif col_data.str.contains(r'\d{1,3}-\d{1,3}%').any():
            extracted = col_data.str.extract(r'(\d{1,3})-(\d{1,3})%')
            if not extracted.empty:
                start_vals = extracted[0].dropna().astype(int)
                bins = [0, 20, 40, 60, 80, 100]
                labels = ['0-20', '21-40', '41-60', '61-80', '81-100']
                ranges = pd.cut(start_vals, bins=bins, labels=labels, right=True)
                counts = ranges.value_counts().sort_index()
                summary.append({
                    "question": column,
                    "type": "Range Feedback",
                    "display_summary": ', '.join([f"{k}: {v}" for k, v in counts.items()])
                })

        # Sentiment Feedback
        elif col_data.str.len().mean() > 15:
            sentiments = col_data.apply(classify_comment)
            counts = sentiments.value_counts()
            summary.append({
                "question": column,
                "type": "Sentiment Feedback",
                "display_summary": ', '.join([f"{k}: {v}" for k, v in counts.items()])
            })

    return summary

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files['file']

    # Read 2nd row as headers (header=1 means skip first row)
    df = pd.read_excel(file, header=1)

    # Clean column names
    df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('\r', '', regex=True)

    summary = analyze_data(df)

    return render_template("results.html", summary=summary)

if __name__ == '__main__':
    app.run(debug=True)
