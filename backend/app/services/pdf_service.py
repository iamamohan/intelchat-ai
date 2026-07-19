import os
import uuid
import logging
from fastapi import HTTPException, status
import fitz
from app.models.response_models import PDFExtractionResponse, PDFPage

logger = logging.getLogger("app.services.pdf_service")

class PDFService:
    """Service responsible for extracting text from a PDF file using PyMuPDF."""

    def extract_text(self, file_path: str) -> PDFExtractionResponse:
        """Extract text from all pages of the PDF located at *file_path*.

        Returns a :class:`PDFExtractionResponse` containing filename, total pages, and a list of
        :class:`PDFPage` objects. Raises ``HTTPException`` with appropriate status codes for
        invalid, corrupted, empty, or unreadable PDFs.
        """
        # Open PDF safely
        try:
            doc = fitz.open(file_path)

            # Generate a unique document identifier for this upload
            document_id = str(uuid.uuid4())
            logger.debug(f"Generated document_id {document_id} for file {file_path}")

        except Exception as e:
            logger.error(f"Failed to open PDF '{file_path}': {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted PDF file."
            )

        try:
            total_pages = doc.page_count
            if total_pages == 0:
                logger.warning(f"Empty PDF file: '{file_path}'")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="PDF contains no pages."
                )

            pages: list[PDFPage] = []
            for i in range(total_pages):
                page = doc.load_page(i)
                text = page.get_text()
                pages.append(PDFPage(page_number=i + 1, text=text))

            logger.info(f"PDF extraction successful for '{file_path}'. Pages extracted: {total_pages}")
            return PDFExtractionResponse(
                success=True,
                filename=os.path.basename(file_path),
                document_id=document_id,
                total_pages=total_pages,
                pages=pages,
            )
        finally:
            doc.close()
            logger.debug(f"Closed PDF document '{file_path}'")
