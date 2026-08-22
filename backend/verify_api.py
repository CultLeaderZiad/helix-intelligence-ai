import urllib.request
import urllib.error
import json
import uuid

def test_api():
    email = f"test_{uuid.uuid4().hex[:8]}@helix.io"
    password = "SecurePassword123!"
    
    print(f"Testing sign-up with email: {email}")
    req = urllib.request.Request(
        "http://localhost:8000/api/auth/sign-up",
        data=json.dumps({"email": email, "password": password, "name": "API Tester"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print("Signup response status:", resp.status)
            print("Signup response body:", data)
            token = data.get("access_token")
            assert token, "Token missing in signup response"
    except urllib.error.HTTPError as e:
        print(f"Signup failed: {e.code} - {e.read().decode()}")
        return

    print("\nTesting sign-in...")
    req_in = urllib.request.Request(
        "http://localhost:8000/api/auth/sign-in",
        data=json.dumps({"email": email, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_in) as resp:
            data_in = json.loads(resp.read().decode())
            print("Signin response status:", resp.status)
            print("Signin response body:", data_in)
            token_in = data_in.get("access_token")
            assert token_in, "Token missing in signin response"
    except urllib.error.HTTPError as e:
        print(f"Signin failed: {e.code} - {e.read().decode()}")
        return

    print("\nTesting session resolution with Bearer token...")
    req_sess = urllib.request.Request(
        "http://localhost:8000/api/auth/session",
        headers={"Authorization": f"Bearer {token_in}"},
        method="GET"
    )
    try:
        with urllib.request.urlopen(req_sess) as resp:
            data_sess = json.loads(resp.read().decode())
            print("Session status:", resp.status)
            print("Session body:", data_sess)
    except urllib.error.HTTPError as e:
        print(f"Session failed: {e.code} - {e.read().decode()}")
        return

    print("\nTesting authenticated Discovery Trigger Search...")
    req_search = urllib.request.Request(
        "http://localhost:8000/api/discovery/jobs",
        data=json.dumps({"query": "Nike running shoes"}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token_in}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_search) as resp:
            data_search = json.loads(resp.read().decode())
            print("Search status:", resp.status)
            print("Search body:", data_search)
    except urllib.error.HTTPError as e:
        print(f"Search failed: {e.code} - {e.read().decode()}")
        return

    print("\nALL AUTH & REAL DB DISCOVERY TESTS PASSED!")

if __name__ == "__main__":
    test_api()
