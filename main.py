# Before
payload = {
    "request": {
        "image": "base64_string"
    }
}

# After (GPT 정보)
payload = {
    "request": {
        "image": {
            "image": "base64_string",
            "sort": 1
        }
    }
}
