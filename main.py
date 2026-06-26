from pypdf import PdfReader

reader = PdfReader("Pricebook_HorizonTrailers_HQ_2026-06-17 1.pdf")

# Let's say UTZ / ETZ starts around page 20—adjust target page as needed
for page_num in range(15, 30): 
    page = reader.pages[page_num]
    # 'layout' mode preserves exact horizontal text positioning with spaces
    text = page.extract_text(extraction_mode="layout")
    
    if "UTZ" in text or "ETZ" in text:
        print(f"--- PAGE {page_num} ---")
        print(text)