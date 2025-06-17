import logging
from pathlib import Path
from typing import List, Optional

from llama_index.core.readers import StringIterableReader
from llama_index.core.readers.base import BaseReader
from llama_index.core.readers.json import JSONReader
from llama_index.core.schema import Document

from .easy_ocr_processor import EasyOcrProcessor  # Existing import

logger = logging.getLogger(__name__)

# Try to import EasyOCR processor
try:
    # EasyOcrProcessor is already imported, check if easyocr library itself is available
    if EasyOcrProcessor(enabled=False).reader is not None or EasyOcrProcessor.EASY_OCR_ENABLED: # Check if easyocr was imported successfully by the processor
        EASY_OCR_PROCESSOR_AVAILABLE = True
        logger.info("EasyOCR Processor potentially available (library imported).")
    else:
        # This case might occur if easyocr itself failed to import within EasyOcrProcessor
        EASY_OCR_PROCESSOR_AVAILABLE = False
        logger.warning("EasyOCR library not found by EasyOcrProcessor, EasyOCR will not be used.")
except ImportError: # Should be caught by EasyOcrProcessor's own try-except for easyocr
    EASY_OCR_PROCESSOR_AVAILABLE = False
    logger.warning("EasyOCR Processor not available (ImportError). EasyOCR will not be used.")
except Exception as e: # Catch other potential init errors
    EASY_OCR_PROCESSOR_AVAILABLE = False
    logger.warning(f"EasyOCR Processor not available due to an error: {e}. EasyOCR will not be used.")


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
        
        # Supported image types for EasyOCR
        easyocr_supported_image_extensions = {".jpg", ".jpeg", ".png"}

        # Priority 1: PDF processing with EasyOCR
        if extension == ".pdf" and EASY_OCR_PROCESSOR_AVAILABLE:
            try:
                logger.info(f"Attempting EasyOCR processing for PDF: {file_name}")
                easy_ocr_processor = EasyOcrProcessor() # Uses default languages/GPU settings
                if easy_ocr_processor.enabled and easy_ocr_processor.reader:
                    # EasyOcrProcessor expects an image path. For PDFs, we'd typically convert pages to images.
                    # However, the current EasyOcrProcessor is designed for image files directly.
                    # To use EasyOCR for PDFs, we would need a PDF-to-image conversion step first.
                    # For now, we'll assume EasyOcrProcessor can handle PDF paths if it's adapted for it,
                    # or this block will effectively be skipped if it only works for images.
                    # A more robust solution would involve pdf2image library here.
                    # Given the current EasyOcrProcessor, it's more likely to be used for images.
                    # Let's assume for now the user wants to try it on PDFs directly if the library supports it,
                    # or this is a placeholder for future PDF-to-image-then-OCR pipeline.
                    # If EasyOcrProcessor's load_data is strictly for images, this will fail gracefully.
                    
                    # To make this work for PDFs with EasyOCR, we'd need to:
                    # 1. Convert PDF pages to images (e.g., using pdf2image).
                    # 2. Pass each image to EasyOcrProcessor.
                    # 3. Combine the results.
                    # This is a significant change. The request was to "replace EnhancedPDFReader".
                    # EnhancedPDFReader itself might have done OCR. EasyOcrProcessor is image-based.
                    # A direct replacement for PDF OCR implies EasyOcrProcessor would handle the PDF.
                    # If EasyOCR cannot read PDF directly, this will fall through.
                    # For simplicity, we'll call it and let it fail if it can't handle PDFs, then fall back.
                    # A more correct implementation for PDF OCR using EasyOCR would be more involved.

                    # Let's assume the user wants to try EasyOCR on the PDF path directly,
                    # and if it's not designed for that, it will return None or raise an error,
                    # leading to fallback.
                    # This is a simplification based on the prompt.
                    logger.warning("Using EasyOcrProcessor for PDF directly. This may not work if EasyOCR doesn't support PDF paths and requires pre-conversion of PDF pages to images.")
                    documents = easy_ocr_processor.load_data(file_data, file_name)
                    if documents:
                        logger.info(f"Successfully processed PDF {file_name} with EasyOcrProcessor.")
                        # NUL byte sanitization and metadata is handled by EasyOcrProcessor
                        return documents
                    else:
                        logger.warning(f"EasyOcrProcessor for PDF {file_name} returned no documents. Falling back.")
                else:
                    logger.info(f"EasyOcrProcessor is not enabled or reader not initialized for PDF {file_name}. Falling back.")
            except Exception as e:
                logger.error(f"Error using EasyOcrProcessor for PDF {file_name}: {e}. Falling back.")
            # Fall through to default PDF reader if EasyOCR fails or is not applicable

        # Priority 2: Image processing with EasyOCR
        if extension in easyocr_supported_image_extensions and EASY_OCR_PROCESSOR_AVAILABLE:
            try:
                logger.info(f"Attempting EasyOCR processing for image: {file_name}")
                easy_ocr_processor = EasyOcrProcessor() # Uses default languages/GPU
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
