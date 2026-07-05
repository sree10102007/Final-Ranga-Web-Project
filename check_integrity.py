import os, re
missing = []
for root, _, files in os.walk('goat_farm_app/templates'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            for match in re.finditer(r'<script\s+[^>]*src=[\'"]([^\'"]+)[\'"][^>]*>', content):
                src = match.group(1)
                if (src.startswith('http') or src.startswith('//')) and 'integrity=' not in match.group(0):
                    missing.append((file, 'script', src))
            for match in re.finditer(r'<link\s+[^>]*href=[\'"]([^\'"]+)[\'"][^>]*>', content):
                href = match.group(1)
                if (href.startswith('http') or href.startswith('//')) and 'integrity=' not in match.group(0):
                    # We exclude google fonts because fonts.googleapis.com is allowed without SRI usually and doesn't support it well.
                    if 'fonts.googleapis.com' not in href:
                        missing.append((file, 'link', href))
print('Missing:', missing)
