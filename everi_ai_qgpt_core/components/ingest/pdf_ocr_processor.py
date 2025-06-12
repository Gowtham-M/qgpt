"""Enhanced PDF processor with OCR and image extraction capabilities."""

import io
import logging
import tempfile
from pathlib import Path
from typing import Any, List, Optional

try:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image
    import requests
    import base64
except ImportError as e:
    raise ImportError(
        "PDF OCR dependencies not found. Install with: "
        "pip install PyMuPDF pytesseract pillow"
    ) from e

from llama_index.core.schema import Document

logger = logging.getLogger(__name__)


class PDFOCRProcessor:
    """Enhanced PDF processor that extracts text, images, and performs OCR."""    
    def __init__(self, ollama_api_base: str = "http://localhost:11434", vision_model: str = "llava:7b"):
        self.ollama_api_base = ollama_api_base
        self.vision_model = vision_model
          # Configure Tesseract path on Windows
        import platform
        if platform.system() == "Windows":
            tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            if Path(tesseract_path).exists():
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def process_pdf_with_ocr(self, file_path: Path) -> List[Document]:
        """Process PDF with OCR capabilities and image analysis."""
        documents = []
        
        try:
            pdf_document = fitz.open(file_path)
            logger.info(f"Processing PDF with {len(pdf_document)} pages")
            
            # Extract text and images from each page
            combined_content = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                page_content = []
                
                # Extract regular text
                text = page.get_text()
                if text.strip():
                    page_content.append(f"Text content:\n{text}")
                  # Extract images and process them
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Extract image using safe method
                        xref = img[0]
                        pil_image = self._extract_image_safely(pdf_document, xref, img_index, page_num)
                        
                        if pil_image is None:
                            logger.warning(f"Skipping image {img_index} on page {page_num}: Could not extract image")
                            continue
                        
                        # Process image with OCR
                        ocr_text = self._extract_text_with_ocr(pil_image)
                        if ocr_text.strip():
                            page_content.append(f"OCR extracted text from image {img_index + 1}:\n{ocr_text}")
                        
                        # Process image with Ollama vision model
                        vision_description = self._analyze_image_with_ollama(pil_image)
                        if vision_description:
                            page_content.append(f"Image {img_index + 1} analysis:\n{vision_description}")
                        
                    except Exception as e:
                        logger.warning(f"Error processing image {img_index} on page {page_num}: {e}")
                        continue
                
                # Combine all content for this page
                if page_content:
                    page_text = f"\n\n--- Page {page_num + 1} ---\n\n" + "\n\n".join(page_content)
                    combined_content.append(page_text)
            
            # Create a single document with all extracted content
            if combined_content:
                full_text = "\n\n".join(combined_content)
                document = Document(
                    text=full_text,
                    metadata={
                        "file_name": file_path.name,
                        "source": "pdf_with_ocr",
                        "total_pages": len(pdf_document)
                    }
                )
                documents.append(document)
            
            pdf_document.close()
            
        except Exception as e:
            logger.error(f"Error processing PDF with OCR: {e}")
            raise
        
        return documents
    def _extract_text_with_ocr(self, image: Image.Image) -> str:
        """Extract text from image using OCR."""
        try:
            # Convert image to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Set Tesseract path for Windows
            import platform
            if platform.system() == "Windows":
                # Common Windows installation paths
                tesseract_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    r"C:\Tools\tesseract\tesseract.exe"
                ]
                
                for path in tesseract_paths:
                    if Path(path).exists():
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
            
            # Perform OCR
            ocr_text = pytesseract.image_to_string(image, lang='eng')
            return ocr_text.strip()
        
        except Exception as e:
            logger.warning(f"OCR extraction failed: {e}")
            return ""
    def _analyze_image_with_ollama(self, image: Image.Image) -> Optional[str]:
        """Analyze image using Ollama vision model."""
        try:
            # Convert image to base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Prepare request to Ollama
            url = f"{self.ollama_api_base}/api/generate"
            
            payload = {
                "model": self.vision_model,
                "prompt": "Describe this image in detail. Focus on any text, diagrams, charts, or important visual elements that would be useful for document understanding.",
                "images": [image_b64],
                "stream": False
            }
            
            logger.info(f"Sending request to Ollama vision model: {self.vision_model}")
            response = requests.post(url, json=payload, timeout=150)
            
            logger.info(f"Ollama response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                vision_response = result.get('response', '').strip()
                logger.info(f"Vision model response length: {len(vision_response)} characters")
                return vision_response
            else:
                logger.warning(f"Ollama vision model request failed: {response.status_code}")
                logger.warning(f"Response content: {response.text}")
                return None
                
        except Exception as e:
            logger.warning(f"Image analysis with Ollama failed: {e}")
            return None
    def _normalize_pdf_if_needed(self, file_path: Path) -> Path:
        """Normalize PDF by re-saving it to fix colorspace and other issues."""
        try:
            # Create a temporary normalized PDF
            normalized_path = file_path.parent / f"normalized_{file_path.name}"
            
            # Open and re-save the PDF with cleanup options
            doc = fitz.open(file_path)
            doc.save(
                normalized_path,
                garbage=3,      # Remove unused objects
                clean=True,     # Clean up internal structures
                deflate=True    # Compress streams
            )
            doc.close()
            
            logger.info(f"Created normalized PDF: {normalized_path}")
            return normalized_path
            
        except Exception as e:
            logger.warning(f"Failed to normalize PDF: {e}")
            return file_path
    def _extract_image_safely(self, pdf_document, xref, img_index, page_num):
        """Safely extract image with multiple fallback methods."""
        pil_image = None
        
        # Method 1: Try base image extraction first (most reliable)
        try:
            base_image = pdf_document.extract_image(xref)
            if base_image and "image" in base_image:
                image_data = base_image["image"]
                pil_image = Image.open(io.BytesIO(image_data))
                logger.debug(f"Successfully extracted image {img_index} on page {page_num} using base image method")
                return pil_image
        except Exception as e:
            logger.debug(f"Base image extraction failed for image {img_index} on page {page_num}: {e}")
        
        # Method 2: Try pixmap extraction with error handling
        try:
            pix = fitz.Pixmap(pdf_document, xref)
            
            # Check if pixmap has valid colorspace
            if pix.colorspace is None:
                logger.warning(f"Pixmap has no colorspace for image {img_index} on page {page_num}")
                pix = None
                return None
            
            # Handle images with alpha channel
            if pix.alpha:
                try:
                    # Remove alpha channel by converting to RGB
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                except Exception as e:
                    logger.warning(f"Failed to remove alpha channel from image {img_index} on page {page_num}: {e}")
                    pix = None
                    return None
            
            # Convert to PIL Image
            if pix.n - pix.alpha < 4:  # GRAY or RGB
                img_data = pix.tobytes("png")
                pil_image = Image.open(io.BytesIO(img_data))
            else:
                # For CMYK images, convert to RGB first
                try:
                    pix_rgb = fitz.Pixmap(fitz.csRGB, pix)
                    img_data = pix_rgb.tobytes("png")
                    pil_image = Image.open(io.BytesIO(img_data))
                    pix_rgb = None  # Clean up
                except Exception as e:
                    logger.warning(f"Failed to convert CMYK image {img_index} on page {page_num}: {e}")
                    pix = None
                    return None
            
            pix = None  # Clean up
            logger.debug(f"Successfully extracted image {img_index} on page {page_num} using pixmap method")
            return pil_image
            
        except Exception as e:
            logger.warning(f"Pixmap extraction failed for image {img_index} on page {page_num}: {e}")
            return None


class EnhancedPDFReader:
    """Enhanced PDF reader that uses OCR processor."""
    
    def __init__(self, use_ocr: bool = True, ollama_api_base: str = "http://localhost:11434"):
        self.use_ocr = use_ocr
        self.ocr_processor = PDFOCRProcessor(ollama_api_base) if use_ocr else None
    
    def load_data(self, file_path: Path) -> List[Document]:
        """Load PDF data with optional OCR processing."""
        try:
            if self.use_ocr and self.ocr_processor:
                return self.ocr_processor.process_pdf_with_ocr(file_path)
            else:
                # Fallback to regular PDF processing
                return self._load_regular_pdf(file_path)
                
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            # Fallback to regular PDF processing if OCR fails
            return self._load_regular_pdf(file_path)
    
    def _load_regular_pdf(self, file_path: Path) -> List[Document]:
        """Fallback regular PDF processing."""
        try:
            from llama_index.readers.file.docs import PDFReader
            
            pdf_reader = PDFReader()
            return pdf_reader.load_data(file_path)
            
        except Exception as e:
            logger.error(f"Regular PDF processing also failed: {e}")
            raise
