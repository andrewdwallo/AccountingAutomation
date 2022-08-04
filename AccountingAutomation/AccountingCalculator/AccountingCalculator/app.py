import streamlit as st
from multiapp import MultiApp
from apps import bank_transactions_to_general_journal, general_journal_to_general_ledger

app = MultiApp()

st.title("Accounting Automater")

# Add all your application here
app.add_app("Bank Transaction to General Journal", bank_transactions_to_general_journal.app)
app.add_app("General Journal to General Ledger", general_journal_to_general_ledger.app)
# The main app
app.run()
