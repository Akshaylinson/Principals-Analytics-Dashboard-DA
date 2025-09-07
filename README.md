Principals Analytics Dashboard
A professional data analytics dashboard built with Flask and Plotly for analyzing and visualizing principal data from Excel spreadsheets.

Features
Comprehensive Data Visualization: Interactive charts including bar charts, pie charts, treemaps, heatmaps, and prediction trends

Data Quality Analysis: Scorecards for data completeness and quality metrics

Geographic Distribution: Visual representation of data across states and cities

Advanced Filtering: Server-side processed datatable with search and pagination

Professional UI: Modern glassmorphism design with responsive layout

Export Functionality: Download data as CSV for further analysis

Installation
Clone or download the project files

Install the required dependencies:

bash
pip install -r requirements.txt
Requirements
The requirements.txt file includes:

text
Flask==3.0.3
pandas==2.2.2
openpyxl==3.1.5
numpy==1.26.4
scipy==1.13.0
Usage
Place your Excel file (Principals 14180.xlsx) in the project directory

Run the Flask application:

bash
python app.py
Open your web browser and navigate to http://localhost:5000

Project Structure
text
principals_analytics/
├── templates/
│   └── index.html          # Main dashboard template
├── app.py                  # Flask backend application
├── Principals 14180.xlsx   # Input Excel data file
├── principals_cache.csv    # Generated cache file
└── requirements.txt        # Python dependencies
API Endpoints
/ - Main dashboard page

/api/summary - Key performance indicators

/api/top-states - Top states by count

/api/top-cities - Top cities by count

/api/phones-by-state - Phone completeness by state

/api/treemap-states - Treemap data for states

/api/state-city-heatmap - Heatmap matrix data

/api/table - Server-side processed data table

/api/predictions - Trend predictions

/api/data-quality - Data quality metrics

/api/geographic-distribution - Geographic data

/download/csv - CSV export endpoint

Data Requirements
The application expects an Excel file with the following columns (names are automatically detected):

Principal/Name column

City column

State/Region column

Phone number column (optional)

Date column (optional, for trend analysis)

Customization
You can customize the dashboard by:

Modifying the color scheme in the CSS variables

Adjusting chart parameters in the JavaScript functions

Adding new API endpoints in app.py

Changing the layout in templates/index.html

Browser Support
This dashboard works best with modern browsers that support:

ES6+ JavaScript features

CSS Grid and Flexbox

Fetch API

License
This project is open source and available under the MIT License.

Troubleshooting
Common Issues
Excel file not found: Ensure the Excel file is in the project directory

Module not found errors: Install all required packages from requirements.txt

Chart display issues: Check browser console for JavaScript errors

Getting Help
If you encounter issues:

Check that all dependencies are installed

Verify your Excel file format and column names

Examine the browser console for error messages

Contributing
Contributions to improve the dashboard are welcome. Please ensure:

Code follows PEP8 guidelines

New features include appropriate tests

Documentation is updated accordingly

