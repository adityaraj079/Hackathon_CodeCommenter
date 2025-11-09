import streamlit as st
import json
import time
import requests
import google.generativeai as genai

# --- Configuration and Initialization ---
# MANDATORY: Retrieve the Firebase config and App ID from the environment
app_id = 'default-app-id'
firebaseConfig = {}

try:
    if '__app_id' in globals():
        app_id = __app_id
    if '__firebase_config' in globals():
        firebaseConfig = json.loads(__firebase_config)
except Exception as e:
    # This block is for local development/testing outside the canvas environment
    print(f"Using default configurations. Error loading environment variables: {e}")

# API Key handling: Leave it empty. The Canvas environment will handle the injection.

try:
    API_KEY = st.secrets["API_KEY"]
    API_URL = st.secrets['API_URL']
except KeyError:
    st.error("Gemini API Key not found. Please set it in Streamlit Secrets or .streamlit/secrets.toml")
    st.stop() # Stop the app if the key is missing

genai.configure(api_key=API_KEY)
# --- LLM API Logic ---

def call_gemini_api(code_snippet: str):
    """
    Calls the Gemini API with exponential backoff to request code commenting.
    """
    if not code_snippet.strip():
        st.error("Please enter some code to comment.")
        return None

    system_prompt = (
        "You are an expert software engineer and code documentation specialist. "
        "Your task is to take the provided code snippet and return the exact code snippet "
        "back, but meticulously add high-quality, descriptive, and clean comments (using '#' for Python) "
        "to every major section, function, and complex line. "
        "Do not include any introductory text, concluding text, or markdown language indicators. "
        "Only return the commented code."
    )

    payload = {
        "contents": [{"parts": [{"text": code_snippet}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    headers = {
        'Content-Type': 'application/json'
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Note: The API_KEY is handled by the canvas environment if left blank
            url_with_key = f"{API_URL}?key={API_KEY}"
            
            response = requests.post(url_with_key, headers=headers, json=payload)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            result = response.json()
            
            # Extract text from the response
            text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text')
            
            if text:
                return text
            else:
                # Handle cases where the model returns an empty or unexpected response
                st.error("The model returned an empty response. Please try again.")
                return None

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"API call failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                st.error(f"Failed to connect to the commenting service after {max_retries} attempts.")
                print(f"Final API call failed: {e}")
                return None
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            return None
    return None

# --- Streamlit UI Components ---

def main():
    """
    Main function to run the Streamlit application.
    """
    st.set_page_config(layout="wide", page_title="Gemini Code Commenter")
    
    st.markdown(
        """
        <style>
        .stButton>button {
            background-color: #3b82f6;
            color: white;
            font-weight: bold;
            border-radius: 0.5rem;
            padding: 0.75rem 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
            transition: all 0.2s;
        }
        .stButton>button:hover {
            background-color: #2563eb;
            transform: translateY(-1px);
        }
        .main-title {
            font-size: 2.5rem;
            font-weight: 800;
            color: #1e40af;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )

    st.markdown('<div class="main-title">Expert Code Commenter (Python)</div>', unsafe_allow_html=True)
    st.caption("Powered by the Gemini API. Enter your Python code below and get professional comments instantly.")
    
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1. Input Your Code")
        default_code = (
            "def quick_sort(arr):\n"
            "    if len(arr) <= 1:\n"
            "        return arr\n"
            "    pivot = arr[len(arr) // 2]\n"
            "    left = [x for x in arr if x < pivot]\n"
            "    middle = [x for x in arr if x == pivot]\n"
            "    right = [x for x in arr if x > pivot]\n"
            "    return quick_sort(left) + middle + quick_sort(right)"
        )
        
        input_code = st.text_area(
            "Paste your Python code here:", 
            value=default_code, 
            height=400,
            key="input_code"
        )
        
        st.markdown("---")
        
        if st.button("Generate Comments", use_container_width=True):
            if 'output_code' not in st.session_state:
                st.session_state.output_code = ""

            with st.spinner("Generating expert comments..."):
                commented_code = call_gemini_api(input_code)
                
                if commented_code:
                    st.session_state.output_code = commented_code
                else:
                    st.session_state.output_code = "Error: Could not retrieve commented code."

    with col2:
        st.subheader("2. Commented Output")
        
        # Display the output code, using a session state variable
        # to preserve the output after button click
        output_value = st.session_state.get('output_code', 'Click "Generate Comments" to see the results.')
        
        st.code(output_value, language='python', )

if __name__ == '__main__':
    if 'output_code' not in st.session_state:
        st.session_state.output_code = 'Click "Generate Comments" to see the results.'
    main()
