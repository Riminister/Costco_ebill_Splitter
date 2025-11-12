import streamlit as st
import re
import json
from collections import defaultdict
from pathlib import Path

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    st.error("PyPDF2 not available. Please install it with: pip install PyPDF2")

# Default users
DEFAULT_USERS = ["Alex", "Daniel", "Jacob", "Jordan", "Judah", "Adam"]

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    if not PDF_AVAILABLE:
        return ""
    
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

def parse_bill_items(text):
    """Parse bill text to extract items and prices"""
    items = []
    lines = text.split('\n')
    
    # Keywords to exclude (summary/total lines)
    exclude_keywords = [
        'SUBTOTAL', 'TAX', 'TOTAL', 'AMOUNT', 'AMOUN T', 'DEBIT', 'CARD', 'MASTER', 'CASH', 
        'HST', 'INSTANT', 'SAVINGS', '****', 'CHANGE', 'BALANCE', 'VL', 'DEPOSI'
    ]
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Skip lines that are clearly summary/total lines
        if any(keyword in line.upper() for keyword in exclude_keywords):
            continue
            
        # Look for lines with product codes and prices
        # Pattern: product_code item_name price Y/N
        price_match = re.search(r'\$?(\d+\.\d{2})', line)
        if price_match:
            price = float(price_match.group(1))
            
            # Skip zero price items (like free items)
            if price == 0.00:
                continue
            
            # Check if this is a TPD (discount) item
            is_tpd = 'TPD' in line.upper()
            
            if is_tpd:
                # This is a discount - apply it to the previous item
                if items:
                    # Subtract the discount from the last item
                    items[-1]['price'] -= price
                    items[-1]['name'] += f" (discount: -${price:.2f})"
                continue
            
            # Check if item has tax (marked with Y)
            has_tax = 'Y' in line.upper()
            
            # Apply 13% tax if marked with Y
            if has_tax:
                price = price * 1.13
                
            # Extract item name by removing price and common suffixes
            item_name = re.sub(r'\$?\d+\.\d{2}\s*[YN-]?\s*$', '', line).strip()
            
            # Remove product codes (numbers at the start)
            item_name = re.sub(r'^\d+\s+', '', item_name)
            
            # Skip if item name is too short or contains only numbers
            if len(item_name) < 3 or item_name.isdigit():
                continue
                
            # Skip if it looks like a summary line (but allow / in product names)
            if any(char in item_name.upper() for char in ['-', '*']) and not '/' in item_name:
                continue
                
            # Add tax indicator to item name for clarity
            if has_tax:
                item_name += " (includes 13% tax)"
                
            items.append({'name': item_name, 'price': price})
    
    return items

def load_selections():
    """Load saved selections from JSON file"""
    selections_file = Path("selections.json")
    if selections_file.exists():
        try:
            with open(selections_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_selections(selections):
    """Save selections to JSON file"""
    with open("selections.json", 'w') as f:
        json.dump(selections, f, indent=2)

def main():
    st.set_page_config(page_title="Costco Bill Splitter", page_icon="💰", layout="wide")
    
    st.title("💰 Costco Bill Splitter")
    st.markdown("---")
    
    # Initialize session state
    if 'items' not in st.session_state:
        st.session_state.items = []
    if 'selections' not in st.session_state:
        st.session_state.selections = load_selections()
    
    # Sidebar for user selection
    with st.sidebar:
        st.header("👤 Select Your Name")
        selected_user = st.selectbox(
            "Who are you?",
            options=DEFAULT_USERS,
            key="user_selector"
        )
        st.markdown("---")
        st.info(f"**Selected:** {selected_user}")
        
        # Load bill button
        if st.button("🔄 Reload Bill from PDF"):
            pdf_path = "bill.pdf"
            if Path(pdf_path).exists():
                with st.spinner("Reading PDF..."):
                    bill_text = extract_text_from_pdf(pdf_path)
                    if bill_text.strip():
                        items = parse_bill_items(bill_text)
                        st.session_state.items = items
                        st.success(f"Loaded {len(items)} items from PDF!")
                    else:
                        st.error("Could not extract text from PDF.")
            else:
                st.error(f"PDF file '{pdf_path}' not found.")
    
    # Main content area
    if not st.session_state.items:
        st.warning("⚠️ No items loaded. Please click 'Reload Bill from PDF' in the sidebar to load items from bill.pdf")
        
        # Try to load automatically
        pdf_path = "bill.pdf"
        if Path(pdf_path).exists():
            with st.spinner("Loading bill automatically..."):
                bill_text = extract_text_from_pdf(pdf_path)
                if bill_text.strip():
                    items = parse_bill_items(bill_text)
                    st.session_state.items = items
                    st.rerun()
    else:
        # Display items with checkboxes
        st.header("📋 Bill Items - Check what you got")
        st.markdown(f"**Total Items:** {len(st.session_state.items)}")
        
        # Initialize selections for current user if not exists
        if selected_user not in st.session_state.selections:
            st.session_state.selections[selected_user] = []
        
        # Create columns for better layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("Item Name")
        with col2:
            st.subheader("Price")
        
        # Display items with checkboxes
        updated = False
        for idx, item in enumerate(st.session_state.items):
            item_id = f"{item['name']}_{idx}"
            is_checked = item_id in st.session_state.selections[selected_user]
            
            col1, col2, col3 = st.columns([0.1, 2.9, 1])
            
            with col1:
                checked = st.checkbox(
                    "",
                    value=is_checked,
                    key=f"checkbox_{selected_user}_{item_id}",
                    label_visibility="collapsed"
                )
            
            with col2:
                st.write(item['name'])
            
            with col3:
                st.write(f"**${item['price']:.2f}**")
            
            # Update selections if checkbox changed
            if checked != is_checked:
                updated = True
                if checked:
                    if item_id not in st.session_state.selections[selected_user]:
                        st.session_state.selections[selected_user].append(item_id)
                else:
                    if item_id in st.session_state.selections[selected_user]:
                        st.session_state.selections[selected_user].remove(item_id)
        
        # Save selections if updated
        if updated:
            save_selections(st.session_state.selections)
            st.rerun()
        
        st.markdown("---")
        
        # Calculate and display summary
        st.header("💵 Bill Split Summary")
        
        # Calculate totals for each user
        user_items = defaultdict(list)
        item_dict = {f"{item['name']}_{idx}": item for idx, item in enumerate(st.session_state.items)}
        
        for user in DEFAULT_USERS:
            if user in st.session_state.selections:
                for item_id in st.session_state.selections[user]:
                    if item_id in item_dict:
                        user_items[user].append(item_dict[item_id])
        
        # Calculate split prices
        split_summary = {}
        for user in DEFAULT_USERS:
            split_summary[user] = []
            total = 0
            
            for item_id in st.session_state.selections.get(user, []):
                if item_id in item_dict:
                    item = item_dict[item_id]
                    # Count how many users selected this item
                    num_users = sum(1 for u in DEFAULT_USERS 
                                  if u in st.session_state.selections 
                                  and item_id in st.session_state.selections[u])
                    
                    if num_users > 0:
                        split_price = item['price'] / num_users
                        split_summary[user].append({
                            'name': item['name'],
                            'price': split_price,
                            'original_price': item['price'],
                            'shared_with': num_users
                        })
                        total += split_price
            
            split_summary[user].append(('TOTAL', total))
        
        # Display summary in columns
        cols = st.columns(3)
        for idx, user in enumerate(DEFAULT_USERS):
            with cols[idx % 3]:
                with st.expander(f"**{user}**", expanded=False):
                    user_total = 0
                    for entry in split_summary[user]:
                        if isinstance(entry, tuple) and entry[0] == 'TOTAL':
                            user_total = entry[1]
                        else:
                            st.write(f"• {entry['name']}")
                            if entry['shared_with'] > 1:
                                st.caption(f"  ${entry['price']:.2f} (shared with {entry['shared_with']} people)")
                            else:
                                st.caption(f"  ${entry['price']:.2f}")
                    st.markdown(f"### **Total: ${user_total:.2f}**")
        
        # Grand total
        grand_total = sum(entry[1] for user in DEFAULT_USERS 
                          for entry in split_summary[user] 
                          if isinstance(entry, tuple) and entry[0] == 'TOTAL')
        
        st.markdown("---")
        st.markdown(f"### **Grand Total: ${grand_total:.2f}**")
        
        # Show who selected what (for transparency)
        with st.expander("👥 View All Selections"):
            for user in DEFAULT_USERS:
                selected_items = st.session_state.selections.get(user, [])
                if selected_items:
                    st.write(f"**{user}** selected {len(selected_items)} item(s)")
                else:
                    st.write(f"**{user}** has not selected any items yet")

if __name__ == "__main__":
    main()

