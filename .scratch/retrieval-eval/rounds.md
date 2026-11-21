# Retrieval eval: round log

Unscoped (cross-tender) search is not evaluated: every golden is run scoped to its own tender.

## Dataset generation

### Chosen tenders

Five tenders are INDEXED. Four are used:

| Tender ID | Org | Buyer / subject | Files fed to `deepeval generate` | Why |
| --- | --- | --- | --- | --- |
| 1039442 | d4q | ONEE Branche Eau, station rehabilitation (KfW-funded works) | `PASS2/AVIS AR 080-2026.docx`, `PASS2/RCDP Travaux KFW (V4 - Avril 2021).docx` | National utility, works contract, long regulatory docx; Arabic notice |
| 1040088 | h5r | Commune de Settat, deratisation products | `DAO PR ETUDE/CPS RATICIDES 2026.pdf`, `DAO PR ETUDE/RC raticides 2026.pdf` | Municipality, supplies, PDF-only DCE |
| 1037536 | m8x | Région Guelmim-Oued Noun, architecture competition | `Avis Conc Archi N°  06-2026.pdf` | Regional council, services competition; bilingual PDF notice with Arabic chunks |
| 1038425 | q9t | Centre hospitalier provincial de Khénifra, catering | `.../CPS FINAL RESTAURATION  AO 09-2026.docx`, `.../RC FINAL RESTAURATION AO 09-2026 Rectif.docx` | Ministry of Health, services, docx CPS + RC |

Excluded: 1036587 (g3h) has only 6 stored chunks, all from blank forms (acte d'engagement, déclaration sur l'honneur).

Only files with stored chunks are used, so each golden can be mapped to a chunk. DeepEval's docs loader reads only `.pdf`, `.docx`, `.txt` and `.md`, so `.doc`, `.xls` and `.xlsm` files are out anyway.

Arabic content exists: d4q's Arabic notice and m8x's notice. Each one is its own source document, so Arabic goldens are expected.

### Generation

Command (per tender, output tagged with the tender afterwards):

```
uv run --with langchain-community --with langchain-text-splitters --with chromadb \
  --with docx2txt --with pypdf --with tiktoken \
  deepeval generate --method docs --variation single-turn --documents <file>... \
  --model gpt-4o-mini --max-contexts-per-document 3 --max-goldens-per-context 2 --cost-tracking \
  --scenario/--task/--input-format/--expected-output-format  (French operator, Arabic when the passage is Arabic)
```

7 documents × 3 contexts × 2 goldens = up to 42 goldens.

Status: **blocked**. The OpenAI account returned `insufficient_quota` / `credit_balance_exhausted`, so no goldens were generated and no cost has been incurred.

Next steps and options (fund OpenAI / Gemini + Ollama / Gemini + contexts): see the Comments section of `issues/01-generate-golden-dataset.md`.
