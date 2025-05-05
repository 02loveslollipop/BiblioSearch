def filter_by_period(entries, start_year, end_year):
    """Filter Scopus entries by publication year"""
    filtered = []
    for entry in entries:
        if 'prism:coverDate' in entry:
            year = int(entry['prism:coverDate'].split('-')[0])
            if start_year <= year <= end_year:
                filtered.append(entry)
    return filtered
