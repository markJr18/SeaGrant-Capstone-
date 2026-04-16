FROM python:3

RUN git clone -b mark-setup https://github.com/markJr18/SeaGrant-Capstone- /usr/src/seagrant
WORKDIR /usr/src/seagrant
RUN pip install --no-cache-dir langchain-core langchain-community langchain-text-splitters langchain-google-genai bs4 pdfplumber streamlit

CMD ["streamlit", "run", "./app.py"]

