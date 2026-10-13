"""Validate locally signed release assets before publication."""
import hashlib
import json
from pathlib import Path
import plistlib
import re
import os
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    tag, folder = sys.argv[1], Path(sys.argv[2])
    version = json.loads((ROOT / 'version.json').read_text())
    config = json.loads((ROOT / 'updates.json').read_text())
    assert tag == 'v' + version['version'], 'Tag does not match version.json'
    archive = f"WeExport-{version['version']}-{version['build']}.zip"
    expected = {archive, 'appcast.xml', f"WeExport-{version['version']}.pkg",
                f"WeExport-{version['version']}-installer.zip",
                f"WeExport-{version['version']}-third-party-sources.tar.gz"}
    recorded = {}
    for line in (folder / 'SHA256SUMS').read_text().splitlines():
        checksum, name = line.split('  ', 1)
        assert name not in recorded and name in expected, 'Unexpected checksum entry'
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == checksum, 'Checksum mismatch'
        recorded[name] = checksum
    assert set(recorded) == expected, 'Missing release asset'
    assert {p.name for p in folder.iterdir()} == expected | {'SHA256SUMS'}, 'Unexpected release file'
    feed = folder / 'appcast.xml'
    namespace = '{http://www.andymatuschak.org/xml-namespaces/sparkle}'
    item = ET.fromstring(feed.read_bytes()).find('./channel/item')
    assert item.findtext(namespace + 'version') == str(version['build']), 'Feed build mismatch'
    assert item.findtext(namespace + 'shortVersionString') == version['version'], 'Feed version mismatch'
    enclosure = item.find('enclosure')
    assert enclosure.get('url') == f"https://github.com/{config['repository']}/releases/download/{tag}/{archive}", 'Archive URL mismatch'
    assert enclosure.get('length') == str((folder / archive).stat().st_size), 'Archive length mismatch'
    raw_feed = feed.read_bytes()
    signed = re.search(rb'<!-- sparkle-signatures:\nedSignature: ([A-Za-z0-9+/=]+)\nlength: ([0-9]+)\n-->\s*$', raw_feed)
    assert signed is not None, 'Missing feed signature'
    assert int(signed[2]) == signed.start(), 'Unexpected signed feed length'
    with tempfile.TemporaryDirectory() as temporary:
        verifier = Path(temporary) / 'verify-signature'
        subprocess.run(['xcrun', 'swiftc', str(ROOT / 'scripts/VerifySignature.swift'), '-o', str(verifier)], check=True)
        subprocess.run([str(verifier), config['public_key'], signed[1].decode(), str(feed), signed[2].decode()], check=True)
        subprocess.run([str(verifier), config['public_key'], enclosure.get(namespace + 'edSignature'), str(folder / archive)], check=True)
    with zipfile.ZipFile(folder / archive) as stream:
        info = plistlib.loads(stream.read('WeExport.app/Contents/Info.plist'))
        assert info['CFBundleVersion'] == str(version['build']), 'App build mismatch'
        assert info['CFBundleShortVersionString'] == version['version'], 'App version mismatch'
        assert info['SUPublicEDKey'] == config['public_key'], 'Update key mismatch'
        assert info['SUFeedURL'] == config['feed_url'], 'Feed URL mismatch'
        assert info['SURequireSignedFeed'] and info['SUVerifyUpdateBeforeExtraction'], 'Missing signature policy'
    package = folder / f"WeExport-{version['version']}.pkg"
    with zipfile.ZipFile(folder / f"WeExport-{version['version']}-installer.zip") as stream:
        assert hashlib.sha256(stream.read(package.name)).digest() == hashlib.sha256(package.read_bytes()).digest(), 'Installer ZIP contains a different package'
    with tempfile.TemporaryDirectory() as temporary:
        expanded = Path(temporary) / 'installer'
        subprocess.run(['pkgutil', '--expand-full', str(package), str(expanded)], check=True)
        component = ET.parse(expanded / 'application.pkg/PackageInfo').getroot()
        assert component.get('install-location') == '/Applications', 'Unexpected installer destination'
        assert component.get('version') == version['version'], 'Installer version mismatch'
        identifier = 'local.wechat.chat-exporter'
        assert component.find(f"./bundle-version/bundle[@id='{identifier}']") is None, 'Installer silently skips downgrades'
        assert component.find(f"./upgrade-bundle/bundle[@id='{identifier}']") is not None, 'Installer must replace the complete bundle'
        assert len(component.findall('./relocate/bundle')) == 0, 'Installer relocation is not allowed'
        distribution = ET.parse(expanded / 'Distribution').getroot()
        assert distribution.find(f".//must-close/app[@id='{identifier}']") is not None, 'Installer must close the running application'
        application = expanded / 'application.pkg/Payload/WeExport.app'
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(application)], check=True)
        # Verify actual payload bytes, not just package metadata or its filename.
        expected_paths = set()
        with zipfile.ZipFile(folder / archive) as stream:
            for entry in stream.infolist():
                if not entry.filename.startswith('WeExport.app/') or entry.is_dir():
                    continue
                relative = entry.filename.removeprefix('WeExport.app/')
                assert relative not in expected_paths, 'Duplicate application archive path'
                expected_paths.add(relative)
                target = application / relative
                assert '..' not in Path(relative).parts, 'Invalid application archive path'
                if stat.S_ISLNK(entry.external_attr >> 16):
                    assert target.is_symlink() and os.fsencode(os.readlink(target)) == stream.read(entry), 'Installer symlink mismatch'
                else:
                    assert target.is_file() and not target.is_symlink(), 'Installer file missing'
                    assert hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(stream.read(entry)).digest(), 'Installer application differs from signed update'
        actual_paths = {str(path.relative_to(application)) for path in application.rglob('*')
                        if path.is_symlink() or path.is_file()}
        assert actual_paths == expected_paths, 'Unexpected installer application files'
    print('Release assets verified:', tag, 'build', version['build'])


if __name__ == '__main__':
    main()
