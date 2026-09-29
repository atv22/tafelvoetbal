with open('styles.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('.stTabs [data-baseweb="tab-list"]', '.stTabs [data-baseweb="tab-list"], .stTabs [role="tablist"]')
content = content.replace('.stTabs [data-baseweb="tab"]', '.stTabs [data-baseweb="tab"], .stTabs [role="tab"]')
content = content.replace('.stTabs [data-baseweb="tab-panel"]', '.stTabs [data-baseweb="tab-panel"], .stTabs [role="tabpanel"]')

with open('styles.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
