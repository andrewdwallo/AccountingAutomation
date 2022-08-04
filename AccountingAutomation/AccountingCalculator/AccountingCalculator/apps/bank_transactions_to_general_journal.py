from lib2to3.pgen2.pgen import DFAState
import selectors
from pyparsing import ungroup
import streamlit as st
import os
import pandas as pd                       #to perform data manipulation and analysis
import numpy as np                        #to cleanse data
from datetime import datetime             #to manipulate dates
import plotly.express as px               #to create interactive charts
import plotly.graph_objects as go         #to create interactive charts
import dash_core_components as dcc        #to get components for interactive user interfaces
import dash_html_components as html       #to compose the dash layout using Python structures
from IPython.core.display import display, HTML

def app():
    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        # Can be used wherever a "file-like" object is accepted:
        df = pd.read_csv(uploaded_file, on_bad_lines='skip')
        df = df.dropna().reset_index(drop=True)
        df.index = np.arange(1, len(df) + 1)                  # index starts at 1
        
        # Assign each transaction as either a debit or credit
        df['Debit or Credit'] = ['Debit' if x>0 else 'Credit' for x in df['Amount']]
        
        # Wrangle the dataframe
        # get rid of certain strings/characters in Description column
        pattern = '|'.join(['\d+', 'Confirmation', 'ID', 'XXXXX', '#'])
        df['Description'] = df['Description'].str.replace(pattern, '')
       
        # Assign a Transaction Type for each Transaction
        df.loc[df['Description'].str.contains('WITHDRWL|Withdrawal|withdrawal|WITHDRAWAL'), 'Transaction Type'] = 'Withdrawal'
        df.loc[df['Description'].str.contains('Bill Payment|bill payment|Bill payment|bill Payment|BILL PAYMENT|scheduled payment'), 'Transaction Type'] = 'Bill Payment'
        df.loc[df['Description'].str.contains('Check|CHECK|check'), 'Transaction Type'] = 'Check'
        df.loc[df['Description'].str.contains('DEPOSIT|deposit|Deposit|DES') & (df['Amount'] > 0), 'Transaction Type'] = 'Deposit'
        df.loc[df['Description'].str.contains('DES') & (df['Amount'] < 0), 'Transaction Type'] = 'ACH'
        df.loc[df['Description'].str.contains('transfer|TRANSFER|Transfer'), 'Transaction Type'] = 'Transfer'
        df.loc[df['Description'].str.contains('Purchase|PURCHASE|purchase'), 'Transaction Type'] = 'Debit Card Purchase'
        df.loc[df['Description'].str.contains('CHECK ORDER|OVERDRAFT'), 'Transaction Type'] = 'Bank Charge'
        # Assign "Other" for Transactions with no type
        df['Transaction Type'] = df['Transaction Type'].fillna('Other')
        
        # rename columns so they are easier to access
        df.rename(columns = {'Date':'date', 
                             'Description':'description', 
                             'Amount':'amount', 
                             'Running Bal.':'running_balance', 
                             'Debit or Credit':'debit_or_credit',
                             'Transaction Type': 'transaction_type'}, inplace = True)
        
        sample_dataframe = pd.DataFrame(data=df)
        
        # let user choose the Account to Debit and the Account to Credit for each unique transaction
        def get_choice(df, column):
            m1 = {}
            m2 = {}
            for v in df[column].unique():
                st.write('Transaction: [{}]'.format(v))
                col1, col2 = st.columns(2)
                # st.write('Transaction: [{}]'.format(v))
                m1[v] = col1.selectbox('Select the Account to Debit for transaction [{}]: '.format(v),
                                       ('Cash',
                                        'Accounts Receivable',
                                        'Land',
                                        'Equipment',
                                        'Salaries Expense',
                                        'Rent Expense', 
                                        'Depreciation Expense', 
                                        'Insurance Expense'))
                
                m2[v] = col2.selectbox('Select the Account to Credit for transaction [{}]: '.format(v),
                                       ('Loans Payable', 
                                        'Accounts Payable', 
                                        'Bonds Payable', 
                                        'Common Stock', 
                                        'Retained Earnings', 
                                        'Sales', 
                                        'Service Fee'))
                
                df['debit'] = df[column].map(m1)
                df['credit'] = df[column].map(m2)
            
            return df
        
        # restore function in df
        df = get_choice(sample_dataframe, 'description')
        
        # create a unique Account Reference for each Transaction
        df['reference'] = df.description.factorize()[0]+1
        df = df
        
        # rearrange dataframe columns for general journal format
        journal_df = df[['date', 'description', 'debit', 'credit', 'reference', 'amount']]
        
        # create two empty rows after every transaction
        empty_rows = 3
        journal_df.index = range(1, empty_rows*len(journal_df), empty_rows)
        journal_df = journal_df.reindex(index=range(empty_rows*len(journal_df)))
        journal_df = journal_df.iloc[1: , :]
        
        # shift values of debit and credit columns
        journal_df['debit'] = journal_df['debit'].shift(1)
        journal_df['credit'] = journal_df['credit'].shift(2)
        
        # fill na values in description column with debit and credit values that were shifted
        journal_df['description'] = journal_df['description'].fillna(journal_df['debit'])
        journal_df['description'] = journal_df['description'].fillna(journal_df['credit'])
        
        # fill debit and credit column with nan values
        journal_df['debit'] = np.NaN
        journal_df['credit'] = np.NaN
        
        # duplicate amount column
        journal_df['amount_duplicated'] = journal_df['amount']
        
        # make all values in amount and amount_duplicated columns positive
        journal_df['amount'] = journal_df['amount'].abs()
        journal_df['amount_duplicated'] = journal_df['amount_duplicated'].abs()
        
        # shift values of amount and amount_duplicated columns
        journal_df['amount'] = journal_df['amount'].shift(1)
        journal_df['amount_duplicated'] = journal_df['amount_duplicated'].shift(2)
        
        # fill na values in debit and credit columns with the amount and amount_duplicated values that were shifted
        journal_df['debit'] = journal_df['debit'].fillna(journal_df['amount'])
        journal_df['credit'] = journal_df['credit'].fillna(journal_df['amount_duplicated'])
        
        # drop amount and amount_duplicated columns from dataframe
        journal_df = journal_df.drop(columns=['amount', 'amount_duplicated'])
        
        # rearrange dataframe again
        journal_df = journal_df[['date', 'description', 'reference', 'debit', 'credit']]
        
        # replace all na values with empty string
        journal_df = journal_df.astype(str)
        journal_df = journal_df.replace({'nan' : ''})
        
        
        # create new column to reformat journal
        journal_df['New1'] = ''
        
        # add two empty rows to help reformat journal
        journal_df = pd.DataFrame(columns=['date', 'description', 'reference', 'debit', 'credit', 'new'], data=journal_df)
        def add_empty_rows(journal_df, n_empty, period):
            journal_df = journal_df.reset_index(drop=True)
            len_new_index = len(journal_df) + n_empty*(len(journal_df) // period)
            new_index = pd.RangeIndex(len_new_index)
            journal_df.index += n_empty * (journal_df.index
                                           .to_series()
                                           .groupby(journal_df.index // period)
                                           .ngroup())
            new_df = journal_df.reindex(new_index)
            return new_df
        journal_df = add_empty_rows(journal_df, 2, 3)
        
        # create another new column to help reformat journal and fill column with NA values
        journal_df['New2'] = ''
        journal_df['New2'] = np.NaN
        
        # fill new column with random string to help reformat journal
        journal_df.loc[1::5, 'new'] = 'hello'
        journal_df.loc[2::5, 'new'] = 'hello'
        
        # fill New2 column with random string to help reformat journal
        journal_df.loc[0::5, 'New2'] = 'hello'
        
        # for any NA values in new column replace with values from respected indices from the description column
        journal_df['new'].fillna(journal_df['description'], inplace=True)
        
        # for any NA values in New2 column replace with values from respected indices from the description column
        journal_df['New2'].fillna(journal_df['description'], inplace=True)
        
        # shift all values in new column down 2 indices
        journal_df['new'] = journal_df['new'].shift(2)
        
        # shift all values in New2 column up 1 indice
        journal_df['New2'] = journal_df['New2'].shift(-1)
        
        # for any NA values in New2 column replace with values from respected indices from the new column
        journal_df['New2'].fillna(journal_df['new'], inplace=True)
        
        # rename New2 column to "account_titles_and_explanations"
        journal_df.rename(columns={'New2':'account_titles_and_explanation'}, inplace=True)
        
        # drop/remove new column from dataframe
        journal_df = journal_df.drop(columns=['new'])
        
        # drop all rows containing at least one NA values
        journal_df = journal_df.dropna()
        
        # rearrange dataframe
        journal_df = journal_df[['date', 'account_titles_and_explanation', 'reference', 'debit', 'credit']]
        
        # shift all values in debit column up 1
        journal_df['debit'] = journal_df['debit'].shift(-1)
        
        # shift all values in credit column up 1
        journal_df['credit'] = journal_df['credit'].shift(-1)
        
        # convert date to datetime
        journal_df['date'] = pd.to_datetime(journal_df.date)
        journal_df['date'] = journal_df['date'].dt.strftime('%m/%d/%Y')
        
        # remove NA values from dataframe
        journal_df = journal_df.astype(str)
        journal_df = journal_df.replace({'nan' : ''})
        
        # add month column based on conditions
        journal_df['month'] = pd.DatetimeIndex(journal_df['date']).month
        
        journal_df['month'] = journal_df['month'].replace({1.0 : 'January', 
                                                           2.0 : 'February', 
                                                           3.0 : 'March', 
                                                           4.0 : 'April', 
                                                           5.0 : 'May', 
                                                           6.0 : 'June', 
                                                           7.0 : 'July', 
                                                           8.0 : 'August', 
                                                           9.0 : 'September', 
                                                           10.0 : 'October', 
                                                           11.0 : 'November', 
                                                           12.0 : 'December'})
        
        journal_df.loc[journal_df['month'].duplicated(), 'month'] = np.NaN
        journal_df = journal_df.replace(np.nan, '', regex=True)
        
        # rearrange dataframe
        journal_df = journal_df[['month', 'date', 'account_titles_and_explanation', 'reference', 'debit', 'credit']]
        
        # add year column based on conditions
        journal_df['year'] = pd.DatetimeIndex(journal_df['date']).year
        journal_df['year'] = journal_df['year'].astype(str).replace('\.0', '', regex=True)
        journal_df = journal_df.replace({'nan' : ''})
        journal_df.loc[journal_df['year'].duplicated(), 'year'] = np.NaN
        journal_df = journal_df.replace(np.nan, '', regex=True)
        
        # rearrange dataframe
        journal_df = journal_df[['year', 'month', 'date', 'account_titles_and_explanation', 'reference', 'debit', 'credit']]
        
        # hide indices by setting new index to the column year
        journal_df = journal_df.set_index('year')
        
        # rename columns
        journal_df = journal_df.rename(columns={'year' : 'Year',
                                                'month' : 'Month',
                                                'date' : 'Date',
                                                'account_titles_and_explanation' : 'Account Titles & Explanation',
                                                'reference' : 'Ref.',
                                                'debit' : 'Debit',
                                                'credit' : 'Credit'})
        
        # rename journal_df to final_journal_df
        final_journal_df = journal_df
        
        st.header("General Journal")
        
        # display dataframe
        st.dataframe(final_journal_df)
        
        # user can download dataframe as csv
        @st.cache
        def convert_df(final_journal_df):
            return final_journal_df.to_csv().encode('utf-8')
        
        csv = convert_df(final_journal_df)
        
        st.download_button(
            label='Download data as CSV',
            data=csv,
            file_name='general_journal.csv',
            mime='text/csv',
        )