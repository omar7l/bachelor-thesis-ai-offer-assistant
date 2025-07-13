import json
import requests
from bexio_utils import transform_to_bexio_format, create_bexio_quote
from config_data import BEXIO_API_TOKEN

BEXIO_API_URL = "https://api.bexio.com/2.0/kb_offer"

# Example: Replace this with your actual AI-generated offer JSON for testing
sample_ai_generated_json_output = {
    "project_title": "Test Project for Bexio API",
    "positions": [
        {
            "position_id": 1,
            "type": "Offer Position",
            "position_title": "Development",
            "description": "<strong>Development Phase</strong><br /><ul><li>Implement core features</li><li>Write tests</li><li>Review code</li></ul>",
            "estimated_hours_input": 10,
            "hourly_rate_chf": 100,
            "service_area_used": "Development",
            "calculated_price_chf": 1000
        },
        {
            "position_id": 2,
            "type": "Offer Position",
            "position_title": "Consulting",
            "description": "<strong>Consulting Services</strong><br />Initial workshop<br /><ul><li>Requirements gathering</li><li>Stakeholder interviews</li><li>Documentation</li></ul>",
            "estimated_hours_input": 5,
            "hourly_rate_chf": 150,
            "service_area_used": "Consulting",
            "calculated_price_chf": 750
        },
        {
            "position_id": 3,
            "type": "Offer Position",
            "position_title": "Deployment",
            "description": "<strong>Deployment</strong><br /><ul><li>Prepare production environment</li><li>Deploy application</li><li>Post-deployment support</li></ul>",
            "estimated_hours_input": 3,
            "hourly_rate_chf": 120,
            "service_area_used": "Deployment",
            "calculated_price_chf": 360
        },
        {
            "position_id": 4,
            "type": "Text Position",
            "position_title": "Introduction",
            "description": "<strong>Welcome!</strong><br />This is an introductory text section.<br /><ul><li>Point A</li><li>Point B</li></ul>"
        }
    ]
}

def get_headers():
    return {
        'Accept': "application/json",
        'Content-Type': "application/json",
        'Authorization': f"Bearer {BEXIO_API_TOKEN}",
    }

def fetch_offer_by_id(quote_id):
    url = f"{BEXIO_API_URL}/{quote_id}"
    response = requests.get(url, headers=get_headers())
    print(f"\n--- Offer with ID {quote_id} ---")
    print(response.text)
    return response

def fetch_active_sales_taxes():
    url = "https://api.bexio.com/3.0/taxes?types=sales_tax&scope=active"
    response = requests.get(url, headers=get_headers())
    print("\n--- Active Sales Taxes (for use as tax_id) ---")
    print(response.text)
    return response

def fetch_last_offers(limit=20):
    url = f"{BEXIO_API_URL}?limit={limit}&order_by=created_at&order_direction=desc"
    response = requests.get(url, headers=get_headers())
    print(f"\n--- Last {limit} Offers ---")
    print(response.text)
    return response

def main():
    print("\n--- Bexio API Test Menu ---")
    print("1. Create a new offer (test)")
    print("2. Fetch a specific offer by ID")
    print("3. Fetch the last 20 offers")
    print("4. Fetch active sales taxes (valid tax_id values)")
    choice = input("Choose an option [1/2/3/4]: ").strip()

    if choice == "1":
        print("\nSample AI-generated JSON:")
        print(json.dumps(sample_ai_generated_json_output, indent=2, ensure_ascii=False))
        bexio_payload = transform_to_bexio_format(sample_ai_generated_json_output)
        print("\nTransformed Bexio Payload:")
        print(json.dumps(bexio_payload, indent=2, ensure_ascii=False))
        if bexio_payload and "error" not in bexio_payload:
            print("\nAttempting to create quote in Bexio...")
            bexio_response = create_bexio_quote(bexio_payload)
            print("\nBexio API Response:")
            print(json.dumps(bexio_response, indent=2, ensure_ascii=False))
        else:
            print("\nError in payload transformation:")
            print(bexio_payload)
    elif choice == "2":
        quote_id = input("Enter the offer (quote) ID to fetch: ").strip()
        fetch_offer_by_id(quote_id)
    elif choice == "3":
        fetch_last_offers()
    elif choice == "4":
        fetch_active_sales_taxes()
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()