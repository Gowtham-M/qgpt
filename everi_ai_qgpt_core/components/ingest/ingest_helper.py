import logging
from pathlib import Path
from typing import List, Optional

from llama_index.core.readers import StringIterableReader
from llama_index.core.readers.base import BaseReader
from llama_index.core.readers.json import JSONReader
from llama_index.core.schema import Document

from .easy_ocr_processor import EasyOcrProcessor  # Existing import
from .easy_ocr_processor import PDF2IMAGE_AVAILABLE as EASY_OCR_PDF_CAPABLE # Import for check

logger = logging.getLogger(__name__)

# Try to import EasyOCR processor
try:
    processor_instance_for_check = EasyOcrProcessor(enabled=False)
    easyocr_lib_ok = processor_instance_for_check.reader is not None or EasyOcrProcessor.EASY_OCR_ENABLED
    
    if easyocr_lib_ok:
        EASY_OCR_PROCESSOR_AVAILABLE = True
        logger.info("EasyOCR Processor potentially available (EasyOCR library imported).")
        if not EASY_OCR_PDF_CAPABLE:
            logger.warning(
                "pdf2image library not found or Poppler not configured. "
                "PDF processing via EasyOCR will not be available."
            )
    else:
        EASY_OCR_PROCESSOR_AVAILABLE = False
        logger.warning("EasyOCR library not found by EasyOcrProcessor, EasyOCR will not be used.")
except ImportError: 
    EASY_OCR_PROCESSOR_AVAILABLE = False
    logger.warning("EasyOCR Processor or its dependency (e.g. pdf2image) not available (ImportError). EasyOCR features might be limited.")
except Exception as e: 
    EASY_OCR_PROCESSOR_AVAILABLE = False
    logger.warning(f"EasyOCR Processor not available due to an error: {e}. EasyOCR will not be used.")

try:
    from everi_ai_qgpt_core.components.ingest.ollama_image_processor import OllamaImageProcessor
    OLLAMA_IMAGE_PROCESSOR_AVAILABLE = True
    logger.info("Ollama Image Processor available")
except ImportError as e:
    logger.warning(f"Ollama Image Processor not available: {e}")
    OLLAMA_IMAGE_PROCESSOR_AVAILABLE = False

def _try_loading_included_file_formats() -> dict[str, type[BaseReader]]:
    try:
        from llama_index.readers.file.docs import (
            DocxReader,
            HWPReader,
            PDFReader,
        )
        from llama_index.readers.file.epub import EpubReader
        from llama_index.readers.file.image import ImageReader
        from llama_index.readers.file.ipynb import IPYNBReader
        from llama_index.readers.file.markdown import MarkdownReader
        from llama_index.readers.file.mbox import MboxReader
        from llama_index.readers.file.slides import PptxReader
        from llama_index.readers.file.tabular import PandasCSVReader, PandasExcelReader
        from llama_index.readers.file.video_audio import VideoAudioReader
    except ImportError as e:
        raise ImportError("`llama-index-readers-file` package not found") from e

    default_file_reader_cls: dict[str, type[BaseReader]] = {
        ".hwp": HWPReader,
        ".pdf": PDFReader,
        ".docx": DocxReader,
        ".pptx": PptxReader,
        ".ppt": PptxReader,
        ".pptm": PptxReader,
        ".jpg": ImageReader,
        ".png": ImageReader,
        ".jpeg": ImageReader,
        ".mp3": VideoAudioReader,
        ".mp4": VideoAudioReader,
        ".csv": PandasCSVReader,
        ".xlsx": PandasExcelReader,
        ".xls": PandasExcelReader,
        ".epub": EpubReader,
        ".md": MarkdownReader,
        ".mbox": MboxReader,
        ".ipynb": IPYNBReader,
    }
    return default_file_reader_cls


FILE_READER_CLS = _try_loading_included_file_formats()
FILE_READER_CLS.update(
    {
        ".json": JSONReader,
    }
)


class IngestionHelper:
    """Helper class to transform a file into a list of documents."""

   
    @staticmethod
    def transform_file_into_documents(
        file_name: str, file_data: Path
    ) -> list[Document]:
        documents = IngestionHelper._load_file_to_documents(file_name, file_data)
        if not documents:
            return []        
        # Ensure consistent doc_id for multi-page sources like PDFs if they weren't handled by a specific processor
        # For EasyOCR, it should return a single document with combined text.
        # For default PDFReader, we might get multiple documents if not handled properly below.
        is_pdf_fallback = Path(file_name).suffix.lower() == ".pdf" and not (
            EASY_OCR_PROCESSOR_AVAILABLE and 
            any(doc.metadata.get("processing_method") == "easy_ocr_extraction" for doc in documents)
        )

        if documents and is_pdf_fallback:
            # This logic is for the default PDF reader if EasyOCR wasn't used or failed
            global_doc_id = documents[0].doc_id 
            for document in documents:
                document.metadata["doc_id"] = global_doc_id
        
        for document in documents:
            document.metadata["file_name"] = file_name
        
        IngestionHelper._exclude_metadata(documents)
        return documents

    @staticmethod
    def _load_file_to_documents(file_name: str, file_data: Path) -> list[Document]:
        logger.debug("Transforming file_name=%s into documents", file_name)
        extension = Path(file_name).suffix.lower()
        
        easyocr_supported_image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

        if extension == ".pdf" and EASY_OCR_PROCESSOR_AVAILABLE:
            try:
                logger.info(f"Attempting EasyOCR processing for PDF: {file_name}")
                easy_ocr_processor = EasyOcrProcessor() 
                if easy_ocr_processor.enabled and easy_ocr_processor.reader:
                    # EasyOcrProcessor now handles PDF to image conversion internally
                    documents = easy_ocr_processor.load_data(file_data, file_name)
                    if documents:
                        logger.info(f"Successfully processed PDF {file_name} with EasyOcrProcessor.")
                        return documents
                    else:
                        # Log already happens in EasyOcrProcessor if pdf2image is missing or conversion fails
                        logger.warning(f"EasyOcrProcessor for PDF {file_name} returned no documents or encountered an issue. Falling back to default PDFReader.")
                else:
                    logger.info(f"EasyOcrProcessor is not enabled or reader not initialized for PDF {file_name}. Falling back to default PDFReader.")
            except Exception as e:
                logger.error(f"Error using EasyOcrProcessor for PDF {file_name}: {e}. Falling back to default PDFReader.")
            # Fall through to default PDF reader

        if extension in easyocr_supported_image_extensions and EASY_OCR_PROCESSOR_AVAILABLE:
            try:
                logger.info(f"Attempting EasyOCR processing for image: {file_name}")
                easy_ocr_processor = EasyOcrProcessor() 
                if easy_ocr_processor.enabled and easy_ocr_processor.reader:
                    documents = easy_ocr_processor.load_data(file_data, file_name)
                    if documents:
                        logger.info(f"Successfully processed image {file_name} with EasyOcrProcessor.")
                        # NUL byte sanitization and metadata is handled by EasyOcrProcessor
                        return documents
                    else:
                        logger.warning(f"EasyOcrProcessor for image {file_name} returned no documents. Falling back to default ImageReader.")
                else:
                    logger.info(f"EasyOcrProcessor is not enabled or reader not initialized for image {file_name}. Falling back to default ImageReader.")
            except Exception as e:
                logger.error(f"An unexpected error occurred using EasyOcrProcessor for image {file_name}: {e}. Falling back to default ImageReader.")

        # Fall through to default ImageReader if EasyOCR fails or is not applicable
        image_extensions = {".jpg", ".jpeg", ".png"}
        if extension in image_extensions and OLLAMA_IMAGE_PROCESSOR_AVAILABLE:
            try:
                # Initialize the processor (it will use its own default or environment-set configurations)
                ollama_processor = OllamaImageProcessor()
                if ollama_processor.enabled:
                    documents = ollama_processor.load_data(file_data, file_name)
                    if documents:
                        logger.info(f"Successfully processed image {file_name} with OllamaImageProcessor.")
                        # NUL byte sanitization is handled within OllamaImageProcessor
                        return documents
                    else:
                        logger.warning(f"OllamaImageProcessor for image {file_name} returned no documents. Falling back to default ImageReader.")
                else:
                    logger.info(f"OllamaImageProcessor is disabled. Falling back to default ImageReader for {file_name}.")
            except Exception as e:
                logger.error(f"An unexpected error occurred using OllamaImageProcessor for image {file_name}: {e}. Falling back to default ImageReader.")
            # If any exception occurs, processor is disabled, or returns no documents, 
            # code execution falls through to the default ImageReader logic below.
            # Regular file processing (including fallbacks for PDF/Images)
        reader_cls = FILE_READER_CLS.get(extension)
        if reader_cls is None:
            # Only use string reader for known text file types
            text_extensions = {'.txt', '.log', '.json', '.xml', '.html', '.htm', '.css', '.js', '.py', '.java', '.c', '.cpp', '.h', '.cs', '.php', '.rb', '.pl', '.sh', '.bat', '.ps1', '.sql'}
            # If no extension, treat as text file (common for Google Docs and similar content)
            if extension in text_extensions or extension == "":
                logger.debug(
                    "No specific reader found for extension=%s, using default string reader",
                    extension,
                )               
                string_reader = StringIterableReader()
                try:
                    # Try UTF-8 first
                    text_content = file_data.read_text('utf-8')
                    return string_reader.load_data([text_content])
                except UnicodeDecodeError as e:
                    logger.warning(f"UTF-8 decoding failed for {file_name}, trying with error handling: {e}")
                    try:
                        # Try with error handling
                        text_content = file_data.read_text('utf-8', errors='replace')
                        return string_reader.load_data([text_content])
                    except Exception as e2:
                        logger.error(f"Failed to read file as text with error handling: {e2}")
                        raise ValueError(f"Failed to read file as text: {extension}")
                except Exception as e:
                    logger.error(
                        "Failed to read file as text. File may be binary or use a different encoding.",
                    )
                    raise ValueError(f"Failed to read file as text: {extension}")
            else:
                logger.error(
                    "Unsupported file type: %s. Please convert to a supported format.",
                    extension,
                )
                raise ValueError(f"Unsupported file type: {extension}")

        logger.debug("Specific reader found for extension=%s", extension)
        reader = reader_cls()
        try:
            documents = reader.load_data(file_data)
        except Exception as e:
            logger.error(f"Failed to read file with {reader_cls.__name__}: {str(e)}")
            raise

        if extension == ".pdf":
            # This block now primarily serves as a fallback if EasyOCR wasn't used or failed for PDFs.
            # If EasyOCR was successful, it should have returned a single document already.
            is_processed_by_easyocr = any(doc.metadata.get("processing_method") == "easy_ocr_extraction" for doc in documents) if documents else False
            if not is_processed_by_easyocr:
                logger.debug("Applying default PDF processing: merging pages into a single document")
                combined_text = "\n".join(doc.text for doc in documents)
                # Preserve metadata from the first page if available, then add file_name
                base_metadata = documents[0].metadata if documents else {}
                base_metadata["file_name"] = file_name
                documents = [Document(text=combined_text, metadata=base_metadata)]
            # If processed by EasyOCR, it should already be a single document.

        # Sanitize NUL bytes in text which can't be stored in Postgres
        for doc in documents:
            doc.text = doc.text.replace("\u0000", "")

        return documents

    @staticmethod
    def _exclude_metadata(documents: list[Document]) -> None:
        logger.debug("Excluding metadata from count=%s documents", len(documents))
        for document in documents:
            document.excluded_embed_metadata_keys = ["doc_id"]
            document.excluded_llm_metadata_keys = ["file_name", "doc_id", "page_label"]

    def process_image_with_easyocr(
        file_path: Path, 
        file_name: str,
        easyocr_languages: Optional[List[str]] = None, # Allow overriding default languages
        easyocr_gpu: Optional[bool] = None # Allow overriding GPU setting
    ) -> Optional[List[Document]]:
        """
        Processes an image file using EasyOcrProcessor to extract text.

        Args:
            file_path: Path to the image file.
            file_name: Name of the image file.
            easyocr_languages: Optional list of language codes for EasyOCR.
            easyocr_gpu: Optional boolean to enable/disable GPU for EasyOCR.

        Returns:
            A list of Document objects containing the extracted text, or None if processing fails.
        """
        try:
            logger.debug(f"Attempting EasyOCR processing for image: {file_name}")
            
            # Prepare kwargs for EasyOcrProcessor, only including non-None overrides
            processor_kwargs = {}
            if easyocr_languages is not None:
                processor_kwargs['languages'] = easyocr_languages
            if easyocr_gpu is not None:
                processor_kwargs['gpu'] = easyocr_gpu
                
            easy_ocr_processor = EasyOcrProcessor(**processor_kwargs)
            
            if not easy_ocr_processor.enabled:
                logger.info(f"EasyOCR processor is not enabled. Skipping OCR for {file_name}.")
                return None
                
            documents = easy_ocr_processor.load_data(file_path, file_name)
            
            if documents:
                logger.info(f"Successfully extracted text from {file_name} using EasyOCR.")
                return documents
            else:
                logger.info(f"No text extracted or EasyOCR processing failed for {file_name}.")
                return None
                
        except Exception as e:
            logger.error(f"Error during EasyOCR processing for {file_name}: {e}", exc_info=True)
            return None
                
          
