import streamlit as st
import controllers
import models
import os
import dotenv
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import plotly.express as px
from datetime import datetime
from utils import limit_dataframe_for_graph, parse_results, filter_by_period
from utils.animations import (parse_results_for_animation, prepare_rolling_data, 
                           generate_animated_country_map, generate_animated_author_chart,
                           generate_animated_word_cloud_gif, calculate_max_window)
import json # Added import

# --- Caching Helper Functions ---
@st.cache_data
def generate_wordcloud_figure(words_list): # Renamed parameter
    """Generates a WordCloud figure from a list of words.""" # Updated docstring
    if not words_list:
        return None
    # Join the list of words into a single string for the word cloud
    text = ' '.join(words_list)
    wc = WordCloud(width=800, height=400, background_color='white').generate(text)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    return fig

@st.cache_data
def generate_bar_chart(data_list, column_name, title):
    """Generates a Plotly bar chart for top 25 items."""
    if not data_list:
        return None
    df = pd.DataFrame({column_name: data_list})
    count_df = df[column_name].value_counts().reset_index()
    count_df.columns = [column_name, 'Count']
    count_df = limit_dataframe_for_graph(count_df, 'Count', column_name)
    if count_df.empty:
        return None
    fig = px.bar(count_df, x=column_name, y='Count', title=title)
    return fig

@st.cache_data
def generate_line_chart(years_list, title):
    """Generates a Plotly line chart for publications by year."""
    if not years_list:
        return None
    year_df = pd.DataFrame({'Year': years_list})
    year_count = year_df['Year'].value_counts().sort_index().reset_index()
    year_count.columns = ['Year', 'Count']
    if year_count.empty:
        return None
    fig = px.line(year_count, x='Year', y='Count', markers=True, title=title)
    return fig

@st.cache_data
def generate_country_map(countries_list, title):
    """Generates a Plotly choropleth map for publications by country."""
    if not countries_list:
        return None
    country_df = pd.DataFrame({'Country': countries_list})
    country_count = country_df['Country'].value_counts().reset_index()
    country_count.columns = ['Country', 'Count']
    if country_count.empty:
        return None
    
    # Attempt to create the choropleth map
    try:
        fig = px.choropleth(country_count, 
                            locations="Country", 
                            locationmode='country names', # Use country names directly
                            color="Count",
                            hover_name="Country", 
                            color_continuous_scale=px.colors.sequential.Plasma,
                            title=title,
                            # Set a range to ensure the color scale is consistent
                            range_color=[0, country_count['Count'].max()]
                           )
        # Update layout to show all landmasses and fit bounds
        fig.update_layout(
            geo=dict(
                showframe=False, 
                showcoastlines=True, # Keep coastlines for definition
                showland=True,       # Explicitly show land
                landcolor='rgb(217, 217, 217)', # Set color for land without data
                bgcolor='rgba(0,0,0,0)', # Make overall background transparent
                fitbounds="locations" # Fit map bounds to the locations with data
            ),
            margin={"r":0,"t":30,"l":0,"b":0} # Adjust margins for better fit
        )
        return fig
    except Exception as e:
        # Log the error or inform the user if country names are not recognized
        st.warning(f"Could not generate world map. Some country names might not be recognized: {e}")
        return None

# load environment variables from .env file
dotenv.load_dotenv()

st.set_page_config(page_title="Scopus Visual Bibliometrics", page_icon=":bar_chart:", layout="wide")

if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

# Initialize session state variables for search results and parsed data
if 'total_available_results' not in st.session_state:
    st.session_state.total_available_results = None
if 'displayed_results_count' not in st.session_state:
    st.session_state.displayed_results_count = None
if 'entries' not in st.session_state:
    st.session_state.entries = None
if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None
if 'results_available' not in st.session_state:
    st.session_state.results_available = False

# Set api_key as a persistent state variable
if 'api_key' not in st.session_state:
    api_key = os.getenv("API_KEY")
    if not api_key:
        api_key = st.text_input("Enter your Scopus API Key, get one from [Elsevier developer portal](https://dev.elsevier.com/apikey/manage)", type="password")
    st.session_state['api_key'] = api_key
else:
    api_key = st.session_state['api_key']

if not api_key:
    st.warning("API key not found. Please enter your API key above. If you don't trust this app, check the [github repo](%s) and run it locally" % "https://github.com/02loveslollipop/scopusBiblioSearch")

api = controllers.ScopusAPI(api_key)    

st.title("Scopus Visual Bibliometrics")

st.markdown("This app allows you to visualize bibliometric data from Scopus.")

st.sidebar.header("User Input")
search_equation = st.sidebar.text_input("Search Equation", '"natural language processing" AND "Self-supervised learning" AND "Large language model" AND "transfer learning" AND "Machine learning" AND "Reinforcement learning"')
search_limit = st.sidebar.number_input("Search Limit", min_value=10, value=25, step=5)

st.button("Search", key="search_button")

# Display total results info if available
if st.session_state.total_available_results is not None:
    st.info(f"📊 Found {st.session_state.total_available_results:,} total results in Scopus (showing top {st.session_state.displayed_results_count})")

# Handle search button click
if st.session_state.get("search_button"):
    if search_equation:
        try:
            # Validate the search equation
            search_equation = models.ScopusSearchEquation(search_equation)
            st.session_state.search_equation = search_equation
            st.success(f"Search equation is valid: {search_equation}")
            
            # Perform search
            with st.spinner("Searching Scopus..."):
                result = api.search_all(search_equation, total_count=search_limit)
                entries = result.get('search-results', {}).get('entry', [])
            
            if not entries:
                st.warning("No results found.")
                # Reset the results counts and data in session state
                st.session_state.total_available_results = None
                st.session_state.displayed_results_count = None
                st.session_state.entries = None
                st.session_state.parsed_data = None
                st.session_state.results_available = False
            else:
                # Store data in session state
                st.session_state.entries = entries
                st.session_state.total_available_results = int(result.get('search-results', {}).get('opensearch:totalResults', 0))
                st.session_state.displayed_results_count = len(entries)
                
                # Parse data and store in session state
                with st.spinner("Parsing results..."):
                    parsed_data = parse_results(entries)
                    st.session_state.parsed_data = parsed_data
                
                st.session_state.results_available = True
                # Rerun to display results immediately after search
                st.rerun() 

        except ValueError as e:
            st.error(f"Invalid search equation: {e}")
            st.session_state.results_available = False
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.session_state.results_available = False
    else:
        st.warning("Please enter a search equation.")
        st.session_state.results_available = False

# Display results if available in session state
if st.session_state.results_available and st.session_state.entries:
    # Unpack parsed data - updated variable name
    words_for_cloud, orgs, countries, years, authors = st.session_state.parsed_data 
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Articles", len(st.session_state.entries))
    with col2:
        st.metric("Unique Authors", len(set(authors)))
    with col3:
        st.metric("Organizations", len(set(orgs)))
    with col4:
        st.metric("Countries", len(set(countries)))

    # --- Add Export Buttons ---
    st.markdown("---") # Separator
    st.subheader("Export Full Results")
    
    # Prepare data for export
    export_df = pd.DataFrame(st.session_state.entries)
    # Flatten potential list/dict columns for better CSV/JSON export if needed
    # For simplicity, exporting raw entries for now. Complex structures might need flattening.
    
    csv_data = export_df.to_csv(index=False).encode('utf-8')
    json_data = json.dumps(st.session_state.entries, indent=4)

    col_export1, col_export2 = st.columns(2)
    with col_export1:
        st.download_button(
            label="📥 Export as CSV",
            data=csv_data,
            file_name='scopus_results.csv',
            mime='text/csv',
        )
    with col_export2:
        st.download_button(
            label="📥 Export as JSON",
            data=json_data,
            file_name='scopus_results.json',
            mime='application/json',
        )
    st.markdown("---") # Separator
    # --- End Export Buttons ---

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Overview", "Period Analysis", "Animations"])
    with tab1:
        st.subheader("Word Cloud (Keywords, Title, Description)") # Updated subheader
        if words_for_cloud: # Use updated variable
            fig = generate_wordcloud_figure(words_for_cloud) # Pass updated variable
            if fig:
                st.pyplot(fig)
            else:
                st.info("No words found in results for word cloud.") # Updated info message
            
        st.subheader("Top 25 Authors") # Moved Author Graph Section here
        if authors:
            fig_author_bar = generate_bar_chart(tuple(authors), 'Author', 'Top 25 Authors') # Use tuple
            if fig_author_bar:
                st.plotly_chart(fig_author_bar)
            else:
                st.info("No author data found.")
            
        st.subheader("Top 25 Organizations")
        if orgs:
            fig = generate_bar_chart(orgs, 'Organization', 'Top 25 Organizations')
            if fig:
                st.plotly_chart(fig)
            
        st.subheader("Top 25 Countries (Bar Chart)")
        if countries:
            fig_country_bar = generate_bar_chart(tuple(countries), 'Country', 'Top 25 Countries') # Use tuple
            if fig_country_bar:
                st.plotly_chart(fig_country_bar)
            else:
                st.info("No country data found.") 

        st.subheader("Country Distribution (World Map)")
        if countries:
            fig_country_map = generate_country_map(tuple(countries), 'Publication Distribution by Country') # Use tuple
            if fig_country_map:
                st.plotly_chart(fig_country_map)
            
        st.subheader("Publications by Year")
        if years:
            fig = generate_line_chart(years, 'Publications by Year')
            if fig:
                st.plotly_chart(fig)

    with tab2:
        st.subheader("Select Period")
        if years:
            min_year = min(years)
            max_year = max(years)
            if min_year == max_year:
                st.info(f"All results are from the year {min_year}. No period selection available.")
                filtered_entries = [e for e in st.session_state.entries if e.get('prism:coverDate', '').startswith(str(min_year))]
            else:
                # Use a key for the slider to maintain its state across reruns
                period = st.slider("Year Range", min_value=min_year, max_value=max_year, value=(min_year, max_year), key="period_slider")
                # Filter entries based on the slider value
                filtered_entries = filter_by_period(st.session_state.entries, period[0], period[1])
                
            # Parse only the filtered entries for this tab
            # Unpack parsed data - updated variable name
            f_words_for_cloud, f_orgs, f_countries, f_years, f_authors = parse_results(filtered_entries)
            
            # Display filtered metrics and visualizations
            col1_f, col2_f, col3_f, col4_f = st.columns(4)
            with col1_f:
                st.metric("Articles in Period", len(filtered_entries))
            with col2_f:
                st.metric("Authors in Period", len(set(f_authors)))
            with col3_f:
                st.metric("Organizations in Period", len(set(f_orgs)))
            with col4_f:
                st.metric("Countries in Period", len(set(f_countries)))
            
            st.subheader("Word Cloud (Period - Keywords, Title, Description)") # Updated subheader
            if f_words_for_cloud: # Use updated variable
                fig_f = generate_wordcloud_figure(f_words_for_cloud) # Pass updated variable
                if fig_f:
                    st.pyplot(fig_f)
                else:
                    st.info("No words found in period for word cloud.") # Updated info message
            
            st.subheader("Top 25 Authors (Period)") # Moved Author Graph Section here
            if f_authors:
                fig_author_bar_f = generate_bar_chart(tuple(f_authors), 'Author', 'Top 25 Authors (Period)') # Use tuple
                if fig_author_bar_f:
                    st.plotly_chart(fig_author_bar_f)
                else:
                    st.info("No author data found in period.")
                
            if f_orgs:
                fig_f = generate_bar_chart(f_orgs, 'Organization', 'Top 25 Organizations (Period)')
                if fig_f:
                    st.subheader("Top 25 Organizations (Period)")
                    st.plotly_chart(fig_f)
                
            st.subheader("Top 25 Countries (Period - Bar Chart)")
            if f_countries:
                fig_country_bar_f = generate_bar_chart(tuple(f_countries), 'Country', 'Top 25 Countries (Period)') # Use tuple
                if fig_country_bar_f:
                    st.plotly_chart(fig_country_bar_f)
                else:
                    st.info("No country data found in period.") 

            st.subheader("Country Distribution (Period - World Map)")
            if f_countries:
                fig_country_map_f = generate_country_map(tuple(f_countries), 'Publication Distribution by Country (Period)') # Use tuple
                if fig_country_map_f:
                    st.plotly_chart(fig_country_map_f)
                
            if f_years:
                fig_f = generate_line_chart(f_years, 'Publications by Year (Period)')
                if fig_f:
                    st.subheader("Publications by Year (Period)")
                    st.plotly_chart(fig_f)

    # --- New Animations Tab ---
    with tab3:
        st.header("Animated Visualizations")
        st.markdown("""
            These animations show trends over time based on data aggregated over a rolling window.
            You can adjust the window size using the slider below.
        """)

        # Prepare data for animations (run once)
        with st.spinner("Preparing data for animations..."):
            anim_df = parse_results_for_animation(st.session_state.entries)
            if anim_df.empty:
                st.warning("Not enough date information in the results to generate animations.")
            else:
                # Calculate max window size based on dataset timespan
                max_window_size = calculate_max_window(anim_df)
                
                # Add slider for rolling window selection
                window_size = st.slider(
                    "Rolling Window Size (months)", 
                    min_value=1, 
                    max_value=max_window_size,
                    value=min(6, max_window_size),  # Default to 6 months if possible
                    step=1,
                    help="Select 1 month for no rolling window, or larger values to see trends over time"
                )
                
                # Generate rolling data with selected window size
                country_anim_df, author_anim_df, word_anim_list, anim_months = prepare_rolling_data(
                    anim_df, months_window=window_size
                )
                
                # Show a description of the selected rolling window
                if window_size == 1:
                    st.info("📊 Showing data by month (no rolling)")
                else:
                    st.info(f"📊 Showing data with a {window_size}-month rolling window")

        if not anim_df.empty and anim_months:
            st.markdown("---")
            st.subheader("Animated Country Map")
            with st.spinner("Generating country map animation..."):
                country_map_anim_fig = generate_animated_country_map(country_anim_df, window_size=window_size)
            if country_map_anim_fig:
                st.plotly_chart(country_map_anim_fig, use_container_width=True)
            else:
                st.info("Could not generate animated country map (perhaps no country data or animation frames).")

            st.markdown("---")
            st.subheader("Animated Top Authors Chart")
            with st.spinner("Generating author chart animation..."):
                author_chart_anim_fig = generate_animated_author_chart(author_anim_df, window_size=window_size)
            if author_chart_anim_fig:
                st.plotly_chart(author_chart_anim_fig, use_container_width=True)
            else:
                st.info("Could not generate animated author chart (perhaps no author data or animation frames).")

            st.markdown("---")
            st.subheader("Animated Word Cloud")
            with st.spinner("Generating word cloud animation (this may take a while)..."):
                word_cloud_anim_gif = generate_animated_word_cloud_gif(word_anim_list, window_size=window_size)
            if word_cloud_anim_gif:
                st.image(word_cloud_anim_gif, caption=f"Animated Word Cloud ({window_size}-Month Rolling Window)")
            else:
                st.info("Could not generate animated word cloud (perhaps no word data or animation frames).")
        elif not anim_df.empty:
             st.warning("Could not generate animation frames. Check if data spans multiple months.")