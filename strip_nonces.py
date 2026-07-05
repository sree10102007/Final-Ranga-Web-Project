import os
def strip_nonces(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                content = content.replace(' nonce="{{ csp_nonce() }}"', '')
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

if __name__ == '__main__':
    strip_nonces('goat_farm_app/templates')
