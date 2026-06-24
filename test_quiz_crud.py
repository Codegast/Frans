import requests
import sqlite3

base = "http://localhost:8080"
s = requests.Session()

# login als docent
r = s.post(base+"/login", data={"gebruikersnaam":"maartsen","wachtwoord":"maa123","rol":"docent"}, allow_redirects=False)
print("login:", r.status_code)

# maak een nieuwe quiz
r2 = s.post(base+"/docent/quizzen", data={"titel":"Mijn Test Quiz","vak":"wi","klas":"la21"})
print("quiz aanmaken:", r2.status_code)

# controleer in database
conn = sqlite3.connect("schoolportaal.db")
cursor = conn.cursor()
cursor.execute("SELECT id, titel FROM quizzen WHERE titel = ?", ("Mijn Test Quiz",))
row = cursor.fetchone()
print("in database:", row)
conn.close()

if row:
    quiz_id = row[0]
    # verwijder de quiz
    r3 = s.post(base+f"/docent/quiz/verwijder/{quiz_id}")
    print("verwijderen:", r3.status_code)
    
    # controleer of hij weg is
    conn2 = sqlite3.connect("schoolportaal.db")
    c2 = conn2.cursor()
    c2.execute("SELECT COUNT(*) FROM quizzen WHERE id = ?", (quiz_id,))
    count = c2.fetchone()[0]
    conn2.close()
    print("na verwijderen in database:", "verdwenen" if count == 0 else "nog steeds aanwezig")
else:
    print("quiz niet gevonden in database")