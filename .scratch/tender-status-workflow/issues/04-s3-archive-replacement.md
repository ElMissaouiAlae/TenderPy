Status: needs-triage

# Handle DCE archive replacement in S3

If a tender's DCE archive changes after it has already been uploaded (the
source platform re-publishes an updated zip for the same
`tender_id`/`organization_acronym`), we currently have no plan for detecting
this or for replacing the stale object in S3. Left unhandled, we'd either
silently keep serving the old archive or accumulate orphaned versions.

Raised during design of the tender status workflow (see `CONTEXT.md` for the
`TenderStatus` / `last_status` model this sits alongside). Not in scope for
that change — flagged here so it isn't lost.

Open questions for whoever picks this up:
- How do we detect that a tender's archive changed (hash comparison? re-download
  and diff? platform-provided version/timestamp?)
- Overwrite in place vs. keep versions (S3 versioning) vs. explicit delete-then-put
- Does this need a new status, or is it orthogonal to the `TenderStatus` pipeline

## Comments
