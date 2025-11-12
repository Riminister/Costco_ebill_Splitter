# Costco Bill Splitter

A Streamlit web application for splitting Costco bills among multiple users. Each user can check off items they received, and the app automatically calculates how much each person owes.

## Features

- 📄 Automatically extracts items from Costco PDF bills
- ✅ Interactive checkboxes for each user to select their items
- 💰 Automatic price splitting for shared items
- 📊 Real-time bill summary showing each person's total
- 💾 Saves selections so multiple users can use the app simultaneously

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Place your Costco bill PDF:**
   - Save your Costco bill as `bill.pdf` in the project root directory

3. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

4. **Access the app:**
   - The app will open in your browser (usually at `http://localhost:8501`)
   - Each user should select their name from the sidebar
   - Check off items they received
   - View the bill split summary at the bottom

## Users

The app is configured for 6 users:
- Alex
- Daniel
- Jacob
- Jordan
- Judah
- Adam

## How It Works

1. **Load Bill:** Click "Reload Bill from PDF" in the sidebar to extract items from `bill.pdf`
2. **Select Items:** Each user selects their name and checks off items they received
3. **Automatic Splitting:** Items selected by multiple users are automatically split evenly
4. **View Summary:** See each person's total at the bottom of the page

## File Structure

```
Costco_Bill_Order/
├── app.py              # Streamlit web application
├── python.py           # Original command-line script
├── requirements.txt    # Python dependencies
├── bill.pdf           # Costco bill PDF (not in git)
├── selections.json    # Saved user selections (not in git)
└── README.md          # This file
```

## Notes

- The app handles tax automatically (13% HST for items marked with 'Y' in the PDF)
- Discounts are automatically applied to the previous item
- Selections are saved in `selections.json` so multiple users can use the app at the same time
- The original command-line script (`python.py`) is still available for non-web use

