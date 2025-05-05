import pandas as pd
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re
from collections import Counter
import io
import imageio
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import streamlit as st

def parse_results_for_animation(entries):
    """Extracts date, country, author, and words for each entry."""
    data = []
    for entry in entries:
        # Extract date
        date_str = entry.get('prism:coverDate')
        try:
            # Handle cases like '2023', '2023-05', '2023-05-15'
            if date_str:
                if len(date_str) == 4: # Year only
                    date = datetime.strptime(f"{date_str}-01-01", '%Y-%m-%d')
                elif len(date_str) == 7: # Year-Month
                     date = datetime.strptime(f"{date_str}-01", '%Y-%m-%d')
                else: # Full date
                    date = datetime.strptime(date_str, '%Y-%m-%d')
            else:
                date = None # Skip entries without date for time-based animation
        except (ValueError, TypeError):
            date = None # Skip entries with invalid date format

        if not date:
            continue

        # Extract country
        countries_entry = []
        if 'affiliation' in entry:
            affiliations = entry['affiliation']
            if isinstance(affiliations, list):
                for aff in affiliations:
                    if isinstance(aff, dict) and 'affiliation-country' in aff:
                        countries_entry.append(aff['affiliation-country'])
            elif isinstance(affiliations, dict) and 'affiliation-country' in affiliations:
                countries_entry.append(affiliations['affiliation-country'])

        # Extract author
        authors_entry = []
        author_found = False
        if 'author' in entry:
            entry_authors = entry['author']
            if isinstance(entry_authors, list):
                for author in entry_authors:
                    if isinstance(author, dict) and 'authname' in author:
                        authors_entry.append(author['authname'])
                        author_found = True
            elif isinstance(entry_authors, dict) and 'authname' in entry_authors:
                authors_entry.append(entry_authors['authname'])
                author_found = True
        if not author_found and 'dc:creator' in entry:
             creator_name = entry.get('dc:creator')
             if creator_name and isinstance(creator_name, str):
                 authors_entry.append(creator_name)

        # Extract words (unique per article)
        article_unique_words = set()
        # Keywords
        if 'authkeywords' in entry:
            keywords_str = entry.get('authkeywords', "") or ""
            entry_keywords = keywords_str.split(' | ')
            for keyword in entry_keywords:
                 # Basic cleaning: lower, strip whitespace
                cleaned_keyword = keyword.strip().lower()
                if cleaned_keyword:
                    article_unique_words.add(cleaned_keyword)
        # Title
        title = entry.get('dc:title', "") or ""
        words_title = re.findall(r'\b\w+\b', title.lower())
        article_unique_words.update(words_title)
        # Description
        description = entry.get('dc:description', "") or ""
        words_desc = re.findall(r'\b\w+\b', description.lower())
        article_unique_words.update(words_desc)

        # Add data for this entry
        data.append({
            'date': date,
            'countries': list(set(countries_entry)), # Unique countries for this entry
            'authors': list(set(authors_entry)),     # Unique authors for this entry
            'words': list(article_unique_words)
        })

    if not data:
        return pd.DataFrame(columns=['date', 'countries', 'authors', 'words'])

    # Create DataFrame with lists, then process each animation separately
    df = pd.DataFrame(data)
    df = df.dropna(subset=['date']) # Ensure date is present
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df


def prepare_rolling_data(df, months_window=6):
    """Calculates rolling counts/frequencies over a specified window."""
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), [], []

    df = df.copy() # Create a copy to avoid SettingWithCopyWarning
    min_date = df['date'].min()
    max_date = df['date'].max()

    if pd.isna(min_date) or pd.isna(max_date):
         return pd.DataFrame(), pd.DataFrame(), [], []

    # Create monthly periods for animation frames
    # Ensure the range includes the last month properly
    periods = pd.date_range(start=min_date.to_period('M').to_timestamp(),
                            end=max_date.to_period('M').to_timestamp() + pd.offsets.MonthEnd(0),
                            freq='M')

    rolling_country_data = []
    rolling_author_data = []
    rolling_word_data = []

    for period_end_date in periods:
        period_start_date = period_end_date - relativedelta(months=months_window - 1)
        period_start_date = period_start_date.replace(day=1) # Start of the month

        # Filter data within the rolling window [period_start_date, period_end_date]
        window_df = df[(df['date'] >= period_start_date) & (df['date'] <= period_end_date)]

        if window_df.empty:
            continue

        month_str = period_end_date.strftime('%Y-%m')

        # Country counts
        country_counts = []
        for _, row in window_df.iterrows():
            for country in row['countries']:
                if country:  # Skip empty strings
                    country_counts.append(country)
        
        if country_counts:
            country_df = pd.DataFrame({'Country': country_counts})
            country_counts = country_df['Country'].value_counts().reset_index()
            country_counts.columns = ['Country', 'Count']
            country_counts['Month'] = month_str
            rolling_country_data.append(country_counts)

        # Author counts
        author_counts = []
        for _, row in window_df.iterrows():
            for author in row['authors']:
                if author:  # Skip empty strings
                    author_counts.append(author)
        
        if author_counts:
            author_df = pd.DataFrame({'Author': author_counts})
            author_counts = author_df['Author'].value_counts().reset_index()
            author_counts.columns = ['Author', 'Count']
            # Get top N authors for the frame
            top_authors = author_counts.nlargest(25, 'Count')
            top_authors['Month'] = month_str
            rolling_author_data.append(top_authors)

        # Word counts
        word_counts = Counter()
        for _, row in window_df.iterrows():
            for word in row['words']:
                if word:  # Skip empty strings
                    word_counts[word] += 1
        
        # Keep top N words for the frame (e.g., top 100 for word cloud)
        top_words = dict(word_counts.most_common(100))
        if top_words:  # Only add if there are words
             rolling_word_data.append({'Month': month_str, 'WordCounts': top_words})


    all_country_df = pd.concat(rolling_country_data, ignore_index=True) if rolling_country_data else pd.DataFrame(columns=['Country', 'Count', 'Month'])
    all_author_df = pd.concat(rolling_author_data, ignore_index=True) if rolling_author_data else pd.DataFrame(columns=['Author', 'Count', 'Month'])
    
    # Get list of unique months
    months = []
    if not all_country_df.empty and 'Month' in all_country_df.columns:
        months.extend(all_country_df['Month'].unique())
    if not all_author_df.empty and 'Month' in all_author_df.columns:
        months.extend(all_author_df['Month'].unique())
    unique_months = sorted(set(months))

    return all_country_df, all_author_df, rolling_word_data, unique_months


def calculate_max_window(df):
    """Calculate the maximum allowed rolling window size in months based on dataset timespan."""
    if df.empty:
        return 6  # Default window size
    
    min_date = df['date'].min()
    max_date = df['date'].max()
    
    if pd.isna(min_date) or pd.isna(max_date):
        return 6  # Default if dates are invalid
    
    # Calculate months between min and max dates
    months_diff = ((max_date.year - min_date.year) * 12 + 
                   (max_date.month - min_date.month))
    
    # Maximum window is the smaller of: 24 months (2 years) or total months - 1
    # We need at least 2 months of data to have a rolling window
    if months_diff <= 1:
        return 1  # Minimum window size
    else:
        return min(24, months_diff)  # Cap at 24 months (2 years)


# --- Function: Generate Animated Country Map (Plotly) ---
@st.cache_data(show_spinner=False)
def generate_animated_country_map(country_df, window_size=6):
    """Generates an animated choropleth map of publication counts by country."""
    if country_df.empty or 'Month' not in country_df.columns:
        return None
    # Ensure months are sorted for animation order
    country_df = country_df.sort_values('Month')
    # Find the global max count for consistent color scale
    max_count = country_df['Count'].max()

    # Format window description for title
    window_desc = f"{window_size}-Month" if window_size > 1 else "Monthly"

    try:
        fig = px.choropleth(country_df,
                            locations="Country",
                            locationmode='country names',
                            color="Count",
                            hover_name="Country",
                            animation_frame="Month",
                            color_continuous_scale=px.colors.sequential.Plasma,
                            range_color=[0, max_count], # Consistent color scale
                            title=f"Publications per Country ({window_desc} Rolling Window)")

        fig.update_layout(
            geo=dict(
                showframe=False,
                showcoastlines=True,
                showland=True,
                landcolor='rgb(217, 217, 217)',
                bgcolor='rgba(0,0,0,0)',
                projection_type='natural earth'
            ),
            margin={"r":0,"t":40,"l":0,"b":0} # Adjust margins
        )
        # Adjust animation speed (optional)
        fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 1000 # ms per frame
        fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 300 # ms transition

        return fig
    except Exception as e:
        st.warning(f"Could not generate animated world map: {e}")
        return None

# --- Function: Generate Animated Author Bar Chart (Plotly) ---
@st.cache_data(show_spinner=False)
def generate_animated_author_chart(author_df, window_size=6):
    """Generates an animated bar chart of publication counts by author."""
    if author_df.empty or 'Month' not in author_df.columns:
        return None
    
    # Get the unique months
    months = author_df['Month'].unique()
    
    # Find the global top 25 authors across all months for consistent ordering
    top_global_authors = author_df.groupby('Author')['Count'].sum().nlargest(25).index.tolist()
    
    # If we have less than 25 authors, use all available
    if len(top_global_authors) < 25:
        # Get all unique authors
        all_authors = author_df['Author'].unique().tolist()
        # Use all authors instead
        top_global_authors = all_authors
    
    # Ensure months are sorted
    author_df = author_df.sort_values(['Month', 'Count'], ascending=[True, False])
    
    # Find the global max count for consistent y-axis
    max_count = author_df['Count'].max()
    
    # Format window description for title
    window_desc = f"{window_size}-Month" if window_size > 1 else "Monthly"
    
    # Create a complete dataframe with all top authors for each month (filling missing values with 0)
    complete_df = []
    
    for month in months:
        month_data = author_df[author_df['Month'] == month]
        month_authors = set(month_data['Author'].tolist())
        
        # Add existing authors
        complete_df.append(month_data)
        
        # Add missing top authors with count 0
        missing_authors = [author for author in top_global_authors if author not in month_authors]
        if missing_authors:
            missing_df = pd.DataFrame({
                'Author': missing_authors,
                'Count': [0] * len(missing_authors),
                'Month': [month] * len(missing_authors)
            })
            complete_df.append(missing_df)
    
    if not complete_df:
        return None
    
    # Combine all dataframes
    complete_author_df = pd.concat(complete_df, ignore_index=True)
    
    try:
        # Create the bar chart with custom category ordering
        fig = px.bar(
            complete_author_df,
            x="Author",
            y="Count",
            color="Author",  # Color by author
            animation_frame="Month",
            title=f"Top 25 Authors ({window_desc} Rolling Window)",
            range_y=[0, max_count * 1.1],  # Consistent y-axis + 10% padding
            category_orders={"Author": top_global_authors}  # Force consistent author ordering
        )
        
        # Improve layout
        fig.update_xaxes(tickangle=45)  # Angle labels for better readability
        fig.update_layout(
            showlegend=False,  # Hide legend if too cluttered
            height=600,  # Increase height for better visibility
            xaxis={'visible': True, 'title': ''},  # Remove x-axis title
            margin={"r": 20, "t": 40, "l": 20, "b": 80}  # Adjust margins
        )
        
        # Adjust animation settings
        fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 1000  # ms per frame
        fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 300  # ms transition
        
        return fig
    except Exception as e:
        st.warning(f"Could not generate animated author chart: {e}")
        return None


# --- Function: Generate Animated Word Cloud (Matplotlib/Imageio) ---
@st.cache_data(show_spinner=False)
def generate_animated_word_cloud_gif(word_data_list, window_size=6):
    """Generates an animated GIF of word clouds over time."""
    if not word_data_list:
        return None

    # Format window description for title
    window_desc = f"{window_size}-Month" if window_size > 1 else "Monthly"

    try:
        # Sort data by month
        word_data_list = sorted(word_data_list, key=lambda x: x['Month'])
        months = [item['Month'] for item in word_data_list]
        word_counts_per_month = [item['WordCounts'] for item in word_data_list]

        fig, ax = plt.subplots(figsize=(8, 4))
        plt.tight_layout(pad=0) # Reduce padding
        ax.axis("off") # Turn off axis

        images = [] # List to store frames for GIF

        # Pre-generate all wordclouds to avoid issues within FuncAnimation
        wc_objects = []
        for word_counts in word_counts_per_month:
             if word_counts:
                 wc = WordCloud(width=400, height=200, background_color='white').generate_from_frequencies(word_counts)
                 wc_objects.append(wc)
             else:
                 # Handle empty frames - maybe generate an empty image or skip
                 wc_objects.append(None) # Placeholder for empty

        # Create frames
        for i, wc in enumerate(wc_objects):
            ax.clear() # Clear previous frame
            ax.axis("off")
            if wc:
                 ax.imshow(wc, interpolation="bilinear")
            else:
                 # Display placeholder text for empty frames
                 ax.text(0.5, 0.5, 'No data for this period', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)

            ax.set_title(f"Word Cloud ({window_desc} Rolling) - {months[i]}", fontsize=10)
            fig.canvas.draw() # Draw the canvas, cache the renderer

            # Convert plot to image data
            image = io.BytesIO()
            plt.savefig(image, format='png', bbox_inches='tight', pad_inches=0.1)
            image.seek(0)
            images.append(imageio.imread(image))

        plt.close(fig) # Close the figure after loop

        # Save frames as GIF
        gif_bytes = io.BytesIO()
        imageio.mimsave(gif_bytes, images, duration=1.0, format='GIF') # duration in seconds per frame
        gif_bytes.seek(0)
        return gif_bytes.getvalue()

    except Exception as e:
        st.warning(f"Could not generate animated word cloud GIF: {e}")
        # Fallback or error indication
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, f"Word Cloud Animation Failed:\n{e}", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, color='red')
        ax.axis("off")
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()