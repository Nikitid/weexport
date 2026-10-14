# Distribution releases

Application builds and update signing take place in the separate private source
checkout. This repository contains public metadata and verification code only.
Signing keys, server configuration, diagnostics, and account data are excluded.

1. Build and test the application in its source checkout.
2. Prepare signed assets and verify them with `scripts/verify-release.py`.
3. `scripts/publish-update.py --push-tag` in the source checkout uploads the
   verified assets to a draft release (a beta as a pre-release), commits
   `version.json`, `updates.json`, `LICENSE` and the verification scripts here,
   and pushes the matching tag `vX.Y.Z` or `vX.Y.Z_betaBUILD`. Never move an
   existing published tag.
4. The Release workflow downloads the draft, verifies signatures, version
   numbers, checksums and installer payload bytes, publishes it with the notes
   written in the source repository (a stable release as latest), and deploys
   `appcast.xml` to GitHub Pages (`https://nikitid.github.io/weexport/appcast.xml`).
   The manual Feed workflow redeploys the latest release's feed.

The public archive includes third-party source and licenses required by bundled
components. WeExport itself is proprietary; its source is not published. Previous feed
entries are retained when preparing an update. An unsuccessful workflow leaves
the draft hidden and the previous latest release available.

Versions up to 1.2.0 read the feed from this repository's former name,
`weexport-updates`, whose release URLs GitHub redirects, so the latest stable
release keeps an `appcast.xml` asset. Never create a repository named
`weexport-updates`.
