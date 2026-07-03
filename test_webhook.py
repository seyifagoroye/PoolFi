import hmac
import hashlib
import base64
import requests

secret = "NombaHackathon2026"
url = "http://127.0.0.1:8000/webhooks/payment"

# Fresh IDs to completely bypass the database unique check constraints
payload_string = '{"eventType":"payment_success","requestId":"req-889903","transaction":{"transactionId":"tx-999004","aliasAccountNumber":"2322113709","transactionAmount":50000.0}}'

computed_hmac = hmac.new(
    secret.encode("utf-8"), 
    payload_string.encode("utf-8"), 
    hashlib.sha256
).digest()
signature = base64.b64encode(computed_hmac).decode("utf-8")

headers = {
    "Content-Type": "application/json",
    "x-nomba-signature": signature
}

print("Firing secure webhook ingestion simulation payload...")
response = requests.post(url, data=payload_string, headers=headers)

print("Response Status:", response.status_code)
print("Response Body:", response.json())
