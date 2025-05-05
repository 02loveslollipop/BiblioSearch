def limit_dataframe_for_graph(df, count_column, name_column, top_n=25):
    """Limit dataframe to top N entries based on count"""
    if len(df) > top_n:
        top_entries = df.nlargest(top_n, count_column)
        return top_entries
    return df