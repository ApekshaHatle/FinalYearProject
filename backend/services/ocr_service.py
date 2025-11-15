"""OCR Service for extracting text from images"""
import pytesseract
from PIL import Image
import os

class OCRService:
    def __init__(self):
        # Set Tesseract path for Windows
        # Adjust this path if you installed Tesseract elsewhere
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        print("✅ OCR Service initialized")
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from an image file"""
        try:
            # Open image
            image = Image.open(image_path)
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(image, lang='eng')
            
            # Clean up text
            text = text.strip()
            
            if not text:
                return "No text found in image."
            
            return text
            
        except Exception as e:
            print(f"❌ Error extracting text from image: {e}")
            raise Exception(f"Failed to extract text: {str(e)}")

# Global instance
ocr_service = OCRService()