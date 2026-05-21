# Lesson 9: Pandas for Tabular Data in Python

## Overview

Pandas is the standard Python library for working with **tabular data**. It is used to:

- load and inspect datasets
- select and filter rows and columns
- clean and transform data
- compute summary statistics
- group and aggregate data
- prepare data for machine learning workflows

The central abstraction in pandas is the **DataFrame**, which represents a table. Each column in a DataFrame is a **Series**.

---

## Key Concepts

### 1. Pandas and the `DataFrame`
- **Pandas** is designed for manipulating structured data in Python.
- A **DataFrame** is a table with rows and columns.
- A **Series** is a single labeled column inside a DataFrame.

### 2. Creating DataFrames
You can create a DataFrame from:
- a list of lists
- a list of dictionaries

### 3. Inspecting Data
- `head()` shows the first rows of a DataFrame.
- This is one of the first things to do after loading data.

### 4. Selecting Data
- Use dot notation or bracket notation to access columns.
- Use double brackets to select multiple columns.

### 5. Adding and Removing Columns
- New columns can be created by assignment.
- Existing columns can be replaced by assignment.
- Columns can be deleted with `del`.

### 6. Indexing Rows
- Every DataFrame has an **index**.
- `loc` selects by label.
- `iloc` selects by integer position.
- `reset_index()` restores a sequential index.

### 7. Element-wise Operations
- Pandas Series support vectorized arithmetic and logical operations.
- Operations are applied element by element.

### 8. Filtering Rows
- Boolean conditions return a mask of `True` / `False`.
- Use that mask to keep only matching rows.

### 9. String Operations
- Pandas provides string helpers via `.str`.
- Useful for cleaning and normalizing text columns.

### 10. Summary Statistics
- `mean()`, `max()`, `min()`, etc. work on numeric Series.
- `describe()` gives a compact statistical summary.
- `nunique()` counts unique values.

### 11. Missing Values
- `isnull()` identifies missing values.
- `sum()` can count missing values per column.

### 12. Grouping and Aggregation
- `groupby()` groups rows by a column.
- Aggregation functions like `mean()` compute summaries within each group.

### 13. Converting Back to Python Structures
- `to_dict(orient="records")` converts a DataFrame to a list of dictionaries.

---

## Detailed Explanations and Examples

## 1. Creating a DataFrame

A DataFrame is the basic pandas table object.

### From a list of lists
Each inner list represents one row.

```python
import pandas as pd

data = [
    ["toyota", "camry", 2019, 2500, 200, 4, "automatic", "sedan", 22000],
    ["nissan", "altima", 2018, 2400, 180, 4, "manual", "sedan", 18000],
    ["ford", "focus", 2017, 2000, 160, 4, "automatic", "hatchback", 15000],
    ["nissan", "sentra", 2016, 1800, None, 4, "manual", "sedan", 14000],
    ["honda", "civic", 2020, 2200, 170, 4, "automatic", "sedan", 21000],
]

columns = [
    "make",
    "model",
    "year",
    "engine",
    "horsepower",
    "cylinders",
    "transmission type",
    "vehicle style",
    "price",
]

df = pd.DataFrame(data, columns=columns)
```

### From a list of dictionaries
This is often more readable because each row is explicit.

```python
data = [
    {
        "make": "toyota",
        "model": "camry",
        "year": 2019,
        "engine": 2500,
        "horsepower": 200,
        "cylinders": 4,
        "transmission type": "automatic",
        "vehicle style": "sedan",
        "price": 22000,
    },
    {
        "make": "nissan",
        "model": "altima",
        "year": 2018,
        "engine": 2400,
        "horsepower": 180,
        "cylinders": 4,
        "transmission type": "manual",
        "vehicle style": "sedan",
        "price": 18000,
    },
]

df = pd.DataFrame(data)
```

### Why this matters
- DataFrames are the standard input/output format in pandas.
- Most ML preprocessing steps begin with a DataFrame.
- Real datasets are often read from CSV, SQL, or JSON, then converted into DataFrames.

---

## 2. Inspecting the Data

The first thing to do after loading a dataset is inspect a few rows.

```python
df.head()
```

You can request a specific number of rows:

```python
df.head(2)
```

### Why this matters
- Quickly verifies that data loaded correctly.
- Helps detect column naming issues, missing values, wrong types, or malformed rows.

---

## 3. Accessing Columns

Each column is a pandas `Series`.

### Dot notation
Works only when the column name is a valid Python identifier.

```python
df.make
```

### Bracket notation
Works for any column name, including names with spaces.

```python
df["make"]
df["transmission type"]
```

### Selecting multiple columns
Use a list inside brackets.

```python
df[["make", "model", "price"]]
```

### Why this matters
- Bracket notation is more general and safer.
- Dot notation is convenient but limited.
- Columns with spaces, hyphens, or special characters require bracket notation.

---

## 4. Adding, Replacing, and Deleting Columns

### Add a new column
Assign a value to a new column name.

```python
df["id"] = [1, 2, 3, 4, 5]
```

### Replace an existing column
Assignment overwrites the old values.

```python
df["id"] = [10, 20, 30, 40, 50]
```

### Delete a column
Use `del`.

```python
del df["id"]
```

### Why this matters
- Column assignment is one of the most common data wrangling operations.
- Useful for derived features, identifiers, and cleaned versions of raw columns.

---

## 5. The Index and Row Selection

The **index** labels rows in a DataFrame.

```python
df.index
```

A default DataFrame usually has a `RangeIndex` starting at 0.

### Selecting rows with `loc`
`loc` selects rows by **index label**.

```python
df.loc[1]
df.loc[[1, 3]]
```

If the index is changed, `loc` must use the new labels.

### Selecting rows with `iloc`
`iloc` selects rows by **position**.

```python
df.iloc[1]
df.iloc[[1, 3]]
```

This works like list or NumPy indexing.

### Resetting the index
If you have a custom index and want a sequential one again:

```python
df = df.reset_index()
```

If you do not want the old index saved as a column:

```python
df = df.reset_index(drop=True)
```

### Why this matters
- Indexing is central to selecting and aligning data in pandas.
- `loc` and `iloc` serve different purposes:
  - `loc`: label-based
  - `iloc`: position-based

---

## 6. Element-wise Operations on Series

Pandas supports vectorized operations on columns.

```python
df["engine"] / 100
df["horsepower"] * 2
```

If a value is missing, the result remains missing for that entry.

### Why this matters
- Vectorized operations are fast and concise.
- They avoid Python loops for common transformations.

### Important note
Pandas Series behave similarly to NumPy arrays, but they also carry:
- an index
- a name
- nullable behavior and richer metadata

---

## 7. Filtering Rows with Boolean Conditions

To keep only rows meeting a condition, first create a boolean mask.

### Example: filter cars made after 2015

```python
df[df["year"] > 2015]
```

This works in two steps:
1. `df["year"] > 2015` creates a boolean Series
2. `df[...]` keeps only rows where the condition is `True`

### Example: filter by make

```python
df[df["make"] == "nissan"]
```

### Combine conditions
Use `&` for logical AND.

```python
df[(df["make"] == "nissan") & (df["year"] > 2015)]
```

### Why this matters
- Filtering is one of the core data cleaning and exploration operations.
- Essential for subsetting datasets before analysis or modeling.

### Important syntax rule
When combining conditions, wrap each condition in parentheses.

---

## 8. String Operations on Columns

String-cleaning is common in real datasets.

Pandas provides `.str` to apply string methods across a Series.

### Convert text to lowercase

```python
df["vehicle style"].str.lower()
```

### Replace spaces with underscores

```python
df["vehicle style"].str.replace(" ", "_")
```

### Chain operations

```python
clean_style = (
    df["vehicle style"]
    .str.replace(" ", "_")
    .str.lower()
)
```

### Assign cleaned values back
String methods return a new Series; they do not modify the original column unless assigned.

```python
df["vehicle style"] = df["vehicle style"].str.replace(" ", "_").str.lower()
```

### Why this matters
- Text normalization reduces inconsistency.
- Useful for feature engineering, grouping, and avoiding duplicate categories caused by formatting differences.

---

## 9. Summary Statistics

Pandas provides built-in summary methods for numeric Series.

### Example: price statistics

```python
df["price"].mean()
df["price"].max()
df["price"].min()
```

### Descriptive statistics
`describe()` gives a compact summary.

```python
df["price"].describe()
```

For a full DataFrame, `describe()` summarizes numeric columns only.

```python
df.describe()
```

You can round for readability:

```python
df.describe().round(2)
```

### Typical statistics returned
- count
- mean
- standard deviation
- min
- 25th percentile
- 50th percentile / median
- 75th percentile
- max

### Why this matters
- Gives a quick understanding of distributions.
- Helps identify outliers, scale differences, and missingness.

---

## 10. Unique Values and Cardinality

For categorical columns, it is useful to know how many distinct values exist.

```python
df["make"].nunique()
```

You can apply it to the whole DataFrame:

```python
df.nunique()
```

### Why this matters
- Helps understand categorical feature cardinality.
- Important for encoding choices in machine learning.
- Useful for spotting unexpectedly high or low variety in columns.

---

## 11. Missing Values

Missing values are common in real datasets.

### Identify missing values

```python
df.isnull()
```

This returns a boolean DataFrame where `True` means the value is missing.

### Count missing values per column

```python
df.isnull().sum()
```

### Why this matters
- Missing data can break models or reduce performance.
- Before training, you usually need to handle missing values explicitly.

### Engineering consideration
Common strategies include:
- dropping rows or columns
- imputing values
- using models that handle missingness
- adding missing-value indicator features

---

## 12. Grouping and Aggregation

Grouping is one of the most powerful pandas operations.

### Goal
Compute the average price per transmission type.

```python
df.groupby("transmission type")["price"].mean()
```

### General pattern
- choose a grouping column
- select a numeric column
- apply an aggregation like `mean`, `min`, `max`, or `sum`

### Example variants

```python
df.groupby("transmission type")["price"].min()
df.groupby("transmission type")["price"].max()
df.groupby("transmission type")["price"].sum()
```

### Why this matters
- Grouping lets you compare subpopulations.
- Very common in exploratory analysis, reporting, and feature engineering.

### Relation to SQL
This is the pandas equivalent of a SQL `GROUP BY` query.

---

## 13. Accessing the Underlying NumPy Array

Pandas is built on top of NumPy.

```python
df["price"].values
```

This returns the underlying array-like representation.

### Why this matters
- Useful when interfacing with libraries that expect NumPy arrays.
- Helps understand that pandas Series are higher-level wrappers around array data.

---

## 14. Converting a DataFrame to a List of Dictionaries

If you created a DataFrame from records, you can convert it back into the same style.

```python
records = df.to_dict(orient="records")
```

This returns:

```python
[
    {"make": "...", "model": "...", ...},
    {"make": "...", "model": "...", ...},
]
```

### Why this matters
- Useful for exporting data.
- Helpful when sending structured records to APIs, JSON, or custom processing code.

---

## Mermaid Diagram

```mermaid
flowchart TD
    A[Raw tabular data] --> B[Create DataFrame]
    B --> C[Inspect with head()]
    B --> D[Select columns]
    B --> E[Filter rows]
    B --> F[Add / replace / delete columns]
    B --> G[Indexing with loc / iloc]
    B --> H[String cleaning with .str]
    B --> I[Summary stats]
    B --> J[Missing value checks]
    B --> K[Groupby + aggregation]
    I --> L[Feature understanding]
    J --> M[Data cleaning]
    K --> N[Exploratory analysis]
    E --> O[Subset for modeling]
    H --> M
    D --> O
```

---

## Common Pitfalls

- **Using dot notation on invalid column names**
  - Column names with spaces or special characters require bracket notation.
- **Forgetting that string methods need `.str`**
  - `df["col"].lower()` does not work; use `df["col"].str.lower()`.
- **Assuming operations modify data in place**
  - Many pandas methods return a new object.
  - Always assign the result back if you want to keep it.
- **Confusing `loc` and `iloc`**
  - `loc` uses labels.
  - `iloc` uses integer positions.
- **Combining boolean conditions incorrectly**
  - Use `&` and parentheses, not `and`.
- **Ignoring missing values**
  - Missing values can affect summaries and break modeling pipelines.
- **Assuming `describe()` summarizes all columns**
  - It summarizes numeric columns by default.
- **Overwriting index semantics unintentionally**
  - Changing the index affects how `loc` works.

---

## Best Practices

- Inspect new datasets with `head()` immediately after loading.
- Prefer bracket notation for robust column access.
- Use `loc` for label-based row selection and `iloc` for positional selection.
- Normalize text columns early when categories should be consistent.
- Check missing values before modeling.
- Use `groupby()` for subpopulation analysis and aggregation.
- Reassign cleaned or transformed columns explicitly.
- Use `describe()` and `nunique()` to understand dataset structure quickly.
- Convert to records with `to_dict(orient="records")` when interoperating with JSON-like data.
- Keep transformations readable by chaining related string or numeric operations carefully.

---

## Key Takeaways

- Pandas is the primary Python library for working with tabular data.
- A **DataFrame** is a table; a **Series** is a labeled column.
- Pandas supports:
  - selection
  - indexing
  - filtering
  - cleaning
  - summarization
  - grouping
  - conversion to other data structures
- Many pandas operations are vectorized and act on whole columns efficiently.
- Missing values, categorical normalization, and grouping are essential tools for machine learning data preparation.

---

## Potential Project Ideas

- Load a CSV of car listings and compute descriptive statistics for price and horsepower.
- Clean a messy categorical column by lowercasing and replacing spaces with underscores.
- Build a small exploratory notebook that filters cars by make, year, and transmission type.
- Compare average price across transmission types using `groupby()`.
- Count missing values per column and design a simple imputation strategy.
- Convert a cleaned DataFrame into a list of dictionaries for JSON export.
- Create a reusable preprocessing script that standardizes column names and categorical values before model training.