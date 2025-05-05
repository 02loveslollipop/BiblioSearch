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

import models.scopus_search_equation

# load environment variables from .env file
dotenv.load_dotenv()

st.set_page_config(page_title="Scopus Visual Bibliometrics", page_icon=":bar_chart:", layout="wide")

if 'current_page' not in st.session_state:
    st.session_state.current_page = 0


# Set api_key as a persistent state variable
if 'api_key' not in st.session_state:
    try:
        api_key = st.secrets.get("api_key")
    except FileNotFoundError:
        api_key = None
    if not api_key:
        api_key = os.getenv("API_KEY")
    if not api_key:
        api_key = st.text_input("Enter your Scopus API Key", type="password")
    st.session_state['api_key'] = api_key
else:
    api_key = st.session_state['api_key']

if not api_key:
    st.warning("API key not found. Please enter your API key above.")

api = controllers.ScopusAPI(api_key)    

st.title("Scopus Visual Bibliometrics")

st.markdown("This app allows you to visualize bibliometric data from Scopus.")

st.sidebar.header("User Input")
search_equation = st.sidebar.text_input("Search Equation", "TITLE-ABS-KEY(\"machine learning\")")
search_limit = st.sidebar.number_input("Search Limit", min_value=10, value=25, step=5)

st.button("Search", key="search_button")

# Helper functions
def parse_results(entries):
    # Extract keywords, affiliations, countries, and years
    keywords = []
    orgs = []
    countries = []
    years = []
    for entry in entries:
        # Keywords: try to extract from 'authkeywords' or similar fields if available
        if 'authkeywords' in entry:
            kws = entry['authkeywords']
            if isinstance(kws, str):
                keywords.extend([k.strip() for k in kws.split(';')])
            elif isinstance(kws, list):
                keywords.extend(kws)
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
    return keywords, orgs, countries, years

def filter_by_period(entries, start_year, end_year):
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

if st.session_state.get("search_button"):
    if search_equation:
        try:
            # Validate the search equation
            search_equation = models.ScopusSearchEquation(search_equation)
            st.session_state.search_equation = search_equation
            st.success(f"Search equation is valid: {search_equation}")
            # Perform search
            from controllers.scopus_api import ScopusAPI
            #api = ScopusAPI(st.session_state['api_key'])
            result = api.search_all(search_equation, total_count=search_limit)
            entries = result.get('search-results', {}).get('entry', [])
            if not entries:
                st.warning("No results found.")
            else:
                # Parse data
                keywords, orgs, countries, years = parse_results(entries)
                # Tabs
                tab1, tab2 = st.tabs(["Overview", "Period Analysis"])
                with tab1:
                    st.subheader("Keyword Wordcloud")
                    if keywords:
                        wc = WordCloud(width=800, height=400, background_color='white').generate(' '.join(keywords))
                        fig, ax = plt.subplots(figsize=(10, 5))
                        ax.imshow(wc, interpolation='bilinear')
                        ax.axis('off')
                        st.pyplot(fig)
                    else:
                        st.info("No keywords found in results.")
                    st.subheader("Affiliations by Organization")
                    if orgs:
                        org_df = pd.DataFrame({'Organization': orgs})
                        org_count = org_df['Organization'].value_counts().reset_index()
                        org_count.columns = ['Organization', 'Count']
                        st.plotly_chart(px.bar(org_count, x='Organization', y='Count', title='Affiliations by Organization'))
                    st.subheader("Affiliations by Country")
                    if countries:
                        country_df = pd.DataFrame({'Country': countries})
                        country_count = country_df['Country'].value_counts().reset_index()
                        country_count.columns = ['Country', 'Count']
                        st.plotly_chart(px.bar(country_count, x='Country', y='Count', title='Affiliations by Country'))
                    st.subheader("Affiliations by Year")
                    if years:
                        year_df = pd.DataFrame({'Year': years})
                        year_count = year_df['Year'].value_counts().sort_index().reset_index()
                        year_count.columns = ['Year', 'Count']
                        st.plotly_chart(px.line(year_count, x='Year', y='Count', markers=True, title='Affiliations by Year'))
                with tab2:
                    st.subheader("Select Period")
                    if years:
                        min_year = min(years)
                        max_year = max(years)
                        if min_year == max_year:
                            st.info(f"All results are from the year {min_year}. No period selection available.")
                            filtered_entries = [e for e in entries if e.get('prism:coverDate', '').startswith(str(min_year))]
                        else:
                            period = st.slider("Year Range", min_value=min_year, max_value=max_year, value=(min_year, max_year))
                            filtered_entries = filter_by_period(entries, period[0], period[1])
                        f_keywords, f_orgs, f_countries, f_years = parse_results(filtered_entries)
                        st.write(f"Results in period: {len(filtered_entries)}")
                        st.subheader("Keyword Wordcloud (Period)")
                        if f_keywords:
                            wc = WordCloud(width=800, height=400, background_color='white').generate(' '.join(f_keywords))
                            fig, ax = plt.subplots(figsize=(10, 5))
                            ax.imshow(wc, interpolation='bilinear')
                            ax.axis('off')
                            st.pyplot(fig)
                        else:
                            st.info("No keywords found in period.")
                        st.subheader("Affiliations by Organization (Period)")
                        if f_orgs:
                            org_df = pd.DataFrame({'Organization': f_orgs})
                            org_count = org_df['Organization'].value_counts().reset_index()
                            org_count.columns = ['Organization', 'Count']
                            st.plotly_chart(px.bar(org_count, x='Organization', y='Count', title='Affiliations by Organization (Period)'))
                        st.subheader("Affiliations by Country (Period)")
                        if f_countries:
                            country_df = pd.DataFrame({'Country': f_countries})
                            country_count = country_df['Country'].value_counts().reset_index()
                            country_count.columns = ['Country', 'Count']
                            st.plotly_chart(px.bar(country_count, x='Country', y='Count', title='Affiliations by Country (Period)'))
                        st.subheader("Affiliations by Year (Period)")
                        if f_years:
                            year_df = pd.DataFrame({'Year': f_years})
                            year_count = year_df['Year'].value_counts().sort_index().reset_index()
                            year_count.columns = ['Year', 'Count']
                            st.plotly_chart(px.line(year_count, x='Year', y='Count', markers=True, title='Affiliations by Year (Period)'))
                    else:
                        st.info("No year information available in results.")
        except ValueError as e:
            st.error(f"Invalid search equation: {e}")
    else:
        st.warning("Please enter a search equation.")

