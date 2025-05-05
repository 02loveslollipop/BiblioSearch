def clean_text(text):
    """
    Clean text by removing special characters and numbers, converting to lowercase,
    and splitting into individual words.
    """
    import re
    # Convert to lowercase and remove special characters
    text = re.sub(r'[^a-zA-Z\s]', ' ', text.lower())
    # Split into words and remove empty strings and single characters
    words = [word.strip() for word in text.split() if len(word.strip()) > 2]
    return words

def parse_results(entries):
    """
    Extract keywords, titles, affiliations, countries, years and authors from Scopus API entries.
    Combines keywords and title words for word cloud generation.
    """
    keywords = []
    orgs = []
    countries = []
    years = []
    authors = []
    
    # Common English stop words to filter out
    stop_words = {'and', 'the', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    for entry in entries:
        # Keywords from authkeywords
        if 'authkeywords' in entry:
            kws = entry['authkeywords']
            if isinstance(kws, str):
                keywords.extend([k.strip().lower() for k in kws.split('|')])
            elif isinstance(kws, list):
                keywords.extend([k.lower() for k in kws])
        
        # Words from title
        if 'dc:title' in entry:
            title_words = clean_text(entry['dc:title'])
            # Filter out stop words
            title_words = [w for w in title_words if w not in stop_words]
            keywords.extend(title_words)
        
        # Authors
        if 'author' in entry:
            for author in entry['author']:
                # Use authname if available, otherwise construct from given-name and surname
                author_name = author.get('authname', '')
                if not author_name and 'surname' in author:
                    given_name = author.get('given-name', '')
                    surname = author.get('surname', '')
                    author_name = f"{surname}, {given_name}" if given_name else surname
                if author_name:
                    authors.append(author_name)
        
        # Affiliations
        for aff in entry.get('affiliation', []):
            orgs.append(aff.get('affilname', 'Unknown'))
            countries.append(aff.get('affiliation-country', 'Unknown'))
        
        # Year
        date_str = entry.get('prism:coverDate')
        if date_str:
            try:
                year = int(date_str[:4])
                years.append(year)
            except Exception:
                pass
    
    return keywords, orgs, countries, years, authors