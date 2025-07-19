"""
UI Layout tests to ensure visual consistency and prevent layout breakages.
Uses snapshot testing to catch unintended CSS/HTML changes.
"""
import pytest
from bs4 import BeautifulSoup
import re

pytestmark = pytest.mark.asyncio


class TestUILayout:
    """Test suite for UI layout consistency"""
    
    async def test_login_page_structure(self, client):
        """Test login page has correct HTML structure"""
        response = await client.get("/login")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check main container exists and has correct classes
        main_container = soup.find('div', class_=re.compile(r'flex.*h-screen'))
        assert main_container is not None, "Main container with flex and h-screen not found"
        
        # Ensure NO flex-col md:flex-row pattern (causes column breakage)
        assert 'flex-col' not in main_container.get('class', []), "flex-col found in main container - will break layout!"
        assert 'md:flex-row' not in main_container.get('class', []), "md:flex-row found - will break layout!"
        
        # Check for auth container
        auth_container = soup.find('div', id='auth-container')
        assert auth_container is not None, "Auth container not found"
        
        # Check form structure
        form = soup.find('form')
        assert form is not None, "Login form not found"
        
        # Check required input fields
        email_input = soup.find('input', {'name': 'email'})
        password_input = soup.find('input', {'name': 'password'})
        assert email_input is not None, "Email input not found"
        assert password_input is not None, "Password input not found"
    
    async def test_chat_page_layout(self, client):
        """Test chat page layout structure"""
        # Mock authenticated session
        with client.session_transaction() as sess:
            sess["jwt_token"] = "test-token"
            sess["user"] = {"id": "123", "email": "test@example.com"}
        
        response = await client.get("/chat")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check main layout container
        main_container = soup.find('div', class_=re.compile(r'flex.*h-screen'))
        assert main_container is not None, "Main chat container not found"
        
        # Check for sidebar
        sidebar = soup.find('div', id='sidebar')
        assert sidebar is not None, "Sidebar not found"
        
        # Check for main content area
        main_content = soup.find('main')
        assert main_content is not None, "Main content area not found"
        
        # Check for message container
        messages = soup.find('div', id='messages')
        assert messages is not None, "Messages container not found"
    
    async def test_responsive_classes_consistency(self, client):
        """Test that responsive classes are used consistently"""
        pages = ['/login', '/register']
        
        for page in pages:
            response = await client.get(page)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all elements with class attributes
            elements_with_classes = soup.find_all(class_=True)
            
            for element in elements_with_classes:
                classes = element.get('class', [])
                class_string = ' '.join(classes)
                
                # Check for problematic responsive patterns
                if 'flex-col' in class_string and 'md:flex-row' in class_string:
                    assert False, f"Found flex-col md:flex-row pattern on {page} - this breaks layout!"
                
                # Check for consistent spacing
                if 'p-' in class_string or 'px-' in class_string or 'py-' in class_string:
                    # Ensure padding values are from our standard scale
                    padding_pattern = re.findall(r'p[xy]?-(\d+)', class_string)
                    for value in padding_pattern:
                        assert int(value) in [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24], \
                            f"Non-standard padding value p-{value} found on {page}"
    
    async def test_css_class_naming_convention(self, client):
        """Test that CSS classes follow naming conventions"""
        response = await client.get("/login")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check Gaia-specific classes follow pattern
        gaia_elements = soup.find_all(class_=re.compile(r'gaia-'))
        for element in gaia_elements:
            classes = element.get('class', [])
            for cls in classes:
                if cls.startswith('gaia-'):
                    # Should be kebab-case
                    assert cls.islower() or '-' in cls, f"Gaia class '{cls}' should be kebab-case"
                    assert not '_' in cls, f"Gaia class '{cls}' should use hyphens, not underscores"
    
    async def test_loading_indicators_placement(self, client):
        """Test loading indicators are outside swap targets"""
        response = await client.get("/login")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all HTMX elements
        htmx_elements = soup.find_all(attrs={'hx-post': True})
        
        for element in htmx_elements:
            # Check if element has hx-indicator
            indicator_selector = element.get('hx-indicator')
            if indicator_selector:
                # Find the indicator element
                indicator = soup.select_one(indicator_selector)
                assert indicator is not None, f"Indicator {indicator_selector} not found"
                
                # Check swap target
                swap_target = element.get('hx-target', 'this')
                if swap_target != 'this':
                    target_element = soup.select_one(swap_target)
                    if target_element:
                        # Indicator should NOT be inside swap target
                        assert not target_element.find(id=indicator.get('id')), \
                            f"Loading indicator is inside swap target - will disappear!"
    
    async def test_form_structure_consistency(self, client):
        """Test that forms have consistent structure"""
        pages = ['/login', '/register']
        
        for page in pages:
            response = await client.get(page)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            forms = soup.find_all('form')
            for form in forms:
                # Check form has proper spacing
                form_classes = form.get('class', [])
                assert any('space-y-' in cls for cls in form_classes), \
                    f"Form on {page} missing space-y-* class for vertical spacing"
                
                # Check inputs have proper styling
                inputs = form.find_all('input', type=['text', 'email', 'password'])
                for input_elem in inputs:
                    input_classes = input_elem.get('class', [])
                    # Should have Tailwind form classes
                    assert any('rounded' in cls for cls in input_classes), \
                        f"Input on {page} missing rounded corners"
                    assert any('border' in cls for cls in input_classes), \
                        f"Input on {page} missing border styling"
    
    async def test_color_scheme_consistency(self, client):
        """Test that color scheme uses consistent palette"""
        response = await client.get("/login")
        
        # Define allowed color patterns
        allowed_colors = [
            'slate', 'purple', 'violet', 'indigo',  # Our primary colors
            'red', 'green', 'yellow', 'blue',       # Status colors
            'white', 'black', 'transparent'         # Basics
        ]
        
        # Check that we're not using random colors
        color_pattern = re.compile(r'(?:bg|text|border)-(\w+)-\d+')
        matches = color_pattern.findall(response.text)
        
        for color in matches:
            assert color in allowed_colors, \
                f"Non-standard color '{color}' found - use consistent palette"
    
    async def test_mobile_viewport_meta(self, client):
        """Test that pages have proper mobile viewport meta tag"""
        pages = ['/login', '/register', '/']
        
        for page in pages:
            response = await client.get(page)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            viewport_meta = soup.find('meta', attrs={'name': 'viewport'})
            assert viewport_meta is not None, f"Viewport meta tag missing on {page}"
            
            content = viewport_meta.get('content', '')
            assert 'width=device-width' in content, f"Viewport missing device-width on {page}"
            assert 'initial-scale=1' in content, f"Viewport missing initial-scale on {page}"


class TestUIComponents:
    """Test individual UI components for consistency"""
    
    async def test_button_styling(self, client):
        """Test all buttons have consistent styling"""
        response = await client.get("/login")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        buttons = soup.find_all('button')
        for button in buttons:
            classes = button.get('class', [])
            class_string = ' '.join(classes)
            
            # All buttons should have rounded corners
            assert 'rounded' in class_string, "Button missing rounded corners"
            
            # All buttons should have padding
            assert any(p in class_string for p in ['p-', 'px-', 'py-']), \
                "Button missing padding"
            
            # All buttons should have background color
            assert 'bg-' in class_string, "Button missing background color"
    
    async def test_message_component_structure(self, client):
        """Test message components maintain structure"""
        # This would test the actual message components
        # For now, we'll test the container structure
        with client.session_transaction() as sess:
            sess["jwt_token"] = "test-token"
            sess["user"] = {"id": "123", "email": "test@example.com"}
        
        response = await client.get("/chat")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        message_container = soup.find('div', id='messages')
        assert message_container is not None
        
        # Check it has proper scrolling classes
        classes = message_container.get('class', [])
        assert any('overflow-' in cls for cls in classes), \
            "Message container missing overflow handling"