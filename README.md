# field-match

## Overview

field-match is a Python library designed to analyze and compare fields between two datasets based on similarity scores,
and match up the field names.

## Installation

To install the package, run:

```bash
pip install field-match
```

## Usage

Import and use the package as follows:

```python
import pandas as pd
from field_match import field_similarity_report, generate_column_rename

# Load your datasets
df1 = pd.read_csv('dataset1.csv')
df2 = pd.read_csv('dataset2.csv')

# Use the field_similarity_report function to match up fields by similarity score
results = field_similarity_report(df1, df2)
                   
# Generate the column rename code snippet
rename_snippet = generate_column_rename(results)                      

```

For more detailed examples, please refer to the `examples` folder in this repository.

## Example Applications

1. **Clarifying Ambiguous Dataset Fields:** When merging or integrating a new or updated dataset (e.g. data from
   another year or source) with an existing dataset or workflow, uncertainty in how fields correspond to each
   may exist because of a lack of headers or differing field names. `field-match` can help identify which fields in the
   new dataset correspond to expected fields.

2. **Integrating External Dataset with Existing Model:** When feeding an external dataset into a pre-existing model,
   the new data must align correctly with the model's expected input format. `field-match` can help identify which fields
   in the new dataset correspond to the fields the model expects.

## License

field-match is released under the [MIT License](LICENSE).
