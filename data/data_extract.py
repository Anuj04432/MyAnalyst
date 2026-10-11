import pandas as pd

def data_info(df):
    info = {
        # Dataset
        "shape": df.shape,
        "memory_usage": df.memory_usage(deep=True).sum(),
        "dtypes": df.dtypes,
        
        # Missing data
        "total_missing": df.isnull().sum().sum(),
        "null_values": df.isnull().sum(),
        "missing_percentage": (
            df.isnull().sum() / len(df) * 100
        ).round(2),

        # Duplicates
        "duplicate_rows": df.duplicated().sum(),

        # Columns
        "numeric_columns": df.select_dtypes(include="number"),
        "categorical_columns": df.select_dtypes(include="object").columns,
        "datetime_columns": df.select_dtypes(include="datetime").columns,

        # Cardinality
        "unique_values": df.nunique(),
        
        # Numeric
        "sum": df.select_dtypes(include="number").sum().round(2),
        "mean": df.select_dtypes(include="number").mean().round(2),
        "median": df.select_dtypes(include="number").median().round(2),
        "min": df.select_dtypes(include="number").min().round(2),
        "max": df.select_dtypes(include="number").max().round(2),
        "std": df.select_dtypes(include="number").std().round(2),
        "variance": df.select_dtypes(include="number").var().round(2),

        # Relationships
        "correlation": df.select_dtypes(include="number").corr(),

        # Statistical distribution
        "skewness": df.select_dtypes(include="number").skew(),
        "kurtosis": df.select_dtypes(include="number").kurt(),

        # Categorical
        "categorical_summary": {
            col: df[col].value_counts().head(10)
            for col in df.select_dtypes(include="object").columns
        }
    }
    return info