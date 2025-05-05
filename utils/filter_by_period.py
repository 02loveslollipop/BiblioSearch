def filter_by_period(entries, start_year, end_year):
    """
    Filter Scopus API entries by a year range (inclusive).
    """
    filtered = []
    for entry in entries:
        date_str = entry.get('prism:coverDate')
        if date_str:
            try:
                year = int(date_str[:4])
                if start_year <= year <= end_year:
                    filtered.append(entry)
            except Exception:
                continue
    return filtered
