# Changelog

All notable changes to the FinOps project are documented in this file.

## [Unreleased]

### Fixed
- Resolved `AttributeError` on sample data load: `app.py` now defensively filters file inputs before passing to ingestion (`hasattr(f, "getbuffer") or isinstance(f, (str, os.PathLike))`)
- Fixed test assertion errors: `tests/test_pipeline.py` and `tests/test_file_loading.py` expected stale row counts (12 per provider); updated to match actual sample data (360 per provider, 720 combined)
- Fixed `tests/test_file_loading.py` to use real sample data paths instead of non-existent fake paths

### Changed
- `runtime.txt` files converted from CRLF to LF line endings for cross-platform compatibility
- Research reports moved from repository root to `docs/research/`
- `docs/ARCHITECTURE.md` moved to `docs/architecture/ARCHITECTURE.md`
- README.md documentation links updated for moved files

### Added
- `.editorconfig` for consistent editor configuration
- `CONTRIBUTING.md` contribution guide
- `CHANGELOG.md` (this file)
- `.github/workflows/ci.yml` continuous integration workflow
- `scripts/validate.ps1` PowerShell validation script
- `docs/decisions/ADR-0001-project-structure.md` architecture decision record
- `docs/architecture/DATA_FLOW.md` data flow documentation

## [c7749e8] - 2026-10-17

### Fixed
- Fixed `runtime.txt` CRLF line endings and pinned Python 3.11 for wheel compatibility
- Relaxed dependency version bounds (`>=`) to permit pre-compiled binary wheel resolution

## [e32daf2] - 2026-10-17

### Added
- Interactive model hyperparameters (Prophet seasonality, interval width, forecast horizon; Isolation Forest contamination, n_estimators)
- Data validation guards
- 12-test ingestor regression suite

## [7c81f3d] - 2026-10-17

### Changed
- Enforced Python 3.11 runtime
- Relaxed dependency version bounds for wheel compatibility

## [de8475f] - 2026-10-17

### Fixed
- Resolved README.md merge conflict and integrated origin/master

## [d7e1ac2] - 2026-10-17

### Fixed
- Added defensive filter for file_inputs to resolve `AttributeError` during sample data loading
