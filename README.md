# Mortgage Calculator

An interactive mortgage calculator built with Streamlit. This application helps users:

- Calculate monthly mortgage payments
- Visualize amortization schedules
- Analyse the impact of overpayments
- Compare different mortgage scenarios

## Features

- Standard mortgage calculation
- Overpayment analysis
- Interactive visualizations
- Downloadable amortization schedules

## Installation

1. Clone this repository
2. Install the dependencies:

```bash
pip install -r requirements.txt
```

## Local Development

To run the app locally:

```bash
streamlit run app.py
```

The application will start and open in your default web browser at http://localhost:8501.

## Deployment on Streamlit Cloud

1. Push this repository to GitHub
2. Log in to [Streamlit Cloud](https://streamlit.io/cloud)
3. Click "New app" and select this repository
4. Choose the main branch and enter `app.py` as the path to the app file
5. Click "Deploy"

## Usage

1. Enter your mortgage parameters in the sidebar
2. View the calculated monthly payment and amortization schedule
3. Switch to the "Overpayment Calculator" tab to analyze the impact of making one-time overpayments
4. Download amortization schedules for your records
