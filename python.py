import re
from collections import defaultdict

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("PyPDF2 not available. Please install it with: pip install PyPDF2")
    print("Or manually enter the bill items below.")

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
        print(f"Error reading PDF: {e}")
    return text

def manual_item_entry():
    """Allow manual entry of items if PDF reading fails"""
    items = []
    print("\nEnter bill items manually:")
    print("Format: Item Name, Price (e.g., 'Pizza, 15.99')")
    print("Press Enter with empty input to finish")
    
    while True:
        item_input = input("Item: ").strip()
        if not item_input:
            break
        
        try:
            if ',' in item_input:
                name, price = item_input.rsplit(',', 1)
                items.append({'name': name.strip(), 'price': float(price.strip())})
            else:
                print("Please use format: Item Name, Price")
        except ValueError:
            print("Invalid price format. Please try again.")
    
    return items

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

def main():
    pdf_path = "bill.pdf"
    
    print("Starting bill splitter...")
    print(f"Looking for PDF file: {pdf_path}")
    
    # Extract text from PDF
    print("Reading bill from PDF...")
    bill_text = extract_text_from_pdf(pdf_path)
    
    print(f"PDF_AVAILABLE: {PDF_AVAILABLE}")
    print(f"Bill text length: {len(bill_text)}")
    
    if not bill_text.strip():
        print("Could not extract text from PDF. Please check if the file exists and is readable.")
        items = manual_item_entry()
        if not items:
            print("No items entered. Exiting.")
            return
    else:
        # Parse items from the text
        items = parse_bill_items(bill_text)
        
        if not items:
            print("\nNo items found in the bill. The PDF format might not be compatible.")
            print("Please check the extracted text above and adjust the parsing logic if needed.")
            items = manual_item_entry()
            if not items:
                print("No items entered. Exiting.")
                return
    
    if bill_text.strip():
        print("Bill text extracted successfully!")
        print("\nExtracted text:")
        print("-" * 50)
        print(bill_text[:500] + "..." if len(bill_text) > 500 else bill_text)
        print("-" * 50)
    
    print(f"\nFound {len(items)} items:")
    for i, item in enumerate(items, 1):
        print(f"{i}. {item['name']} - ${item['price']:.2f}")
    
    print(f"\nTotal items found: {len(items)}")
    
    # Get list of users
    print("\nEnter the names of people splitting the bill:")
    print("Enter names separated by commas (e.g., Daniel, Jacob, Jordan, Judah, Alex, Adam, Sam)")
    users_input = input("Users: ").strip()
    
    if not users_input:
        print("No users entered. Exiting.")
        return
    
    users = [name.strip() for name in users_input.split(',')]
    print(f"\nUsers: {', '.join(users)}")
    
    # Interactive item assignment
    print("\nNow assign each item to users:")
    print("For each item, enter the numbers of users who should pay for it.")
    print("Example: For item shared by Daniel(1) and Jacob(2), enter: 1,2")
    print("Example: For item only for Jordan(3), enter: 3")
    print("Example: For item shared by everyone, enter: 1,2,3,4,5,6,7")
    
    user_items = defaultdict(list)
    
    for i, item in enumerate(items):
        print(f"\nItem {i+1}: {item['name']} - ${item['price']:.2f}")
        print(f"Users: {', '.join([f'{j+1}.{users[j]}' for j in range(len(users))])}")
        
        while True:
            try:
                user_input = input("Enter user numbers (comma-separated): ").strip()
                if not user_input:
                    print("Please enter at least one user number.")
                    continue
                
                user_indices = [int(x.strip()) - 1 for x in user_input.split(',')]
                
                # Validate indices
                if any(idx < 0 or idx >= len(users) for idx in user_indices):
                    print(f"Please enter numbers between 1 and {len(users)}")
                    continue
                
                # Calculate split price per user
                split_price = item['price'] / len(user_indices)
                
                # Add item to selected users with split price
                for idx in user_indices:
                    split_item = item.copy()
                    split_item['price'] = split_price
                    user_items[users[idx]].append(split_item)
                
                print(f"Assigned to: {[users[idx] for idx in user_indices]} (${split_price:.2f} each)")
                break
                
            except ValueError:
                print("Please enter valid numbers separated by commas.")
            except Exception as e:
                print(f"Error: {e}")
    
    # Calculate totals for each user
    print("\n" + "="*50)
    print("BILL SPLIT SUMMARY")
    print("="*50)
    
    total_bill = 0
    for user in users:
        user_total = sum(item['price'] for item in user_items[user])
        print(f"\n{user}:")
        for item in user_items[user]:
            print(f"  - {item['name']}: ${item['price']:.2f}")
        print(f"  Total: ${user_total:.2f}")
        total_bill += user_total
    
    print(f"\nGrand Total: ${total_bill:.2f}")
    
    # Verify the split is correct
    print(f"\nVerification:")
    print(f"Total of all user amounts: ${total_bill:.2f}")
    print(f"Number of users: {len(users)}")
    print(f"Items per user: {[len(user_items[user]) for user in users]}")

if __name__ == "__main__":
    print("Script starting...")
    try:
        main()
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
