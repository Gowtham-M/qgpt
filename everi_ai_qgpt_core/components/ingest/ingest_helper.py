import logging
from pathlib import Path

from llama_index.core.readers import StringIterableReader
from llama_index.core.readers.base import BaseReader
from llama_index.core.readers.json import JSONReader
from llama_index.core.schema import Document

logger = logging.getLogger(__name__)

# Try to import OCR processor
try:
    from everi_ai_qgpt_core.components.ingest.pdf_ocr_processor import EnhancedPDFReader
    OCR_AVAILABLE = True
    logger.info("PDF OCR processor available")
except ImportError as e:
    logger.warning(f"PDF OCR processor not available: {e}")
    OCR_AVAILABLE = False

# Try to import Ollama Image Processor
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
        global_doc_id = documents[0].doc_id  # Ensure single doc_id for PDFs
        for document in documents:
            document.metadata["file_name"] = file_name
            if Path(file_name).suffix == ".pdf":
                document.metadata["doc_id"] = global_doc_id  # Assign consistent doc_id for PDFs
        
        IngestionHelper._exclude_metadata(documents)
        return documents

    @staticmethod
    def _load_file_to_documents(file_name: str, file_data: Path) -> list[Document]:
        logger.debug("Transforming file_name=%s into documents", file_name)
        extension = Path(file_name).suffix.lower()
        
        # Special handling for PDFs with OCR
        if extension == ".pdf" and OCR_AVAILABLE:
            try:
                logger.info("Using enhanced PDF processor with OCR for %s", file_name)
                ocr_reader = EnhancedPDFReader(use_ocr=True)
                documents = ocr_reader.load_data(file_data)
                
                # Ensure consistent doc_id for PDFs
                if documents:
                    global_doc_id = documents[0].doc_id
                    for doc in documents:
                        doc.metadata["doc_id"] = global_doc_id
                        doc.metadata["file_name"] = file_name
                        # Sanitize NUL bytes
                        doc.text = doc.text.replace("\\u0000", "") # Corrected NUL byte replacement
                
                    return documents
            except Exception as e:
                logger.warning(f"OCR processing failed for PDF, falling back to regular processing: {e}")
                # Fall through to regular PDF processing by FILE_READER_CLS below

        # New: Special handling for images with OllamaImageProcessor
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
        
        # Regular file processing
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
            logger.debug("Merging multiple PDF pages into a single document")
            combined_text = "\n".join(doc.text for doc in documents)
            documents = [Document(text=combined_text, metadata={"file_name": file_name})]

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
