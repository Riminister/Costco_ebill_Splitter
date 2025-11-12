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
    if 'items' not in st.session_state or not isinstance(st.session_state.items, list):
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
        
        # Load bill section
        st.header("📄 Load Bill")
        
        # Upload PDF
        uploaded_file = st.file_uploader("Upload Costco Bill PDF", type=['pdf'], key="pdf_uploader")
        
        # Store uploaded file in session state
        if uploaded_file is not None:
            # Save file to session state
            if 'uploaded_pdf_data' not in st.session_state or st.session_state.get('uploaded_pdf_name') != uploaded_file.name:
                st.session_state.uploaded_pdf_data = uploaded_file.getbuffer()
                st.session_state.uploaded_pdf_name = uploaded_file.name
                st.session_state.pdf_processed = False
                st.session_state.button_clicked = False
            
            st.info(f"📄 **File ready:** {uploaded_file.name}")
        
        # Button to process the uploaded PDF (always show if file is uploaded or in session state)
        has_pdf_data = uploaded_file is not None or 'uploaded_pdf_data' in st.session_state
        
        if has_pdf_data:
            st.markdown("---")
            process_button = st.button("🚀 Process PDF and Extract Items", type="primary", use_container_width=True, key="process_pdf_button")
            
            # Use session state to track button clicks more reliably
            if process_button:
                st.session_state.button_clicked = True
                st.session_state.should_process_pdf = True
            
            # Process PDF if button was clicked
            if st.session_state.get('should_process_pdf', False) and 'uploaded_pdf_data' in st.session_state:
                # Don't reset flag yet - we'll do it after processing
                
                st.write("🔄 **Button clicked! Processing PDF...**")
                
                # Check if we have PDF data
                if 'uploaded_pdf_data' not in st.session_state:
                    st.error("❌ No PDF data found in session state. Please upload the file again.")
                else:
                    with st.spinner("Reading PDF and extracting items..."):
                        try:
                            # Save uploaded file temporarily
                            temp_path = Path("temp_bill.pdf")
                            st.write(f"📝 Saving PDF to temporary file: {temp_path}")
                            
                            with open(temp_path, "wb") as f:
                                f.write(st.session_state.uploaded_pdf_data)
                            
                            st.write(f"✅ PDF saved. File size: {temp_path.stat().st_size} bytes")
                            
                            # Extract text
                            st.write("📖 Extracting text from PDF...")
                            bill_text = extract_text_from_pdf(str(temp_path))
                            
                            st.write(f"📊 Extracted text length: {len(bill_text) if bill_text else 0} characters")
                            
                            if bill_text and bill_text.strip():
                                # Always show debug info
                                st.success("✅ Text extracted successfully!")
                                
                                with st.expander("🔍 Debug: View extracted text (first 1000 chars)", expanded=False):
                                    st.text(f"Extracted text length: {len(bill_text)} characters")
                                    st.code(bill_text[:1000])
                                
                                # Parse items
                                st.write("🔍 Parsing items from text...")
                                items = parse_bill_items(bill_text)
                                
                                st.write(f"📦 Found {len(items) if items else 0} items after parsing")
                                
                                if items and len(items) > 0:
                                    # Store items in session state
                                    st.session_state.items = items
                                    st.session_state.pdf_processed = True
                                    
                                    st.success(f"✅ Successfully loaded {len(items)} items from PDF!")
                                    st.balloons()  # Celebration!
                                    
                                    # Show first few items as preview
                                    with st.expander("👀 Preview first 5 items", expanded=True):
                                        for i, item in enumerate(items[:5], 1):
                                            st.write(f"{i}. {item['name']} - ${item['price']:.2f}")
                                    
                                    # Clean up temp file
                                    if temp_path.exists():
                                        temp_path.unlink()
                                    
                                    # Reset the processing flag
                                    st.session_state.should_process_pdf = False
                                    
                                    # Automatically rerun to show items - they're already in session_state
                                    st.success(f"✅ **Successfully loaded {len(items)} items!** Showing them now...")
                                    st.rerun()
                                else:
                                    # Reset flag even on failure
                                    st.session_state.should_process_pdf = False
                                    
                                    st.warning(f"⚠️ Parsed {len(items) if items else 0} items from PDF.")
                                    st.error("❌ No items found in PDF. The PDF format might not match expected format.")
                                    
                                    # Show detailed parsing debug info
                                    st.markdown("### 🔍 Parsing Debug Information")
                                    
                                    # Show all lines with prices
                                    lines = bill_text.split('\n')
                                    lines_with_prices = []
                                    for line in lines:
                                        line = line.strip()
                                        if line and re.search(r'\d+\.\d{2}', line):
                                            lines_with_prices.append(line)
                                    
                                    st.write(f"**Found {len(lines_with_prices)} lines with prices:**")
                                    with st.expander("View all lines with prices", expanded=True):
                                        for i, line in enumerate(lines_with_prices[:20], 1):
                                            st.code(f"{i}. {line}")
                                    
                                    # Show why lines were rejected
                                    st.write("**Testing why items weren't parsed:**")
                                    test_lines = lines_with_prices[:5]
                                    for test_line in test_lines:
                                        st.write(f"**Line:** `{test_line}`")
                                        
                                        # Test each filter
                                        price_match = re.search(r'\$?(\d+\.\d{2})', test_line)
                                        if price_match:
                                            price = float(price_match.group(1))
                                            st.write(f"  - Price found: ${price:.2f}")
                                            
                                            if price == 0.00:
                                                st.write(f"  - ❌ Rejected: Zero price")
                                                continue
                                            
                                            # Extract item name
                                            item_name = re.sub(r'\$?\d+\.\d{2}\s*[YN-]?\s*$', '', test_line).strip()
                                            item_name = re.sub(r'^\d+\s+', '', item_name)
                                            
                                            st.write(f"  - Item name after cleaning: `{item_name}`")
                                            
                                            if len(item_name) < 3:
                                                st.write(f"  - ❌ Rejected: Name too short ({len(item_name)} chars)")
                                            elif item_name.isdigit():
                                                st.write(f"  - ❌ Rejected: Name is only digits")
                                            elif any(char in item_name.upper() for char in ['-', '*']) and not '/' in item_name:
                                                st.write(f"  - ❌ Rejected: Looks like summary line")
                                            else:
                                                st.write(f"  - ✅ Would be accepted as item!")
                                        
                                        st.markdown("---")
                                    
                                    st.info("💡 **Tip:** Make sure the PDF contains text (not just images). The parsing looks for lines with prices in format like 'ITEM NAME 12.99 Y'")
                            else:
                                st.session_state.should_process_pdf = False
                                st.error("❌ Could not extract text from PDF. The PDF might be image-based or corrupted.")
                                st.info("💡 **Tip:** If your PDF is image-based, you may need OCR software to convert it to text first.")
                            
                            # Clean up temp file
                            if temp_path.exists():
                                temp_path.unlink()
                        except Exception as e:
                            st.session_state.should_process_pdf = False
                            st.error(f"❌ Error processing PDF: {str(e)}")
                            import traceback
                            with st.expander("🔍 View error details", expanded=True):
                                st.code(traceback.format_exc())
        else:
            # Clear PDF data if no file is uploaded
            if 'uploaded_pdf_data' in st.session_state:
                del st.session_state.uploaded_pdf_data
            if 'uploaded_pdf_name' in st.session_state:
                del st.session_state.uploaded_pdf_name
            st.session_state.pdf_processed = False
        
        st.markdown("---")
        
        # Clear selections button
        if st.button("🗑️ Clear My Selections", type="secondary"):
            if selected_user in st.session_state.selections:
                st.session_state.selections[selected_user] = []
                save_selections(st.session_state.selections)
                st.success("Your selections have been cleared!")
                st.rerun()
        
        # Clear all selections button
        if st.button("⚠️ Clear All Selections", type="secondary"):
            st.session_state.selections = {}
            save_selections({})
            st.success("All selections have been cleared!")
            st.rerun()
    
    # Main content area
    # Check if items list is empty (not just falsy, but actually empty list)
    items_list = st.session_state.items if isinstance(st.session_state.items, list) else []
    
    # Debug: Show what's in session state
    if st.session_state.get('pdf_processed', False):
        st.sidebar.write(f"🔍 Debug: {len(items_list)} items in session state")
    
    if not items_list or len(items_list) == 0:
        st.warning("⚠️ No items loaded. Please upload a PDF and click 'Process PDF and Extract Items' in the sidebar.")
        
        # Show instructions
        st.info("""
        **How to load a bill:**
        1. **Upload PDF:** Use the file uploader in the sidebar to upload your Costco bill PDF
        2. **Click Process:** After uploading, click the "🚀 Process PDF and Extract Items" button in the sidebar
        """)
    else:
        # Display items with checkboxes
        st.header("📋 Bill Items - Check what you got")
        
        # Ensure items is a list and get it
        if not isinstance(st.session_state.items, list):
            st.session_state.items = []
        items_list = st.session_state.items if isinstance(st.session_state.items, list) else []
        
        # Debug info - always show item count
        st.info(f"📊 **Items in memory: {len(items_list)}**")
        
        if len(items_list) == 0:
            st.error("⚠️ Items list is empty. Please reload the PDF.")
            # Show what's actually in session state for debugging
            st.write(f"Debug - session_state.items type: {type(st.session_state.items)}")
            st.write(f"Debug - session_state.items value: {st.session_state.items}")
        else:
            st.success(f"✅ **{len(items_list)} items ready to select!**")
            st.markdown(f"**Total Items:** {len(items_list)}")
        
        # Initialize selections for current user if not exists
        if selected_user not in st.session_state.selections:
            st.session_state.selections[selected_user] = []
        
        # Create columns for better layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("Item Name")
        with col2:
            st.subheader("Price")
        
        # Search/filter functionality
        search_term = st.text_input("🔍 Search items", placeholder="Type to filter items...", key="search_input")
        
        # Ensure items is a list
        items_list = st.session_state.items if isinstance(st.session_state.items, list) else []
        
        # Filter items based on search - store indices instead of items
        filtered_indices = set(range(len(items_list)))
        if search_term:
            filtered_indices = {idx for idx, item in enumerate(items_list) 
                              if search_term.lower() in item['name'].lower()}
            st.info(f"Showing {len(filtered_indices)} of {len(items_list)} items")
        
        # Display items with checkboxes
        if filtered_indices:
            # Create a container for all checkboxes
            for idx, item in enumerate(items_list):
                # Only show if in filtered list
                if idx not in filtered_indices:
                    continue
                    
                item_id = f"{item['name']}_{idx}"
                is_checked = item_id in st.session_state.selections.get(selected_user, [])
                
                col1, col2, col3 = st.columns([0.1, 2.9, 1])
                
                with col1:
                    checked = st.checkbox(
                        "",
                        value=is_checked,
                        key=f"checkbox_{selected_user}_{item_id}",
                        label_visibility="collapsed"
                    )
                
                with col2:
                    # Highlight checked items
                    if checked:
                        st.markdown(f"✅ **{item['name']}**")
                    else:
                        st.write(item['name'])
                
                with col3:
                    st.write(f"**${item['price']:.2f}**")
                
                # Update selections immediately when checkbox changes
                if checked and item_id not in st.session_state.selections.get(selected_user, []):
                    if selected_user not in st.session_state.selections:
                        st.session_state.selections[selected_user] = []
                    st.session_state.selections[selected_user].append(item_id)
                    save_selections(st.session_state.selections)
                    st.rerun()
                elif not checked and item_id in st.session_state.selections.get(selected_user, []):
                    st.session_state.selections[selected_user].remove(item_id)
                    save_selections(st.session_state.selections)
                    st.rerun()
        elif search_term:
            st.warning("No items match your search.")
        
        st.markdown("---")
        
        # Calculate and display summary
        st.header("💵 Bill Split Summary")
        
        # Calculate totals for each user
        user_items = defaultdict(list)
        # Ensure items is a list before enumerating
        items_list = st.session_state.items if isinstance(st.session_state.items, list) else []
        item_dict = {f"{item['name']}_{idx}": item for idx, item in enumerate(items_list)}
        
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
        
        # Display summary in columns with better formatting
        cols = st.columns(3)
        for idx, user in enumerate(DEFAULT_USERS):
            with cols[idx % 3]:
                user_total = 0
                items_list = []
                for entry in split_summary[user]:
                    if isinstance(entry, tuple) and entry[0] == 'TOTAL':
                        user_total = entry[1]
                    else:
                        items_list.append(entry)
                
                # Color code based on total
                if user_total > 0:
                    with st.expander(f"**{user}** - ${user_total:.2f}", expanded=(user == selected_user)):
                        if items_list:
                            for entry in items_list:
                                st.write(f"• {entry['name']}")
                                if entry['shared_with'] > 1:
                                    st.caption(f"  ${entry['price']:.2f} (shared with {entry['shared_with']} people)")
                                else:
                                    st.caption(f"  ${entry['price']:.2f}")
                        else:
                            st.write("No items selected")
                        st.markdown(f"**Total: ${user_total:.2f}**")
                else:
                    with st.expander(f"**{user}** - $0.00", expanded=False):
                        st.write("No items selected")
        
        # Grand total
        grand_total = sum(entry[1] for user in DEFAULT_USERS 
                          for entry in split_summary[user] 
                          if isinstance(entry, tuple) and entry[0] == 'TOTAL')
        
        st.markdown("---")
        st.markdown(f"### **Grand Total: ${grand_total:.2f}**")
        
        # Show who selected what (for transparency)
        with st.expander("👥 View All Selections (Detailed)"):
            for user in DEFAULT_USERS:
                selected_items = st.session_state.selections.get(user, [])
                if selected_items:
                    st.markdown(f"### {user} ({len(selected_items)} items)")
                    items_list = st.session_state.items if isinstance(st.session_state.items, list) else []
                    item_dict = {f"{item['name']}_{idx}": item for idx, item in enumerate(items_list)}
                    for item_id in selected_items:
                        if item_id in item_dict:
                            item = item_dict[item_id]
                            st.write(f"  • {item['name']} - ${item['price']:.2f}")
                else:
                    st.write(f"**{user}** - No items selected yet")
        
        # Progress indicator
        total_selected = sum(len(st.session_state.selections.get(user, [])) for user in DEFAULT_USERS)
        items_list = st.session_state.items if isinstance(st.session_state.items, list) else []
        total_items = len(items_list)
        progress = total_selected / (total_items * len(DEFAULT_USERS)) if total_items > 0 else 0
        st.progress(progress)
        st.caption(f"Selection progress: {total_selected} selections made across all users")

if __name__ == "__main__":
    main()

