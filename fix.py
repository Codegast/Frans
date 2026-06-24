with open('Main.cpp', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the broken literal \n line
content = content.replace('std::string postWaarde(const std::string& b, const std::string& v);\\n\\n// ==================== HTTP ====================', '// ==================== HTTP ====================')

# Add forward declarations before the first quiz function
marker = 'std::string docQuizzen(const Sessie& s) {'
forward_decls = 'std::string postWaarde(const std::string& b, const std::string& v);\nstd::string haalCookie(const std::string& r, const std::string& n);\n\n'
content = content.replace(marker, forward_decls + marker, 1)

with open('Main.cpp', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed forward declarations!")