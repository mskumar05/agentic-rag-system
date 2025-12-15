"""
Ingestion API endpoints for PDF upload and processing
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import logging
from pathlib import Path
import shutil
from app.models.schemas import IngestionResponse
from app.services.pdf_processor import PDFProcessor
from app.core.vector_store import get_vector_store
from app.core.embeddings import get_embedding_generator
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/upload", response_model=IngestionResponse)
async def upload_pdfs(files: List[UploadFile] = File(...)):
    """
    Upload and process one or more PDF files

    Args:
        files: List of PDF files to upload

    Returns:
        Ingestion response with processing statistics
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    logger.info(f"Received {len(files)} files for ingestion")

    # Validate files
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} is not a PDF"
            )

    try:
        # Save uploaded files
        saved_paths = []

        for file in files:
            file_path = settings.UPLOADS_DIR / file.filename

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_paths.append(file_path)
            logger.info(f"Saved file: {file.filename}")

        # Process PDFs
        pdf_processor = PDFProcessor()

        all_chunks, all_metadata = pdf_processor.process_multiple_pdfs(saved_paths)

        if not all_chunks:
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from the PDFs"
            )

        logger.info(f"Extracted {len(all_chunks)} chunks from {len(files)} files")

        # Generate embeddings
        embedding_gen = get_embedding_generator()

        chunk_texts = [chunk.text for chunk in all_chunks]
        embeddings = embedding_gen.embed_batch(chunk_texts)

        logger.info(f"Generated embeddings with shape: {embeddings.shape}")

        # Store in vector database
        vector_store = get_vector_store()
        vector_store.add_documents(all_chunks, embeddings)

        # Save to disk
        vector_store.save()

        logger.info("Successfully stored documents in vector database")

        # Collect document IDs
        document_ids = list(set(chunk.document_id for chunk in all_chunks))

        return IngestionResponse(
            success=True,
            message=f"Successfully processed {len(files)} PDF(s)",
            documents_processed=len(files),
            total_chunks=len(all_chunks),
            document_ids=document_ids
        )

    except Exception as e:
        logger.error(f"Error during ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_ingestion_stats():
    """
    Get statistics about ingested documents

    Returns:
        Statistics dictionary
    """
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_documents():
    """
    Clear all documents from the vector store

    Returns:
        Success message
    """
    try:
        vector_store = get_vector_store()
        vector_store.clear()
        vector_store.save()

        logger.info("Cleared all documents from vector store")

        return {
            "success": True,
            "message": "All documents cleared successfully"
        }

    except Exception as e:
        logger.error(f"Error clearing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
