import logging
from pathlib import Path
from llama_index.core.schema import Document
import io

try:
    import easyocr
except ImportError:
    easyocr = None
    logging.warning(
        "easyocr not installed. Please install it to use EasyOcrProcessor: pip install easyocr"
    )

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    convert_from_path = None
    PDF2IMAGE_AVAILABLE = False
    logging.warning(
        "pdf2image not installed. PDF processing with EasyOcrProcessor will not be available. "
        "Install it with: pip install pdf2image"
    )

logger = logging.getLogger(__name__)

# Configuration for EasyOCR processing
# In a production environment, these should be loaded from a configuration file or environment variables.
EASY_OCR_ENABLED = True  # Master switch for this feature. Ensure this is True if you want the processor to be enabled by default.
EASY_OCR_LANGUAGES = ['en']  # Default languages for EasyOCR, e.g., ['en', 'ch_sim']
EASY_OCR_GPU = True  # Whether to use GPU for EasyOCR (if available and supported)
EASY_OCR_MODEL_STORAGE_DIRECTORY = None # Optional: Path to directory for model storage
EASY_OCR_USER_NETWORK_DIRECTORY = None # Optional: Path to directory for user network
EASY_OCR_DOWNLOAD_ENABLED = True # Optional: Enable/disable model auto-download

class EasyOcrProcessor:
    """
    Processes images using EasyOCR to extract text.
    Can also handle PDF files by converting their pages to images first.
    """

    EASY_OCR_ENABLED = EASY_OCR_ENABLED

    def __init__(
        self,
        languages: list[str] | None = None,
        gpu: bool = EASY_OCR_GPU,
        model_storage_directory: str | None = EASY_OCR_MODEL_STORAGE_DIRECTORY,
        user_network_directory: str | None = EASY_OCR_USER_NETWORK_DIRECTORY,
        download_enabled: bool = EASY_OCR_DOWNLOAD_ENABLED,
        enabled: bool = EASY_OCR_ENABLED, # This defaults to the module-level EASY_OCR_ENABLED
    ):
        self.enabled = enabled
        self.reader = None
        self.languages = languages if languages is not None else EASY_OCR_LANGUAGES
        self.gpu = gpu
        self.model_storage_directory = model_storage_directory
        self.user_network_directory = user_network_directory
        self.download_enabled = download_enabled

        if not self.enabled:
            logger.info("EasyOCR Processor is disabled by configuration.")
            return

        if easyocr is None:
            logger.error("EasyOCR library is not installed. EasyOcrProcessor cannot function.")
            self.enabled = False
            return

        try:
            logger.info(
                f"Initializing EasyOCR Reader with languages: {self.languages}, GPU: {self.gpu}"
            )
            self.reader = easyocr.Reader(
                self.languages,
                gpu=self.gpu,
                model_storage_directory=self.model_storage_directory,
                user_network_directory=self.user_network_directory,
                download_enabled=self.download_enabled,
            )
            logger.info("EasyOCR Reader initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR Reader: {e}")
            self.enabled = False  # Disable if reader fails to initialize

    def _process_image_data(self, image_data: bytes, source_description: str) -> str:
        """Helper to process image bytes with EasyOCR."""
        try:
            ocr_results = self.reader.readtext(image_data, detail=0, paragraph=True)
            return "\n".join(ocr_results).strip()
        except Exception as e:
            logger.error(f"EasyOCR failed to process image data from {source_description}: {e}")
            return ""

    def load_data(self, file_path: Path, file_name: str) -> list[Document] | None:
        """
        Loads an image or PDF file, extracts text using EasyOCR, and returns a Document.
        For PDFs, pages are converted to images and processed.
        Returns None if processing is disabled, fails, the file doesn't exist, or no text is found.
        """
        if not self.enabled or not self.reader:
            logger.debug(
                f"EasyOCR processing skipped for {file_name} (disabled or reader not initialized)."
            )
            return None

        if not file_path.exists():
            logger.error(f"File not found for EasyOCR processing: {file_path}")
            return None
        
        if not file_path.is_file():
            logger.error(f"Path is not a file, skipping EasyOCR: {file_path}")
            return None

        extracted_text_parts = []
        
        try:
            file_extension = file_path.suffix.lower()
            
            if file_extension == ".pdf":
                if not PDF2IMAGE_AVAILABLE:
                    logger.error(
                        f"pdf2image library is not available, cannot process PDF: {file_name}. "
                        "Please install it (e.g., pip install pdf2image) and ensure Poppler is in PATH."
                    )
                    return None
                logger.info(f"Processing PDF {file_name} with EasyOCR (via pdf2image conversion).")
                try:
                    images_from_path = convert_from_path(file_path)
                    if not images_from_path:
                        logger.warning(f"pdf2image converted {file_name} into zero images.")
                        return None
                        
                    for i, image_pil in enumerate(images_from_path):
                        logger.debug(f"Processing page {i+1} of {file_name}")
                        img_byte_arr = io.BytesIO()
                        image_pil.save(img_byte_arr, format='PNG') # Or JPEG, PNG is lossless
                        img_bytes = img_byte_arr.getvalue()
                        page_text = self._process_image_data(img_bytes, f"page {i+1} of {file_name}")
                        if page_text:
                            extracted_text_parts.append(page_text)
                except Exception as e:
                    logger.error(f"Error converting PDF {file_name} to images or processing pages: {e}")
                    return None # Or handle partial extraction if desired

            elif file_extension in {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}: # Add other image types if needed
                logger.info(f"Attempting to process image {file_name} with EasyOCR.")
                image_bytes = file_path.read_bytes()
                image_text = self._process_image_data(image_bytes, file_name)
                if image_text:
                    extracted_text_parts.append(image_text)
            else:
                logger.warning(f"Unsupported file type for EasyOcrProcessor: {file_extension} for file {file_name}. Skipping.")
                return None

            final_extracted_text = "\n\n".join(extracted_text_parts).strip() # Join pages/parts with double newline

            if final_extracted_text:
                document = Document(
                    text=final_extracted_text,
                    metadata={
                        "file_name": file_name,
                        "source_model": "easyocr",
                        "ocr_languages": self.languages,
                        "processing_method": "easy_ocr_extraction"
                        # doc_id will be auto-generated by LlamaIndex
                    }
                )
                document.text = document.text.replace("\x00", "").replace("\\u0000", "")
                logger.info(
                    f"Successfully processed file {file_name} with EasyOCR. Text length: {len(final_extracted_text)}"
                )
                return [document]
            else:
                logger.warning(f"EasyOCR processing for file {file_name} returned no text.")
                return None
        
        except Exception as e:
            logger.error(f"An unexpected error occurred processing file {file_name} with EasyOCR: {e}", exc_info=True)
            return None
