# Sidekicks AI Offer Assistant PoC

This project is a Proof-of-Concept (PoC) for an AI-assisted offer creation tool, developed for the company Your Sidekicks AG. It utilizes a Retrieval-Augmented Generation (RAG) pipeline, optionally enhanced with external research, to help consultants draft sales offer content.

## Academic and Confidentiality Notice

**This repository contains the source code for the Proof-of-Concept developed as part of a Bachelor Thesis at the FHNW University of Applied Sciences and Arts Northwestern Switzerland, School of Business.**

This is a sanitized, public version of the original private repository. Due to a Non-Disclosure Agreement (NDA) with the client, Your Sidekicks AG, all proprietary and confidential data has been removed. This includes the dataset of historical offers that formed the original knowledge base.

To allow for code review and application testing, this repository includes a single, fabricated example file: `data/offers_knowledge_base/example_offer.json`. This file showcases the required data structure. To run the application, you can duplicate this file or create your own JSON files following the same schema.

## Features

*   Loads offer data from local JSON files for context.
*   Generates vector embeddings for offer position descriptions using Sentence Transformers.
*   Stores and retrieves embeddings using ChromaDB (local persistent vector store).
*   Uses OpenAI's GPT models for chat, structuring, and drafting offer content.
*   Optionally performs external client and market research using Perplexity models via OpenRouter to enrich the context provided to the LLM.
*   Interactive command-line interface to guide the consultant through the offer creation process.
*   Integrates with Bexio to automatically create a formal quote from the generated content.

## Project Structure / File Overview

*   `main.py`: A thin wrapper script that initializes and runs the main application workflow.
*   `offer_workflow.py`: Contains the core application logic, orchestrating the different stages of offer creation.
*   `llm_utils.py`: Handles all direct interactions with OpenAI and OpenRouter LLMs.
*   `vector_store_utils.py`: Manages all ChromaDB operations (loading, vectorizing, retrieving).
*   `research_utils.py`: Implements the external research functionality via the OpenRouter API.
*   `config_data.py`: Stores various configuration variables, including API model names, data directories, and internal pricing information.
*   `prompts_config.py`: Contains all complex prompt templates used for interacting with the LLMs.
*   `requirements.txt`: Lists all Python dependencies.
*   `.env`: (User-created) Stores API keys.
*   `data/offers_knowledge_base/`: Directory containing example/dummy JSON offer files.
*   `vector_store/`: Directory where ChromaDB stores its persistent vector data.

## Prerequisites

*   Python 3.8+ installed.
*   An OpenAI API Key.
*   Optionally, an OpenRouter API Key for external research capabilities.
*   A Bexio API Token for the final integration step.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/omar7l/SidekicksAIOfferAssistant.git
    cd SidekicksAIOfferAssistant
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip3 install -r requirements.txt
    ```

4.  **Set up your `.env` file:**
    *   Create a file named `.env` in the root of the project directory.
    *   Add your API keys and token. You can obtain these from their respective platforms: [OpenAI Platform](https://platform.openai.com/account/api-keys), [OpenRouter AI](https://openrouter.ai/), and your Bexio account settings.
        ```env
        OPENAI_API_KEY="sk-YOUR_OPENAI_API_KEY_HERE"
        OPENROUTER_API_KEY="sk-or-v1-YOUR_OPENROUTER_API_KEY_HERE"
        BEXIO_API_TOKEN="YOUR_BEXIO_API_TOKEN_HERE"
        ```
    *   **Important:** The `.env` file is listed in `.gitignore` and should **never** be committed to version control.

5.  **Prepare your Offer Data (Knowledge Base):**
    *   As noted above, the original confidential dataset has been removed.
    *   The repository includes a single example file: `data/offers_knowledge_base/example_offer.json`.
    *   To test the RAG functionality, you can **duplicate this file multiple times** within the directory, or create your own JSON files that adhere to the same schema. The system will process all `.json` files found in this directory.

6.  **Configure Bexio Integration (Important):**
    *   See the "Bexio Integration" section below for crucial steps to set up API token and other parameters in `config_data.py`.

## Bexio Integration

This application can automatically create a new quote (offer) in your Bexio account.

### Setup for Bexio Integration:

1.  **API Token (Mandatory):**
    *   Ensure your Bexio API Token is added to your `.env` file. Without this token, the Bexio integration step will be skipped.

2.  **Configuration in `config_data.py` (Mandatory Review):**
    *   Open the `config_data.py` file and locate the `--- BEXIO API CONFIGURATION ---` section.
    *   You **must review and update** the placeholder IDs to match your specific Bexio instance. The default values are examples and **will not work** for your setup.
    *   Key fields to update: `BEXIO_USER_ID`, `BEXIO_CONTACT_ID`, `BEXIO_UNIT_ID_HOURS`, `BEXIO_ACCOUNT_ID_SERVICES`, `BEXIO_TAX_ID_STANDARD`.
    *   **Failure to correctly set these IDs will result in errors** when the application tries to create the quote in Bexio.

## Running the PoC

1.  Ensure your virtual environment is active:
    ```bash
    source venv/bin/activate 
    ```

2.  Execute the main script from the project root directory:
    ```bash
    python3 main.py
    ```    *   **First Run:** The script will process the JSON files in `data/offers_knowledge_base/`, generate embeddings, and populate the local ChromaDB vector store. This might take a few moments.
    *   **Interactive Flow:** The application will then guide you through the process, from gathering initial requirements to drafting the final offer.

## How External Research Works

*   If enabled during the interactive flow, the system uses `research_utils.py` to query Perplexity models via the OpenRouter API.
*   Two types of research are performed: Client Research and Offer-Focused Research.
*   The summaries are then provided as additional context to the LLM during the drafting phases.

## Future Considerations / PoC Limitations

*   Error handling can be further improved.
*   Prompt engineering is iterative and can be refined for better outputs.
*   The UI is basic CLI; a web interface could enhance usability.
*   Limited evaluation of generated content quality in this public version due to the absence of the full dataset.