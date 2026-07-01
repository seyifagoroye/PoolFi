import requests

def run():
    TEST_CLIENT = "706df6c4-b8bb-4130-88c4-d21b052f8631"
    TEST_SECRET = "k8UobYk3APgOoxUnNL7VpuxzwTsH4LsXtydfjcHs8RH0YISBB4OMqJsaafG+U8fWETu9YZ96bNXE+DelCDuMPw=="
    
    LIVE_CLIENT = "e5e85b13-f560-4643-814e-c87435dbbc15"
    LIVE_SECRET = "8/doS7Q3w77EANpk3vpgSrc05hhOiRWp3eBs01sXyZ1AmovtZUXlmrxie+xnEF2tR4q79t0IFufMD1d4JrkT8g=="
    
    PARENT = "f666ef9b-888e-4799-85ce-acb505b28023"
    SUB = "5ef7e4cc-6c3c-4eff-a84f-4ff1490bc673"
    
    SANDBOX = "https://sandbox.nomba.com/v1/auth/token/issue"
    LIVE_URL = "https://api.nomba.com/v1/auth/token/issue"

    tests = [
        ("TEST Keys -> Sandbox URL (Parent ID)", SANDBOX, PARENT, TEST_CLIENT, TEST_SECRET),
        ("TEST Keys -> Sandbox URL (Sub ID)", SANDBOX, SUB, TEST_CLIENT, TEST_SECRET),
        ("TEST Keys -> Live URL (Parent ID)", LIVE_URL, PARENT, TEST_CLIENT, TEST_SECRET),
        ("LIVE Keys -> Live URL (Parent ID)", LIVE_URL, PARENT, LIVE_CLIENT, LIVE_SECRET)
    ]
    
    print("\n🚀 Bypassing server to test Nomba directly...\n")
    for name, url, acc, cid, csec in tests:
        print(f"Testing: {name}")
        try:
            resp = requests.post(
                url,
                json={"grant_type": "client_credentials", "client_id": cid, "client_secret": csec},
                headers={"Content-Type": "application/json", "accountId": acc}
            )
            print(f"Status: {resp.status_code} | Output: {resp.text}\n")
        except Exception as e:
            print(f"Error: {e}\n")

run()
