#!/usr/bin/env python3
"""
Capture UI snapshots for visual regression testing.
Saves HTML structure snapshots of key pages to detect unintended changes.
"""
import os
import asyncio
import httpx
from datetime import datetime
from bs4 import BeautifulSoup
import json
import hashlib


class UISnapshotCapture:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.snapshot_dir = "tests/snapshots"
        os.makedirs(self.snapshot_dir, exist_ok=True)
    
    async def capture_page(self, path: str, name: str):
        """Capture HTML structure snapshot of a page"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}{path}")
                if response.status_code != 200:
                    print(f"❌ Failed to capture {name}: HTTP {response.status_code}")
                    return None
                
                # Parse HTML and extract structure
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract key structural elements
                snapshot = {
                    "name": name,
                    "path": path,
                    "timestamp": datetime.now().isoformat(),
                    "structure": self._extract_structure(soup),
                    "forms": self._extract_forms(soup),
                    "htmx_elements": self._extract_htmx_elements(soup),
                    "css_classes": self._extract_css_patterns(soup)
                }
                
                # Save snapshot
                filename = f"{self.snapshot_dir}/{name}.json"
                with open(filename, 'w') as f:
                    json.dump(snapshot, f, indent=2)
                
                print(f"✅ Captured snapshot: {name}")
                return snapshot
                
            except Exception as e:
                print(f"❌ Error capturing {name}: {e}")
                return None
    
    def _extract_structure(self, soup):
        """Extract HTML structure (tags and IDs only)"""
        def extract_element(elem):
            if elem.name is None:
                return None
            
            result = {
                "tag": elem.name,
                "id": elem.get('id'),
                "classes": elem.get('class', [])
            }
            
            # Extract children recursively
            children = []
            for child in elem.children:
                if child.name:  # Skip text nodes
                    child_data = extract_element(child)
                    if child_data:
                        children.append(child_data)
            
            if children:
                result["children"] = children
            
            return result
        
        body = soup.find('body')
        return extract_element(body) if body else None
    
    def _extract_forms(self, soup):
        """Extract form structures"""
        forms = []
        for form in soup.find_all('form'):
            form_data = {
                "action": form.get('action', ''),
                "method": form.get('method', 'get').upper(),
                "hx_post": form.get('hx-post'),
                "hx_target": form.get('hx-target'),
                "inputs": []
            }
            
            # Extract input fields
            for input_elem in form.find_all(['input', 'textarea', 'select']):
                form_data["inputs"].append({
                    "type": input_elem.get('type', 'text'),
                    "name": input_elem.get('name'),
                    "id": input_elem.get('id'),
                    "required": input_elem.get('required') is not None
                })
            
            forms.append(form_data)
        
        return forms
    
    def _extract_htmx_elements(self, soup):
        """Extract HTMX-enabled elements"""
        htmx_elements = []
        
        # Find all elements with HTMX attributes
        htmx_attrs = ['hx-get', 'hx-post', 'hx-put', 'hx-delete', 'hx-target', 'hx-swap']
        
        for attr in htmx_attrs:
            for elem in soup.find_all(attrs={attr: True}):
                htmx_elements.append({
                    "tag": elem.name,
                    "id": elem.get('id'),
                    "htmx_attrs": {
                        attr: elem.get(attr) 
                        for attr in htmx_attrs 
                        if elem.get(attr)
                    }
                })
        
        return htmx_elements
    
    def _extract_css_patterns(self, soup):
        """Extract CSS class patterns"""
        patterns = {
            "flex_patterns": [],
            "color_classes": [],
            "spacing_classes": [],
            "problematic_patterns": []
        }
        
        for elem in soup.find_all(class_=True):
            classes = ' '.join(elem.get('class', []))
            
            # Check for flex patterns
            if 'flex' in classes:
                if 'flex-col' in classes and 'md:flex-row' in classes:
                    patterns["problematic_patterns"].append({
                        "pattern": "flex-col md:flex-row",
                        "element": elem.name,
                        "id": elem.get('id')
                    })
                patterns["flex_patterns"].append(classes)
            
            # Extract color classes
            import re
            colors = re.findall(r'(?:bg|text|border)-(\w+)-\d+', classes)
            patterns["color_classes"].extend(colors)
            
            # Extract spacing classes
            spacing = re.findall(r'[pm][xy]?-\d+', classes)
            patterns["spacing_classes"].extend(spacing)
        
        # Deduplicate
        patterns["flex_patterns"] = list(set(patterns["flex_patterns"]))[:10]
        patterns["color_classes"] = list(set(patterns["color_classes"]))
        patterns["spacing_classes"] = list(set(patterns["spacing_classes"]))
        
        return patterns
    
    async def capture_all_snapshots(self):
        """Capture snapshots of all key pages"""
        pages = [
            ("/", "homepage"),
            ("/login", "login"),
            ("/register", "register"),
            # Add authenticated pages if needed
        ]
        
        print("📸 Capturing UI snapshots...")
        
        for path, name in pages:
            await self.capture_page(path, name)
        
        print("\n✅ Snapshot capture complete!")
        print(f"Snapshots saved to: {self.snapshot_dir}/")


async def main():
    # Check if web service is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/health")
            if response.status_code != 200:
                print("❌ Web service not responding on localhost:8080")
                print("Start it with: docker compose up web-service")
                return
    except:
        print("❌ Cannot connect to web service on localhost:8080")
        print("Start it with: docker compose up web-service")
        return
    
    capturer = UISnapshotCapture()
    await capturer.capture_all_snapshots()


if __name__ == "__main__":
    asyncio.run(main())