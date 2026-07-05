import os, re
import hashlib

styles_map = {}
events_map = {}

def get_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]

def process_templates(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                
                # Find all style="..."
                for match in re.finditer(r'style="([^"]+)"', content):
                    style_str = match.group(1)
                    styles_map[style_str] = styles_map.get(style_str, 0) + 1
                    
                # Find all on...="..."
                for match in re.finditer(r'\b(on[a-z]+)="([^"]+)"', content):
                    event_type = match.group(1)
                    event_code = match.group(2)
                    events_map[(event_type, event_code)] = events_map.get((event_type, event_code), 0) + 1

    print(f"Unique styles: {len(styles_map)}")
    print(f"Unique events: {len(events_map)}")
    
if __name__ == '__main__':
    process_templates('goat_farm_app/templates')
