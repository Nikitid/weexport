# Distribution releases

Application builds and update signing take place in the separate private source
checkout. This repository contains public metadata and verification code only.
Signing keys, server configuration, diagnostics, and account data are excluded.

1. Build and test the application in its source checkout.
2. Prepare signed assets and verify them with `scripts/verify-release.py`.
3. Update `version.json` and `updates.json` in this repository. Commit subjects
   become release notes, so describe user-visible changes. Audit all tracked
   files and run `sh scripts/check-readme.sh` before committing or pushing.
4. Upload the verified assets to a draft release for the matching `vX.Y.Z` tag.
   Do not publish the draft manually. Create the tag locally at the audited
   metadata commit; never move an existing published tag.
5. Push the metadata commit and then the matching tag. The Release workflow
   downloads the draft, verifies signatures, version numbers, checksums, and
   installer payload bytes, builds notes from commit subjects, and publishes.

The public archive includes third-party source and licenses required by bundled
components. It does not include the private application source. Previous feed
entries are retained when preparing an update. An unsuccessful workflow leaves
the draft hidden and the previous latest release available.
