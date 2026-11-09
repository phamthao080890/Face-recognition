

import requests
import base64

def call_search_api(image_path):
    # Read and encode image to base64
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()
        base64_string = base64.b64encode(image_data).decode('utf-8')
    
    # API endpoint and headers
    url = 'http://13.212.33.57:8001/users'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Request payload
    payload = {
        "name": "Akira Phan 2",
        "email": "user@example.com",
        "images": [
            base64_string
        ]
    }
    # print(base64_string)
    # Make POST request
    response = requests.post(url, headers=headers, json=payload)
    
    return response.json()

# Example usage
path = "akira-phan-12-2249.jpg"

result = call_search_api(path)
print(result)
