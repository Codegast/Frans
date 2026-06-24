import pathlib

c = pathlib.Path('Main.cpp').read_text(encoding='utf-8')

# The actual content is: "<a href=\"/leerling/cijfers\">Mijn Cijfers</a>...
# In Python string after reading, \\ becomes \, so we search for \" which is "
idx = c.find('cijfers')
print(f"Context: {repr(c[idx-5:idx+155])}")

old = '": "<a href=\\"/leerling/cijfers\\">Mijn Cijfers</a><a href=\\"/leerling/schoolgids\\">Schoolgids</a>"'
new = '": "<a href=\\"/leerling/cijfers\\">Mijn Cijfers</a><a href=\\"/leerling/quizzen\\">Quizzen</a><a href=\\"/leerling/schoolgids\\">Schoolgids</a>"'

c = c.replace(old, new)
pathlib.Path('Main.cpp').write_text(c, encoding='utf-8')
print("Fixed!")