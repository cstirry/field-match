import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def compute_text_similarity(series_1, series_2):
    """
    Compute the cosine similarity between two series of text data.

    This function uses TF-IDF (Term Frequency-Inverse Document Frequency) to convert
    the text data into vectors and then computes the cosine similarity between these vectors.
    It's a measure of similarity between two non-zero vectors of an inner product space
    and is used to measure the cosine of the angle between them.

    Parameters:
    - series_1 (pandas.Series): A pandas Series containing text data.
    - series_2 (pandas.Series): Another pandas Series containing text data to be
                                compared with series_1.

    Returns:
    - float: A single floating-point number representing the average cosine similarity
             score between series_1 and series_2. The score ranges from 0 (no similarity)
             to 1 (identical text content).
    """
    vectorizer = TfidfVectorizer(stop_words='english')
    combined_text = pd.concat([series_1.fillna(''), series_2.fillna('')], ignore_index=True)
    tfidf_matrix = vectorizer.fit_transform(combined_text)
    return cosine_similarity(tfidf_matrix[:len(series_1)], tfidf_matrix[len(series_1):]).mean()


def compute_numeric_similarity(series_1, series_2):
    """
    Compute similarity for date fields based on the range of dates.

    This function calculates the similarity between two date series by comparing the
    range (difference between max and min dates) of each series. The similarity score
    is inversely proportional to the difference in ranges between the two series.

    Parameters:
    - series_1 (pandas.Series): A pandas Series containing datetime data.
    - series_2 (pandas.Series): Another pandas Series containing datetime data for comparison.

    Returns:
    - float: A similarity score ranging from 0 (no similarity) to 1 (identical ranges).
    """
    stats_1 = series_1.describe()
    stats_2 = series_2.describe()
    similarities = {
        'mean': 1 - abs(stats_1['mean'] - stats_2['mean']) / max(stats_1['mean'], stats_2['mean'], 1),
        'median': 1 - abs(stats_1['50%'] - stats_2['50%']) / max(stats_1['50%'], stats_2['50%'], 1),
        'std_dev': 1 - abs(stats_1['std'] - stats_2['std']) / max(stats_1['std'], stats_2['std'], 1),
        'range': 1 - abs((stats_1['max'] - stats_1['min']) - (stats_2['max'] - stats_2['min'])) / max(
            stats_1['max'] - stats_1['min'], stats_2['max'] - stats_2['min'], 1)
    }
    return np.mean(list(similarities.values()))


def compute_date_similarity(series_1, series_2):
    """
    Compute similarity for date fields based on the range of dates.

    This function calculates the similarity between two date series by comparing the
    range (difference between max and min dates) of each series. The similarity score
    is inversely proportional to the difference in ranges between the two series.

    Parameters:
    - series_1 (pandas.Series): A pandas Series containing datetime data.
    - series_2 (pandas.Series): Another pandas Series containing datetime data for comparison.

    Returns:
    - float: A similarity score ranging from 0 (no similarity) to 1 (identical ranges).
    """
    range1 = series_1.max() - series_1.min()
    range2 = series_2.max() - series_2.min()
    return 1 - abs((range1 - range2).days) / max(range1.days, range2.days)


def compute_boolean_similarity(series_1, series_2):
    """
    Compute similarity for boolean fields based on value proportions.

    This function assesses the similarity between two boolean series by comparing the
    proportion of True values in each. It uses a close approximation to determine if the
    proportions are similar.

    Parameters:
    - series_1 (pandas.Series): A pandas Series containing boolean data.
    - series_2 (pandas.Series): Another pandas Series containing boolean data for comparison.

    Returns:
    - bool: True if the series are similar in their proportion of True values, False otherwise.
    """
    proportion_1 = series_1.mean()
    proportion_2 = series_2.mean()

    # Use the smaller proportion as the base for comparison to avoid division by zero
    base_proportion = min(proportion_1, proportion_2, 1 - proportion_1, 1 - proportion_2)

    # Avoid division by zero; if both proportions are 0 or 1, they are identical
    if base_proportion == 0:
        return float(proportion_1 == proportion_2)

    return 1 - abs(proportion_1 - proportion_2) / base_proportion


def compute_categorical_similarity(series_1, series_2):
    """
    Compute similarity for categorical data using Jaccard similarity.

    This function evaluates the similarity between two categorical series by calculating
    the Jaccard similarity, which is the ratio of the intersection to the union of the
    unique values in both series.

    Parameters:
    - series_1 (pandas.Series): A pandas Series containing categorical data.
    - series_2 (pandas.Series): Another pandas Series containing categorical data for comparison.

    Returns:
    - float: The Jaccard similarity score, ranging from 0 (no similarity) to 1 (identical categories).
    """
    set1 = set(series_1.dropna().unique())
    set2 = set(series_2.dropna().unique())
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union != 0 else 0


def field_similarity_report(data1, data2):
    """
    Compares fields between two pandas DataFrame objects and calculates similarity scores
    for each pair of fields with the same data type.

    This function iterates through each field in `data1` and compares it with every field in `data2`
    of the same data type. For each field pair, it calculates a similarity score based on the
    type of data they contain (e.g., text, numeric).

    Parameters:
    - data1 (pandas.DataFrame): The first DataFrame containing fields to be compared.
    - data2 (pandas.DataFrame): The second DataFrame against which fields from data1 are compared.

    Returns:
    - dict: A dictionary where each key is a field name from data1, and the value is a list of tuples.
            Each tuple contains a field name from data2 and its calculated similarity score with the key field.
            The data type of each field from data1 is also included in the output.
    """
    matched_fields_similarities = {}
    for field1 in data1.columns:
        field_similarities = []
        for field2 in data2.columns:
            if data1[field1].dtype == data2[field2].dtype:
                similarity_score = 0
                if pd.api.types.is_string_dtype(data1[field1]):
                    similarity_score = compute_text_similarity(data1[field1], data2[field2])
                elif pd.api.types.is_numeric_dtype(data1[field1]):
                    similarity_score = compute_numeric_similarity(data1[field1], data2[field2])
                elif pd.api.types.is_categorical_dtype(data1[field1]):
                    similarity_score = compute_categorical_similarity(data1[field1], data2[field2])
                elif pd.api.types.is_datetime64_any_dtype(data1[field1]):
                    similarity_score = compute_date_similarity(data1[field1], data2[field2])
                elif pd.api.types.is_bool_dtype(data1[field1]):
                    similarity_score = compute_boolean_similarity(data1[field1], data2[field2])

                field_similarities.append((field2, round(similarity_score, 3)))

        field_similarities.sort(key=lambda x: x[1], reverse=True)
        matched_fields_similarities[field1] = {
            "data_type": str(data1[field1].dtype),
            "similar_fields": field_similarities
        }

    return matched_fields_similarities


def generate_column_rename(matched_fields_similarities):
    """
    Generates a Python code snippet that suggests how to rename columns in the second DataFrame
    based on the highest similarity scores from the field_similarity_report output.

    Parameters:
    - matched_fields_similarities (dict): The output dictionary from the field_similarity_report function.

    Returns:
    - str: A string containing the Python code snippet for renaming columns.
    """
    rename_instr = "rename_dict = {\n"
    for field1, match_info in matched_fields_similarities.items():
        similar_fields = match_info.get('similar_fields', [])
        if similar_fields:  # Check if there are matching fields
            most_similar_field, highest_score = similar_fields[0]
            # Generate instruction only if the similarity score is above a certain threshold, e.g., 0.3
            if highest_score > 0.3:
                rename_instr += f"    '{most_similar_field}': '{field1}',  # Similarity Score: {highest_score:.2f}\n"

    rename_instr += "}\ndata2.rename(columns=rename_dict, inplace=True)\n"

    return rename_instr
