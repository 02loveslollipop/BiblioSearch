# Biblio Search

> A simple tool to visualize articles using a search equation and Scopus API

## Disclaimer

**IMPORTANT**: This project is not affiliated with, endorsed by, or related to Scopus or Elsevier in any official capacity. It is an independent tool that utilizes the Scopus API for academic and research purposes only.

## Introduction

Biblio Search is a Streamlit-based tool that allows to visualize data obtained from the Scopus database. The application offers a variety of visualization tools including wordclouds, bar charts, choropleth maps, and animations to explore publication trends, author collaborations, geographical distributions, and keyword frequencies.

## Features

- **Comprehensive Metrics**: View article count, unique authors, organizations, and countries at a glance
- **Rich Visualizations**:
  - Word Cloud generation from keywords, titles, and descriptions
  - Top 25 authors and organizations bar charts
  - Country distribution visualizations (bar charts and world maps)
  - Publication trends over time
- **Period Analysis**: Filter results by year range for targeted trend analysis
- **Animated Visualizations**: 
  - Rolling window animations showing evolution of research topics
  - Country publication patterns over time
  - Author productivity trends
- **Data Export**: Export search results in CSV and JSON formats for further analysis

## Getting Started

### Prerequisites

- Python 3.8+
- Scopus API Key (obtainable through Elsevier Developer Portal)

### Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/02loveslollipop/BiblioSearch.git
   cd scopusBiblioSearch
   ```

2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   
   Either create a `.env` file in the project root:
   ```
   API_KEY=your_scopus_api_key_here
   ```
   
   Or enter it directly in the application when prompted.

4. **Run the application:**
   ```sh
   streamlit run main.py
   ```

### Usage

1. **Enter Search Query:**
   - Input your Scopus search equation in the sidebar
   - Set the desired number of results to retrieve

2. **Explore Visualizations:**
   - Navigate through the tabs to view different visualizations
   - Use the period selection slider to analyze specific timeframes
   - Adjust rolling window size in the animations tab to see different temporal patterns

3. **Export Data:**
   - Use the export buttons to download results in CSV or JSON format

## Example Search Queries

- Basic keyword search:
  ```
  "machine learning"
  ```

- Complex search with multiple terms:
  ```
  "natural language processing" AND "deep learning" AND PUBYEAR > 2020
  ```

- Author-specific search:
  ```
  AUTH("Smith, John") AND SUBJAREA(COMP)
  ```

## Notes on Rolling Window Animations

The animations tab provides visualizations with adjustable rolling window sizes:
- Set to 1 month for discrete monthly data
- Set to larger values (e.g., 6, 12, 24 months) to see smoothed trends over time
- The maximum window size is automatically calculated based on the date range of your results

## Acknowledgments

- This project utilizes the Scopus API for academic research purposes
- Built with Streamlit, Plotly, Matplotlib, and other open-source libraries
