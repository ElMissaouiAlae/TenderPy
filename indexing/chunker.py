"""Split DCE files into chunks with Docling's hybrid chunker."""

from __future__ import annotations

from pathlib import Path

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.doc_chunk import DocChunk
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

from indexing.models import TextChunk

# Formats with no text to extract while OCR is off (images, scans of
# signatures) or that need speech models; Docling reports them as skipped.
_EXCLUDED_FORMATS = {InputFormat.IMAGE, InputFormat.AUDIO, InputFormat.VIDEO}


class UnsupportedFileError(Exception):
    """The DCE file's type is not one Docling chunks."""


class ChunkingError(Exception):
    """Docling could not convert a DCE file of a supported type."""


class DoclingChunker:
    """Convert a DCE file with Docling and split it into token-bounded chunks.

    Chunk size is measured with the embedding model's own tokenizer so every
    chunk fits the model. OCR is disabled: scanned PDFs yield no text for now.
    """

    def __init__(self, tokenizer_model: str, max_tokens: int = 512) -> None:
        """Build the Docling converter and chunker.

        Args:
            tokenizer_model: Hugging Face name of the embedding model whose
                tokenizer measures chunk size (e.g. "BAAI/bge-m3").
            max_tokens: Maximum tokens per chunk.
        """
        pdf_options = PdfPipelineOptions(do_ocr=False)
        self._converter = DocumentConverter(
            allowed_formats=[f for f in InputFormat if f not in _EXCLUDED_FORMATS],
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)},
        )
        tokenizer = HuggingFaceTokenizer(
            tokenizer=AutoTokenizer.from_pretrained(tokenizer_model),
            max_tokens=max_tokens,
        )
        self._chunker = HybridChunker(tokenizer=tokenizer)

    def chunk(self, path: Path) -> list[TextChunk]:
        """Convert the file at path and return its chunks in document order.

        Raises:
            UnsupportedFileError: if Docling does not handle the file's type.
            ChunkingError: if Docling fails to convert the file.
        """
        result = self._converter.convert(path, raises_on_error=False)
        errors = "; ".join(error.error_message for error in result.errors)
        if result.status == ConversionStatus.SKIPPED:
            raise UnsupportedFileError(f"Docling does not support {path.suffix or 'this'} files")
        if result.status not in (ConversionStatus.SUCCESS, ConversionStatus.PARTIAL_SUCCESS):
            raise ChunkingError(errors or f"Conversion ended with status {result.status.value}")
        document = result.document
        doc_chunks = [DocChunk.model_validate(chunk) for chunk in self._chunker.chunk(document)]
        return [
            TextChunk(
                index=index,
                text=chunk.text,
                embedding_text=self._chunker.contextualize(chunk),
                page_numbers=tuple(
                    sorted({prov.page_no for item in chunk.meta.doc_items for prov in item.prov})
                ),
                headings=tuple(chunk.meta.headings or ()),
            )
            for index, chunk in enumerate(doc_chunks)
        ]
