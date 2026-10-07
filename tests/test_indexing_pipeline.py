"""Tests for indexing.pipeline, driven through IndexingPipeline.run(limit).

Docling runs for real on a tiny PDF fixture; S3, the embedder, the vector
store and the tender repository are fakes.
"""

import hashlib
import zipfile
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

import pytest

from core.models import Tender
from indexing.chunker import DoclingChunker
from indexing.embedder import SentenceTransformerEmbedder
from indexing.models import DceFile, DceFileStatus
from indexing.pipeline import IndexingPipeline
from persistence.config import Settings
from persistence.file_storage import S3DocumentStorage
from persistence.models import TenderStatus

FIXTURES = Path(__file__).parent / "fixtures" / "indexing"
EMBEDDING_DIM = Settings(database_url="postgresql://unused").embedding_dim


class FakeS3Client:
    """S3 client serving zip archives by key, noting the work root's contents on each read."""

    def __init__(self, objects: dict[str, bytes], work_root: Path) -> None:
        self._objects = objects
        self._work_root = work_root
        self.work_root_listings: list[list[str]] = []

    def get_object(self, Bucket: str, Key: str) -> dict:
        self.work_root_listings.append(sorted(p.name for p in self._work_root.iterdir()))
        return {"Body": BytesIO(self._objects[Key])}


class FakeEmbedder:
    """Deterministic embedder returning 1024-dim vectors derived from the text."""

    model_name = "fake-embedder"

    def embed(self, texts):
        vectors = []
        for text in texts:
            seed = hashlib.sha256(text.encode()).digest()
            vectors.append([seed[i % len(seed)] / 255 for i in range(EMBEDDING_DIM)])
        return vectors


class InMemoryTenderRepository:
    def __init__(self, tenders: list[tuple[Tender, TenderStatus]]) -> None:
        self._tenders = [tender for tender, _ in tenders]
        self.statuses = {self._key(tender): status for tender, status in tenders}
        self.history = {self._key(tender): [] for tender, _ in tenders}

    @staticmethod
    def _key(tender: Tender) -> tuple:
        return tender.tender_id, tender.organization_acronym

    def find_by_status(self, status: TenderStatus, limit: int) -> list[Tender]:
        matching = [t for t in self._tenders if self.statuses[self._key(t)] == status]
        return matching[:limit]

    def update_status(self, tender_id, organization_acronym, status, last_status=None):
        self.statuses[(tender_id, organization_acronym)] = status
        self.history[(tender_id, organization_acronym)].append(status)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self.files: dict[tuple, list[DceFile]] = {}

    def replace_tender_files(self, tender: Tender, dce_files: Sequence[DceFile]) -> None:
        self.files[(tender.tender_id, tender.organization_acronym)] = list(dce_files)

    def search(self, query_embedding, embedding_model, limit=10):
        raise NotImplementedError


def zip_bytes(members: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buffer.getvalue()


@pytest.fixture(scope="module")
def chunker():
    return DoclingChunker(tokenizer_model="BAAI/bge-m3", max_tokens=512)


@pytest.fixture
def work_root(tmp_path):
    root = tmp_path / "work"
    root.mkdir()
    return root


def build_pipeline(tenders, objects, work_root, chunker, embedder=None):
    repository = InMemoryTenderRepository(tenders)
    s3_client = FakeS3Client(objects, work_root)
    storage = S3DocumentStorage(
        Settings(database_url="postgresql://unused", s3_bucket_name="bucket"), s3_client
    )
    vector_store = InMemoryVectorStore()
    pipeline = IndexingPipeline(
        repository=repository,
        document_storage=storage,
        chunker=chunker,
        embedder=embedder or FakeEmbedder(),
        vector_store=vector_store,
        work_root=work_root,
    )
    return pipeline, repository, vector_store, s3_client


def single_pdf_archive() -> bytes:
    return zip_bytes({"CPS.pdf": (FIXTURES / "cps.pdf").read_bytes()})


def test_uploaded_tender_with_a_single_pdf_reaches_indexed(work_root, chunker):
    tender = Tender(tender_id="T1", organization_acronym="ORG")
    pipeline, repository, vector_store, _ = build_pipeline(
        [(tender, TenderStatus.UPLOADED)],
        {"T1_ORG.zip": single_pdf_archive()},
        work_root,
        chunker,
    )

    pipeline.run(limit=5)

    assert repository.history[("T1", "ORG")] == [
        TenderStatus.CHUNKING,
        TenderStatus.CHUNKED,
        TenderStatus.EMBEDDING,
        TenderStatus.INDEXED,
    ]
    [dce_file] = vector_store.files[("T1", "ORG")]
    assert dce_file.path == "CPS.pdf"
    assert dce_file.file_type == "pdf"
    assert dce_file.status == DceFileStatus.CHUNKED
    assert dce_file.reason is None


def test_chunks_carry_citation_metadata_and_embeddings(work_root, chunker):
    tender = Tender(tender_id="T1", organization_acronym="ORG")
    pipeline, _, vector_store, _ = build_pipeline(
        [(tender, TenderStatus.UPLOADED)],
        {"T1_ORG.zip": single_pdf_archive()},
        work_root,
        chunker,
    )

    pipeline.run(limit=1)

    [dce_file] = vector_store.files[("T1", "ORG")]
    chunks = dce_file.chunks
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert len(chunks) == 2
    first, second = chunks
    assert "fourniture de materiel informatique" in first.text
    assert first.page_numbers == (1,)
    assert first.headings == ("Article 1 - Objet du marche",)
    assert "paiement" in second.text
    assert second.page_numbers == (2,)
    assert second.headings == ("Article 2 - Prix et paiement",)
    for chunk in chunks:
        assert chunk.embedding_model == "fake-embedder"
        assert len(chunk.embedding) == EMBEDDING_DIM


def test_limit_is_respected_and_only_uploaded_tenders_are_picked_in_order(work_root, chunker):
    tenders = [
        (Tender(tender_id="A", organization_acronym="ORG"), TenderStatus.DISCOVERED),
        (Tender(tender_id="B", organization_acronym="ORG"), TenderStatus.UPLOADED),
        (Tender(tender_id="C", organization_acronym="ORG"), TenderStatus.INDEXED),
        (Tender(tender_id="D", organization_acronym="ORG"), TenderStatus.UPLOADED),
        (Tender(tender_id="E", organization_acronym="ORG"), TenderStatus.UPLOADED),
    ]
    archive = single_pdf_archive()
    pipeline, repository, vector_store, _ = build_pipeline(
        tenders,
        {f"{key}_ORG.zip": archive for key in "ABCDE"},
        work_root,
        chunker,
    )

    pipeline.run(limit=2)

    assert list(vector_store.files) == [("B", "ORG"), ("D", "ORG")]
    assert repository.statuses[("B", "ORG")] == TenderStatus.INDEXED
    assert repository.statuses[("D", "ORG")] == TenderStatus.INDEXED
    assert repository.statuses[("E", "ORG")] == TenderStatus.UPLOADED
    assert repository.statuses[("A", "ORG")] == TenderStatus.DISCOVERED
    assert repository.history[("C", "ORG")] == []


def test_temp_folder_exists_only_while_its_tender_is_processed(work_root, chunker):
    tenders = [
        (Tender(tender_id="T1", organization_acronym="ORG"), TenderStatus.UPLOADED),
        (Tender(tender_id="T2", organization_acronym="ORG"), TenderStatus.UPLOADED),
    ]
    archive = single_pdf_archive()
    pipeline, _, _, s3_client = build_pipeline(
        tenders,
        {"T1_ORG.zip": archive, "T2_ORG.zip": archive},
        work_root,
        chunker,
    )

    pipeline.run(limit=2)

    # One per-tender folder while each tender is processed, never two at once.
    assert [len(listing) for listing in s3_client.work_root_listings] == [1, 1]
    assert s3_client.work_root_listings[0] != s3_client.work_root_listings[1]
    assert list(work_root.iterdir()) == []


@pytest.mark.slow
def test_real_bge_m3_produces_1024_dim_vectors_and_is_recorded_on_chunks(work_root, chunker):
    settings = Settings(database_url="postgresql://unused")
    embedder = SentenceTransformerEmbedder(settings.embedding_model, settings.embedding_dim)
    tender = Tender(tender_id="T1", organization_acronym="ORG")
    pipeline, _, vector_store, _ = build_pipeline(
        [(tender, TenderStatus.UPLOADED)],
        {"T1_ORG.zip": single_pdf_archive()},
        work_root,
        chunker,
        embedder=embedder,
    )

    pipeline.run(limit=1)

    [dce_file] = vector_store.files[("T1", "ORG")]
    assert dce_file.chunks
    for chunk in dce_file.chunks:
        assert chunk.embedding_model == "BAAI/bge-m3"
        assert len(chunk.embedding) == 1024


def run_single_tender(archive: bytes, work_root, chunker):
    tender = Tender(tender_id="T1", organization_acronym="ORG")
    pipeline, repository, vector_store, _ = build_pipeline(
        [(tender, TenderStatus.UPLOADED)], {"T1_ORG.zip": archive}, work_root, chunker
    )
    pipeline.run(limit=1)
    files = {dce_file.path: dce_file for dce_file in vector_store.files[("T1", "ORG")]}
    return repository.statuses[("T1", "ORG")], files


def test_nested_zips_are_extracted_recursively_with_their_nesting_in_the_path(
    work_root, chunker
):
    pdf = (FIXTURES / "cps.pdf").read_bytes()
    archive = zip_bytes(
        {
            "CPS.pdf": pdf,
            "annexes.zip": zip_bytes(
                {"RC.pdf": pdf, "lots/deep.zip": zip_bytes({"BPU.pdf": pdf})}
            ),
        }
    )

    status, files = run_single_tender(archive, work_root, chunker)

    assert status == TenderStatus.INDEXED
    assert list(files) == [
        "CPS.pdf",
        "annexes.zip/RC.pdf",
        "annexes.zip/lots/deep.zip/BPU.pdf",
    ]
    for dce_file in files.values():
        assert dce_file.status == DceFileStatus.CHUNKED
        assert dce_file.file_type == "pdf"
        assert dce_file.chunks


def test_unsupported_dce_file_is_skipped_with_a_reason_and_no_chunks(work_root, chunker):
    archive = zip_bytes({"plans/plan.dwg": b"AC1027\x00\x00binary drawing\x01\x02"})

    status, files = run_single_tender(archive, work_root, chunker)

    assert status == TenderStatus.INDEXED
    dce_file = files["plans/plan.dwg"]
    assert dce_file.status == DceFileStatus.SKIPPED
    assert dce_file.file_type == "dwg"
    assert dce_file.reason
    assert dce_file.chunks == []


def test_image_dce_file_is_skipped_since_ocr_is_off(work_root, chunker):
    archive = zip_bytes({"signature.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 20})

    _, files = run_single_tender(archive, work_root, chunker)

    assert files["signature.png"].status == DceFileStatus.SKIPPED


def test_corrupt_pdf_is_failed_with_the_error_and_no_chunks(work_root, chunker):
    archive = zip_bytes({"CCAP.pdf": b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog\ntruncated"})

    status, files = run_single_tender(archive, work_root, chunker)

    assert status == TenderStatus.INDEXED
    dce_file = files["CCAP.pdf"]
    assert dce_file.status == DceFileStatus.FAILED
    assert dce_file.reason
    assert dce_file.chunks == []


def test_corrupt_nested_zip_is_failed_without_failing_the_tender(work_root, chunker):
    archive = zip_bytes(
        {"CPS.pdf": (FIXTURES / "cps.pdf").read_bytes(), "annexes.zip": b"not a zip"}
    )

    status, files = run_single_tender(archive, work_root, chunker)

    assert status == TenderStatus.INDEXED
    assert files["CPS.pdf"].status == DceFileStatus.CHUNKED
    nested = files["annexes.zip"]
    assert nested.status == DceFileStatus.FAILED
    assert nested.file_type == "zip"
    assert nested.reason
    assert nested.chunks == []


def test_tender_with_good_skipped_and_failed_files_reaches_indexed(work_root, chunker):
    archive = zip_bytes(
        {
            "CPS.pdf": (FIXTURES / "cps.pdf").read_bytes(),
            "plan.dwg": b"AC1027\x00\x00binary drawing\x01\x02",
            "CCAP.pdf": b"%PDF-1.4\ntruncated",
        }
    )

    tender = Tender(tender_id="T1", organization_acronym="ORG")
    pipeline, repository, vector_store, _ = build_pipeline(
        [(tender, TenderStatus.UPLOADED)], {"T1_ORG.zip": archive}, work_root, chunker
    )
    pipeline.run(limit=1)

    assert repository.history[("T1", "ORG")] == [
        TenderStatus.CHUNKING,
        TenderStatus.CHUNKED,
        TenderStatus.EMBEDDING,
        TenderStatus.INDEXED,
    ]
    files = {f.path: f for f in vector_store.files[("T1", "ORG")]}
    assert {path: f.status for path, f in files.items()} == {
        "CPS.pdf": DceFileStatus.CHUNKED,
        "plan.dwg": DceFileStatus.SKIPPED,
        "CCAP.pdf": DceFileStatus.FAILED,
    }
    assert len(files["CPS.pdf"].chunks) == 2
    assert list(work_root.iterdir()) == []


def corrupt_member(archive: bytes, name: str) -> bytes:
    """Flip a byte of a stored member's data so reading it fails its CRC check."""
    with zipfile.ZipFile(BytesIO(archive)) as zip_file:
        info = zip_file.getinfo(name)
    data_start = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
    corrupted = bytearray(archive)
    corrupted[data_start] ^= 0xFF
    return bytes(corrupted)


def test_unreadable_members_are_failed_while_their_siblings_are_still_chunked(
    work_root, chunker
):
    pdf = (FIXTURES / "cps.pdf").read_bytes()
    annexes = corrupt_member(zip_bytes({"RC.pdf": pdf, "BPU.pdf": pdf}), "BPU.pdf")
    archive = corrupt_member(
        zip_bytes({"CPS.pdf": pdf, "CCAP.pdf": pdf, "annexes.zip": annexes}), "CCAP.pdf"
    )

    status, files = run_single_tender(archive, work_root, chunker)

    assert status == TenderStatus.INDEXED
    assert {path: f.status for path, f in files.items()} == {
        "CPS.pdf": DceFileStatus.CHUNKED,
        "CCAP.pdf": DceFileStatus.FAILED,
        "annexes.zip/RC.pdf": DceFileStatus.CHUNKED,
        "annexes.zip/BPU.pdf": DceFileStatus.FAILED,
    }
    assert files["CCAP.pdf"].reason
    assert files["annexes.zip/BPU.pdf"].reason
