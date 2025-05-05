import re

def parse_results(entries):
    """Extract unique words (from keywords, title, description), affiliations, countries, years, and authors from Scopus entries"""
    all_words_for_cloud = []
    orgs = []
    countries = []
    years = []
    authors = []

    for entry in entries:
        article_unique_words = set()

        # Extract and process keywords
        if 'authkeywords' in entry:
            keywords_str = entry['authkeywords'] or ""
            entry_keywords = keywords_str.split(' | ')
            for keyword in entry_keywords:
                cleaned_keyword = keyword.strip().lower()
                if cleaned_keyword:
                    article_unique_words.add(cleaned_keyword)

        # Extract and process title
        if 'dc:title' in entry:
            title = entry['dc:title'] or ""
            words = re.findall(r'\b\w+\b', title.lower())
            article_unique_words.update(words)

        # Extract and process description
        if 'dc:description' in entry:
            description = entry['dc:description'] or ""
            words = re.findall(r'\b\w+\b', description.lower())
            article_unique_words.update(words)

        all_words_for_cloud.extend(list(article_unique_words))

        # Extract affiliations and countries
        if 'affiliation' in entry:
            affiliations = entry['affiliation']
            if isinstance(affiliations, list):
                for aff in affiliations:
                    if isinstance(aff, dict):
                        if 'affilname' in aff:
                            orgs.append(aff['affilname'])
                        if 'affiliation-country' in aff:
                            countries.append(aff['affiliation-country'])
            elif isinstance(affiliations, dict):
                if 'affilname' in affiliations:
                    orgs.append(affiliations['affilname'])
                if 'affiliation-country' in affiliations:
                    countries.append(affiliations['affiliation-country'])

        # Extract year
        if 'prism:coverDate' in entry:
            year_str = entry['prism:coverDate']
            if year_str and isinstance(year_str, str): # Check if string and not empty
                year = year_str.split('-')[0]
                try: # Add try-except for robustness
                    years.append(int(year))
                except ValueError:
                    pass # Ignore if year is not a valid integer

        # Extract authors
        # Prioritize the 'author' list/dict if available
        author_found = False
        if 'author' in entry:
            entry_authors = entry['author']
            if isinstance(entry_authors, list):
                for author in entry_authors:
                    # Check if author is a dict and has 'authname'
                    if isinstance(author, dict) and 'authname' in author:
                        authors.append(author['authname'])
                        author_found = True # Mark as found
            elif isinstance(entry_authors, dict) and 'authname' in entry_authors: # Handle single author case
                authors.append(entry_authors['authname'])
                author_found = True # Mark as found
        
        # If no author found in 'author' list/dict, check 'dc:creator'
        if not author_found and 'dc:creator' in entry:
            creator_name = entry['dc:creator']
            if creator_name and isinstance(creator_name, str):
                authors.append(creator_name)

    return all_words_for_cloud, orgs, countries, years, authors