with open('Main.cpp', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the ternary on line 379 - wrap in std::string to avoid type mismatch
old = '(ok?"<p style=\\"color:#69f0ae\\">Goed!</p>":"<p style=\\"color:#ff5252\\">Fout. Het was: "+char(\'A\'+q.vragen[i].antwoord)+". "+q.vragen[i].opties[q.vragen[i].antwoord]+"</p>")'
new = '(!ok?std::string("<p style=\\"color:#ff5252\\">Fout. Het was: ")+char(\'A\'+q.vragen[i].antwoord)+". "+q.vragen[i].opties[q.vragen[i].antwoord]+"</p>":std::string("<p style=\\"color:#69f0ae\\">Goed!</p>"))'

if old in content:
    content = content.replace(old, new)
    with open('Main.cpp', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed ternary on line 379!")
else:
    print("Could not find pattern. Searching for 'Goed'...")
    idx = content.find('Goed')
    if idx >= 0:
        print(repr(content[idx-20:idx+250]))