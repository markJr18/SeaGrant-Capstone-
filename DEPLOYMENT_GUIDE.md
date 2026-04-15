# Deployment & Setup Guide

This guide provides step-by-step instructions to set up and run the SC-Coasts: Coastal Resilience Document Analyzer on your local machine.

## 1. Prerequisites

Before you begin, you must have the following software installed on your computer:

1.  **Python**: Version 3.9 or higher. You can download it from [python.org](https://www.python.org/downloads/).
2.  **Ollama**: The application for running local Large Language Models. You can download it from [ollama.ai](https://ollama.ai/).

## 2. Installation

### Step 2.1: Clone the Repository

Open a terminal and clone the GitHub repository to your local machine:

```bash
git clone https://github.com/markJr18/SeaGrant-Capstone-.git
cd SeaGrant-Capstone-
```

### Step 2.2: Install Python Dependencies

Install all the necessary Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## 3. Configuration

### Step 3.1: Set Up Ollama

Before you can run the application, you must have your local Ollama server running with the `llama3` model.

1.  **Start the Ollama Application**: Find and launch the Ollama application on your computer. You should see an icon in your menu bar.

2.  **Start the Ollama Server**: Open a terminal window and run the following command. **You must keep this terminal window open** while you are using the application.

    ```bash
    ollama serve
    ```

3.  **Load the LLM Model**: Open a **second, new** terminal window and run the following command to load the `llama3` model into memory. You only need to do this once after starting the server.

    ```bash
    ollama run llama3
    ```

## 4. Running the Application

Once your Ollama server is running and the `llama3` model is loaded, you can start the Streamlit web application.

Navigate to the project directory in your terminal and run:

```bash
streamlit run app.py
```

This will automatically open the application in a new tab in your web browser, ready for you to use.

## 5. How to Use the Application

1.  **Build Your Library**: The first time you run the app, your document library will be empty. Go to the **"Add to Library (Scrape)"** tab, select a municipality (e.g., Hilton Head Island), and click **"Start Scraping & Analysis."**

2.  **Search Your Library**: Once the scrape is complete, navigate to the **"Search Library"** tab. Enter a keyword (e.g., "beach", "permit") and click **"Search Library"** to find matching documents.
