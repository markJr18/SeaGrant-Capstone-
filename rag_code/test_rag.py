import os
import datetime
import google.generativeai as genai
from ret_summ import ScrapedDocument, RetrievalSummarizationNetwork, KEYWORD_LIBRARY

# Configure the Generative AI API with your key
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Ensure your GOOGLE_API_KEY is set in your environment
# If not, this script will raise an EnvironmentError, as expected by ret_summ.py
try:
    _ = os.environ["GOOGLE_API_KEY"]
except KeyError:
    print("Error: GOOGLE_API_KEY environment variable is not set.")
    print("Please set it before running this test script.")
    print("Example: export GOOGLE_API_KEY='YOUR_API_KEY'")
    exit(1)

# --- List available models ---
print("Listing available Gemini models...")
available_models = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
print(f"Models supporting generateContent: {available_models}")
if not available_models:
    print("Error: No Gemini models found that support 'generateContent' with your API key.")
    print("Please check your API key permissions and region, or visit https://makersuite.google.com/ to ensure model access.")
    exit(1)

# --- 1. Define a Sample ScrapedDocument ---
# We'll use a very short piece of text that should hit some keywords
sample_text = """
This document discusses coastal erosion and sea level rise impacts on Charleston, SC.
It also mentions efforts in habitat protection and marsh restoration.
Water quality monitoring is a key concern due to stormwater runoff.
"""

sample_doc = ScrapedDocument(
    url="https://example.com/sample-report",
    municipality="Charleston",
    raw_text=sample_text,
    doc_type="report",
    scraped_at=datetime.datetime.now().isoformat()
)

# --- 2. Instantiate the RetrievalSummarizationNetwork ---
# You can adjust parameters here, e.g., relevance_threshold, use_vector_index
print("Initializing RetrievalSummarizationNetwork...")
network = RetrievalSummarizationNetwork(
    relevance_threshold=0.01,  # Set a low threshold for this test to ensure it processes
    use_vector_index=False,    # For simplicity, we'll start without the vector index
    gemini_model="models/gemini-flash-latest",
)
print("Network initialized.")

# --- 3. Process the Sample Document ---
print("\nProcessing sample document...")
result = network.process(sample_doc)

# --- 4. Print the Results ---
if result:
    print("\n--- Retrieval Result ---")
    print(f"URL: {result.url}")
    print(f"Municipality: {result.municipality}")
    print(f"Document Type: {result.doc_type}")
    print(f"Relevance Score: {result.relevance_score}")
    print(f"Matched Categories: {', '.join(result.matched_categories)}")
    print(f"Matched Keywords: {', '.join(result.matched_keywords)}")
    print(f"Summary: {result.summary}")
    print("Key Findings:")
    for finding in result.key_findings:
        print(f"  - {finding}")
    print(f"Raw Excerpt: {result.raw_excerpt[:200]}...") # Print first 200 chars
    print(f"Metadata: {result.metadata}")
else:
    print("\nNo relevant results found for the sample document (score below threshold or no keywords).")

print("\nTest complete.")

# Optional: You can also print the full keyword library to explore
# print("\n--- Keyword Library ---")
# for category, tiers in KEYWORD_LIBRARY.items():
#     print(f"\nCategory: {category}")
#     for tier_name, keywords in tiers.items():
#         print(f"  {tier_name.capitalize()}: {', '.join(keywords[:5])}...")
