"""
PDF processing service for text extraction and chunking
Handles PDF upload, text extraction, and intelligent chunking
"""
import PyPDF2
import pdfplumber
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
from pathlib import Path
from typing import List, Dict, Tuple
import logging
import hashlib
from datetime import datetime
from app.models.schemas import DocumentChunk
from app.utils.text_processing import chunk_text, clean_text
from app.core.config import settings

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    PDF processing with text extraction and intelligent chunking

    Considerations for chunking:
    1. Maintain semantic coherence: Split by paragraphs first, then sentences
    2. Overlap between chunks: Ensures context continuity for better retrieval
    3. Preserve metadata: Track page numbers, document source
    4. Handle various PDF formats: Use multiple extraction methods
    5. Clean extracted text: Remove artifacts, normalize whitespace
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """
        Initialize PDF processor

        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def process_pdf(
        self,
        file_path: Path,
        filename: str = None
    ) -> Tuple[List[DocumentChunk], Dict]:
        """
        Process a PDF file and extract chunks

        Args:
            file_path: Path to PDF file
            filename: Original filename (optional)

        Returns:
            Tuple of (list of chunks, metadata dict)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        filename = filename or file_path.name
        logger.info(f"Processing PDF: {filename}")

        # Extract text from PDF
        pages_text = self._extract_text(file_path)

        if not pages_text:
            logger.warning(f"No text extracted from {filename}")
            return [], {}

        # Generate document ID
        doc_id = self._generate_document_id(filename)

        # Create chunks from extracted text
        chunks = self._create_chunks(
            pages_text=pages_text,
            document_id=doc_id,
            document_name=filename
        )

        # Metadata
        metadata = {
            'document_id': doc_id,
            'filename': filename,
            'total_pages': len(pages_text),
            'total_chunks': len(chunks),
            'processed_at': datetime.now().isoformat(),
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap
        }

        logger.info(
            f"Processed {filename}: {len(pages_text)} pages, {len(chunks)} chunks"
        )

        return chunks, metadata

    def _extract_text(self, file_path: Path) -> Dict[int, str]:
        """
        Extract text from PDF using multiple methods for robustness

        Priority: PyMuPDF (fastest) > pdfplumber (best for tables) > PyPDF2 (fallback)

        Args:
            file_path: Path to PDF file

        Returns:
            Dictionary mapping page numbers to text content
        """
        pages_text = {}

        # Try PyMuPDF first (fastest and most reliable)
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(str(file_path))
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    if text and text.strip():
                        pages_text[page_num + 1] = clean_text(text)

                doc.close()

                if pages_text:
                    logger.debug(f"Extracted text using PyMuPDF: {len(pages_text)} pages")
                    return pages_text

            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {e}")

        # Try pdfplumber (better for tables, complex layouts)
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        pages_text[page_num] = clean_text(text)

            if pages_text:
                logger.debug(f"Extracted text using pdfplumber: {len(pages_text)} pages")
                return pages_text

        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")

        # Fallback to PyPDF2
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()

                    if text and text.strip():
                        pages_text[page_num + 1] = clean_text(text)

            logger.debug(f"Extracted text using PyPDF2: {len(pages_text)} pages")

        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            raise

        return pages_text

    def _create_chunks(
        self,
        pages_text: Dict[int, str],
        document_id: str,
        document_name: str
    ) -> List[DocumentChunk]:
        """
        Create chunks from extracted text with metadata

        Args:
            pages_text: Dictionary of page number to text
            document_id: Unique document identifier
            document_name: Document filename

        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        chunk_index = 0

        for page_num, text in sorted(pages_text.items()):
            if not text or not text.strip():
                continue

            # Chunk the page text
            page_chunks = chunk_text(
                text=text,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )

            # Create DocumentChunk objects
            for chunk_text_content in page_chunks:
                if not chunk_text_content.strip():
                    continue

                chunk = DocumentChunk(
                    chunk_id=f"{document_id}_chunk_{chunk_index}",
                    document_id=document_id,
                    document_name=document_name,
                    text=chunk_text_content,
                    page_number=page_num,
                    chunk_index=chunk_index,
                    metadata={
                        'page_number': page_num,
                        'chunk_size': len(chunk_text_content),
                        'total_pages': len(pages_text)
                    }
                )

                chunks.append(chunk)
                chunk_index += 1

        return chunks

    def _generate_document_id(self, filename: str) -> str:
        """
        Generate a unique document ID based on filename and timestamp

        Args:
            filename: Document filename

        Returns:
            Unique document ID
        """
        # Combine filename with timestamp for uniqueness
        content = f"{filename}_{datetime.now().isoformat()}"
        doc_id = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"doc_{doc_id}"

    def process_multiple_pdfs(
        self,
        file_paths: List[Path]
    ) -> Tuple[List[DocumentChunk], List[Dict]]:
        """
        Process multiple PDF files

        Args:
            file_paths: List of PDF file paths

        Returns:
            Tuple of (all chunks, list of metadata dicts)
        """
        all_chunks = []
        all_metadata = []

        for file_path in file_paths:
            try:
                chunks, metadata = self.process_pdf(file_path)
                all_chunks.extend(chunks)
                all_metadata.append(metadata)

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                all_metadata.append({
                    'filename': file_path.name,
                    'error': str(e),
                    'success': False
                })

        return all_chunks, all_metadata
