import requests

base = "http://localhost:8080"
s = requests.Session()

# login
r = s.post(base+"/login", data={"gebruikersnaam":"maartsen","wachtwoord":"maa123","rol":"docent"}, allow_redirects=False)
print("login status:", r.status_code)
print("login location:", r.headers.get("Location"))

# follow redirect
if r.status_code in (301,302):
    r2 = s.get(base+r.headers["Location"])
    print("dashboard status:", r2.status_code)
    print("dashboard url:", r2.url)
    print("contains Live Quiz:", "Live Quiz" in r2.text)
    
    # test live quiz page
    r3 = s.get(base+"/docent/live")
    print("live quiz status:", r3.status_code)
    print("live quiz url:", r3.url)
else:
    print("no redirect")
    print(r.text[:500])