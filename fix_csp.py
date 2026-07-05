import os
import re
import urllib.request
import hashlib
import base64

def get_sri_hash(url):
    try:
        if url.startswith('//'):
            url = 'https:' + url
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read()
            hash_sha384 = hashlib.sha384(content).digest()
            hash_b64 = base64.b64encode(hash_sha384).decode('utf-8')
            return f"sha384-{hash_b64}"
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def process_templates(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Process scripts with external src
                def script_repl(match):
                    full_match = match.group(0)
                    src = match.group(1)
                    if 'integrity=' in full_match:
                        return full_match # Already has SRI
                    
                    if src.startswith('http') or src.startswith('//'):
                        if 'cloudflare' in src or 'jsdelivr' in src or 'unpkg' in src or 'bootstrap' in src or 'jquery' in src:
                            print(f"Adding SRI to script: {src}")
                            sri = get_sri_hash(src)
                            if sri:
                                return full_match.replace('<script ', f'<script integrity="{sri}" crossorigin="anonymous" ')
                    return full_match
                
                content = re.sub(r'<script\s+[^>]*src=[\'"]([^\'"]+)[\'"][^>]*>', script_repl, content)

                # Process stylesheets with external href
                def style_repl(match):
                    full_match = match.group(0)
                    href = match.group(1)
                    if 'integrity=' in full_match:
                        return full_match # Already has SRI
                    
                    if href.startswith('http') or href.startswith('//'):
                        if 'cloudflare' in href or 'jsdelivr' in href or 'unpkg' in href or 'bootstrap' in href:
                            print(f"Adding SRI to style: {href}")
                            sri = get_sri_hash(href)
                            if sri:
                                return full_match.replace('<link ', f'<link integrity="{sri}" crossorigin="anonymous" ')
                    return full_match
                
                content = re.sub(r'<link\s+[^>]*href=[\'"]([^\'"]+)[\'"][^>]*rel=[\'"]stylesheet[\'"][^>]*>', style_repl, content)
                content = re.sub(r'<link\s+[^>]*rel=[\'"]stylesheet[\'"][^>]*href=[\'"]([^\'"]+)[\'"][^>]*>', style_repl, content)

                # Add nonces to inline scripts (scripts without src)
                def inline_script_repl(match):
                    full_match = match.group(0)
                    if 'src=' not in full_match and 'nonce=' not in full_match:
                        return full_match.replace('<script', '<script nonce="{{ g.csp_nonce }}"')
                    return full_match
                
                content = re.sub(r'<script(?![^>]*src=)[^>]*>', inline_script_repl, content)

                # Add nonces to inline styles
                def inline_style_repl(match):
                    full_match = match.group(0)
                    if 'nonce=' not in full_match:
                        return full_match.replace('<style', '<style nonce="{{ g.csp_nonce }}"')
                    return full_match
                
                content = re.sub(r'<style[^>]*>', inline_style_repl, content)

                # Replace 'unsafe-inline' style attribute if we want to be thorough, but user only said inline blocks. 
                # Doing style=" " -> requires heavy refactoring, let's just do script/style blocks.

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

if __name__ == '__main__':
    process_templates('goat_farm_app/templates')
