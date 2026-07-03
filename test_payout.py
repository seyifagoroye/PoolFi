import requests
import random
from datetime import datetime

unique_suffix = random.randint(1000, 9999)
coordinator_email = f"coordinator_{unique_suffix}@poolfi.com"
member_email = f"member_{unique_suffix}@poolfi.com"
password = "SecurePassword123"

url_register = "http://127.0.0.1:8000/api/auth/register"
url_login = "http://127.0.0.1:8000/api/auth/login"
url_groups = "http://127.0.0.1:8000/api/groups/"

try:
    # 1. Register Coordinator
    print(f"1. Registering coordinator: {coordinator_email}...")
    reg_coord = requests.post(url_register, json={
        "email": coordinator_email, "password": password, "name": "Seyi Coordinator",
        "role": "coordinator", "phone": f"+234803{random.randint(1000000, 9999999)}",
        "bank_account_number": "1234567890", "bank_code": "011"
    })
    
    # 2. Register a Group Member
    print(f"2. Registering pool member: {member_email}...")
    reg_member = requests.post(url_register, json={
        "email": member_email, "password": password, "name": "Mama Titi Traders",
        "role": "member", "phone": f"+234805{random.randint(1000000, 9999999)}",
        "bank_account_number": "2322113709", "bank_code": "044"
    })
    member_id = reg_member.json().get("id")

    # 3. Log in as Coordinator
    print("3. Authenticating coordinator session...")
    login_res = requests.post(url_login, json={"email": coordinator_email, "password": password})
    token = login_res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 4. Create Group
    print("4. Provisioning active savings pool...")
    group_res = requests.post(url_groups, headers=headers, json={
        "name": "Ajegunle Traders Collective", "contribution_amount": 50000.0,
        "cycle_frequency": "monthly", "start_date": datetime.now().strftime("%Y-%m-%d")
    })
    group_id = group_res.json().get("id")

    # 5. Attach Member to Group and assign to Rotation Slot 1
    print(f"5. Joining member {member_email} to pool slot position 1...")
    join_url = f"http://127.0.0.1:8000/api/groups/{group_id}/members"
    join_payload = {"user_id": member_id, "rotation_position": 1, "position": 1}
    
    # Updated debug line
    join_res = requests.post(join_url, headers=headers, json=join_payload)
    print(f"   Member Join Response: {join_res.status_code} - {join_res.json()}")

    # 6. Trigger Outbound Rotation Payout
    print("6. Executing outbound rotation payout via Nomba Engine...")
    payout_url = f"http://127.0.0.1:8000/api/groups/{group_id}/payouts"
    payout_res = requests.post(payout_url, headers=headers)
    