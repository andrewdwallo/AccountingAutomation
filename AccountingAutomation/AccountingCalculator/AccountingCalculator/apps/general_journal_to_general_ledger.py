from lib2to3.pgen2.pgen import DFAState
import streamlit as st
import os
import pandas as pd                       #to perform data manipulation and analysis
import numpy as np                        #to cleanse data
from datetime import datetime             #to manipulate dates
import plotly.express as px               #to create interactive charts
import plotly.graph_objects as go         #to create interactive charts
import dash_core_components as dcc        #to get components for interactive user interfaces
import dash_html_components as html       #to compose the dash layout using Python structures

def app():
    
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        # Can be used wherever a "file-like" object is accepted:
        df = pd.read_csv(uploaded_file)
        
        # rename columns so they are easier to access
        df = df.rename(columns = {'year' : 'year',
                                  'Month' : 'month', 
                                  'Date' : 'date',
                                  'Account Titles & Explanation' : 'account_titles_and_explanation',
                                  'Ref.' : 'ref',
                                  'Debit' : 'debit',
                                  'Credit' : 'credit'})
        
        # convert date to datetime
        df['date'] = pd.to_datetime(df.date)
        df['date'] = df['date'].dt.strftime('%m/%d/%Y')
        
        # convert year to datetime index and reformat
        df['year'] = pd.DatetimeIndex(df['date']).year
        df['year'] = df['year'].astype(str).replace('\.0', '', regex=True)
        
        # replace all NA values with empty string
        df = df.astype(str)
        df = df.replace({'nan' : ''})
        
        # general ledger cash account udataframe
        cash_df = df
        
        # create new columns
        cash_df['Date'] = ''
        cash_df['Transaction Code'] = ''
        cash_df['Description'] = ''
        cash_df['Journal Reference'] = ''
        cash_df['Debit'] = ''
        cash_df['Credit'] = ''
        cash_df['Balance'] = ''
        
        # columns = ['Date', 'Transaction Code', 'Description', 'Journal Reference', 'Debit', 'Credit', 'Balance']
        
        cash_df.loc[df['account_titles_and_explanation'].str.contains('Cash'), 'Description'] = ''
        
        
        
        
        
        st.write(cash_df)
        
        
            
            
            
        
        
        
    