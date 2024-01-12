import pandas as pd

from field_match import field_similarity_report, generate_column_rename


def main():
    # Sample data for usage example
    data1 = pd.DataFrame({
        'product_id': [101, 102, 103],
        'product_name': ['Apple', 'Banana', 'Cherry'],
        'price': [1.20, 0.80, 2.50]
    })

    data2 = pd.DataFrame({
        'id': [1, 2],
        'item_code': [101, 202],
        'description': ['Green Apple', 'Ripe Kiwi'],
        'name': ['Apple', 'Kiwi'],
        'cost': [1.10, 0.85]
    })

    # Using the field_similarity_report function
    similarity_report = field_similarity_report(data1, data2)
    print("Field Similarity Report:")
    print(similarity_report)
    # {'product_id': {'data_type': 'int64', 'similar_fields': [('item_code', 0.345), ('id', 0.309)]},
    # 'product_name': {'data_type': 'object', 'similar_fields': [('name', 0.167), ('description', 0.105)]},
    # 'price': {'data_type': 'float64', 'similar_fields': [('cost', 0.474)]}}

    # Generating a code snippet for renaming columns in data2 based on the similarity report
    rename_snippet = generate_column_rename(similarity_report)
    print("\nSuggested Code Snippet for Renaming Columns:")
    print(rename_snippet)
    # "rename_dict = {
    # 'item_code': 'product_id',  # Similarity Score: 0.34
    # 'cost': 'price',  # Similarity Score: 0.47}
    # data2.rename(columns=rename_dict, inplace=True)"


if __name__ == "__main__":
    main()
