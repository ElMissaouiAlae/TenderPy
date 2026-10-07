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
from botocore.exceptions import ClientError

from core.models import Tender
from indexing.chunker import DoclingChunker
from indexing.embedder import SentenceTransformerEmbedder
from indexing.models import DceFile, DceFileStatus
from indexing.pipeline import IndexingPipeline
from persistence.config import Settings
from persistence.exceptions import RepositoryError
from persistence.file_storage import S3DocumentStorage
from persistence.models import INDEXABLE_LAST_STATUSES, TenderStatus

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
        if Key not in self._objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "GetObject"
            )
        return {"Body": BytesIO(self._objects[Key])}

    def put(self, key: str, content: bytes) -> None:
        self._objects[key] = content


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
    """Tenders in record order; each entry is (tender, status) or (tender, FAILED, last_status)."""

    def __init__(self, tenders: list[tuple]) -> None:
        self._tenders = [tender for tender, *_ in tenders]
        self.statuses = {self._key(tender): status for tender, status, *_ in tenders}
        self.last_statuses = {
            self._key(tender): last[0] if last else None for tender, _, *last in tenders
        }
        self.history = {self._key(tender): [] for tender, *_ in tenders}

    @staticmethod
    def _key(tender: Tender) -> tuple:
        return tender.tender_id, tender.organization_acronym

    def find_for_indexing(self, limit: int) -> list[Tender]:
        matching = [t for t in self._tenders if self._indexable(self._key(t))]
        return matching[:limit]

    def _indexable(self, key: tuple) -> bool:
        status = self.statuses[key]
        return status == TenderStatus.UPLOADED or (
            status == TenderStatus.FAILED and self.last_statuses[key] in INDEXABLE_LAST_STATUSES
        )

    def update_status(self, tender_id, organization_acronym, status, last_status=None):
        key = (tender_id, organization_acronym)
        self.statuses[key] = status
        self.last_statuses[key] = last_status
        self.history[key].append(status)


class FailingTenderRepository(InMemoryTenderRepository):
    """Raises like a lost database connection on every status update for one tender."""

    def __init__(self, tenders: list[tuple], failing_key: tuple) -> None:
        super().__init__(tenders)
        self._failing_key = failing_key

    def update_status(self, tender_id, organization_acronym, status, last_status=None):
        if (tender_id, organization_acronym) == self._failing_key:
            raise RepositoryError("Failed to update tender status: connection lost")
        super().update_status(tender_id, organization_acronym, status, last_status)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self.files: dict[tuple, list[DceFile]] = {}

    def replace_tender_files(self, tender: Tender, dce_files: Sequence[DceFile]) -> None:
        self.files[(tender.tender_id, tender.organization_acronym)] = list(dce_files)

    def search(self, query_embedding, embedding_model, limit=10):
        raise NotImplementedError


class FailingVectorStore(InMemoryVectorStore):
    """Rejects the write for one tender, as a failed transaction would: nothing is stored."""

    def __init__(self, failing_key: tuple) -> None:
        super().__init__()
        self._failing_key = failing_key

    def replace_tender_files(self, tender: Tender, dce_files: Sequence[DceFile]) -> None:
        if (tender.tender_id, tender.organization_acronym) == self._failing_key:
            raise RepositoryError("Failed to store DCE files: connection lost")
        super().replace_tender_files(tender, dce_files)


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


def build_pipeline(
    tenders, objects, work_root, chunker, embedder=None, repository=None, vector_store=None
):
    repository = repository or InMemoryTenderRepository(tenders)
    s3_client = FakeS3Client(objects, work_root)
    storage = S3DocumentStorage(
        Settings(database_url="postgresql://unused", s3_bucket_name="bucket"), s3_client
    )
    vector_store = vector_store or InMemoryVectorStore()
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


SUCCESS_HISTORY = [
    TenderStatus.CHUNKING,
    TenderStatus.CHUNKED,
    TenderStatus.EMBEDDING,
    TenderStatus.INDEXED,
]


def two_tenders():
    return [
        (Tender(tender_id="T1", organization_acronym="ORG"), TenderStatus.UPLOADED),
        (Tender(tender_id="T2", organization_acronym="ORG"), TenderStatus.UPLOADED),
    ]


def test_s3_failure_fails_the_tender_with_last_status_uploaded_and_the_batch_continues(
    work_root, chunker
):
    pipeline, repository, vector_store, _ = build_pipeline(
        two_tenders(), {"T2_ORG.zip": single_pdf_archive()}, work_root, chunker
    )

    pipeline.run(limit=2)

    assert repository.statuses[("T1", "ORG")] == TenderStatus.FAILED
    assert repository.last_statuses[("T1", "ORG")] == TenderStatus.UPLOADED
    assert ("T1", "ORG") not in vector_store.files
    assert repository.history[("T2", "ORG")] == SUCCESS_HISTORY
    assert repository.last_statuses[("T2", "ORG")] is None
    assert list(work_root.iterdir()) == []


def test_unreadable_top_level_archive_fails_the_tender_with_last_status_uploaded(
    work_root, chunker
):
    pipeline, repository, vector_store, _ = build_pipeline(
        two_tenders(),
        {"T1_ORG.zip": b"this is not a zip", "T2_ORG.zip": single_pdf_archive()},
        work_root,
        chunker,
    )

    pipeline.run(limit=2)

    assert repository.statuses[("T1", "ORG")] == TenderStatus.FAILED
    assert repository.last_statuses[("T1", "ORG")] == TenderStatus.UPLOADED
    assert ("T1", "ORG") not in vector_store.files
    assert repository.statuses[("T2", "ORG")] == TenderStatus.INDEXED
    assert list(work_root.iterdir()) == []


def test_database_failure_while_storing_fails_the_tender_with_last_status_chunked(
    work_root, chunker
):
    archive = single_pdf_archive()
    pipeline, repository, vector_store, _ = build_pipeline(
        two_tenders(),
        {"T1_ORG.zip": archive, "T2_ORG.zip": archive},
        work_root,
        chunker,
        vector_store=FailingVectorStore(failing_key=("T1", "ORG")),
    )

    pipeline.run(limit=2)

    assert repository.history[("T1", "ORG")] == [
        TenderStatus.CHUNKING,
        TenderStatus.CHUNKED,
        TenderStatus.EMBEDDING,
        TenderStatus.FAILED,
    ]
    assert repository.last_statuses[("T1", "ORG")] == TenderStatus.CHUNKED
    assert ("T1", "ORG") not in vector_store.files
    assert repository.statuses[("T2", "ORG")] == TenderStatus.INDEXED
    assert list(work_root.iterdir()) == []


def test_tender_whose_status_cannot_be_written_does_not_stop_the_batch(work_root, chunker):
    archive = single_pdf_archive()
    tenders = two_tenders()
    pipeline, repository, _, _ = build_pipeline(
        tenders,
        {"T1_ORG.zip": archive, "T2_ORG.zip": archive},
        work_root,
        chunker,
        repository=FailingTenderRepository(tenders, failing_key=("T1", "ORG")),
    )

    pipeline.run(limit=2)

    assert repository.statuses[("T1", "ORG")] == TenderStatus.UPLOADED
    assert repository.statuses[("T2", "ORG")] == TenderStatus.INDEXED
    assert list(work_root.iterdir()) == []


def test_failed_tender_is_retried_on_the_next_run_and_its_last_status_cleared(
    work_root, chunker
):
    pipeline, repository, _, s3_client = build_pipeline(
        [(Tender(tender_id="T1", organization_acronym="ORG"), TenderStatus.UPLOADED)],
        {},
        work_root,
        chunker,
    )
    pipeline.run(limit=1)
    assert repository.last_statuses[("T1", "ORG")] == TenderStatus.UPLOADED

    # The archive is back in S3 by the next run.
    s3_client.put("T1_ORG.zip", single_pdf_archive())
    repository.history[("T1", "ORG")].clear()
    pipeline.run(limit=1)

    assert repository.history[("T1", "ORG")] == SUCCESS_HISTORY
    assert repository.last_statuses[("T1", "ORG")] is None


@pytest.mark.parametrize(
    "last_status",
    [
        TenderStatus.UPLOADED,
        TenderStatus.CHUNKING,
        TenderStatus.CHUNKED,
        TenderStatus.EMBEDDING,
    ],
)
def test_failed_tender_from_upload_onwards_is_eligible_and_restarts_from_the_download(
    work_root, chunker, last_status
):
    pipeline, repository, vector_store, _ = build_pipeline(
        [(Tender(tender_id="T1", organization_acronym="ORG"), TenderStatus.FAILED, last_status)],
        {"T1_ORG.zip": single_pdf_archive()},
        work_root,
        chunker,
    )

    pipeline.run(limit=1)

    assert repository.history[("T1", "ORG")] == SUCCESS_HISTORY
    assert repository.last_statuses[("T1", "ORG")] is None
    assert vector_store.files[("T1", "ORG")]


def test_failed_tenders_before_upload_are_not_picked_and_eligible_ones_share_the_limit(
    work_root, chunker
):
    tenders = [
        (Tender(tender_id="A", organization_acronym="ORG"), TenderStatus.FAILED,
         TenderStatus.DOWNLOADED),
        (Tender(tender_id="B", organization_acronym="ORG"), TenderStatus.FAILED,
         TenderStatus.CHUNKED),
        (Tender(tender_id="C", organization_acronym="ORG"), TenderStatus.UPLOADED),
        (Tender(tender_id="D", organization_acronym="ORG"), TenderStatus.UPLOADED),
    ]
    archive = single_pdf_archive()
    pipeline, repository, vector_store, _ = build_pipeline(
        tenders, {f"{key}_ORG.zip": archive for key in "ABCD"}, work_root, chunker
    )

    pipeline.run(limit=2)

    assert list(vector_store.files) == [("B", "ORG"), ("C", "ORG")]
    assert repository.history[("A", "ORG")] == []
    assert repository.last_statuses[("A", "ORG")] == TenderStatus.DOWNLOADED
    assert repository.statuses[("D", "ORG")] == TenderStatus.UPLOADED
