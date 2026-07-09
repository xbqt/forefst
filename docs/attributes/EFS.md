# $EFS

`$EFS` is the Windows **Encrypting File System** metadata for an encrypted file. ReFS stores it as a
single `$LOGGED_UTILITY_STREAM` attribute (schema 0x200, embedded type 0x100) whose stream name is
`$EFS`. It holds the standard Windows **DDF** (Data-Decryption Field): the user's certificate identity
and the RSA-wrapped File Encryption Key.

## Value layout

The value is a 12-byte ReFS sub-record wrapper followed by the standard Windows EFS metadata carrying
the DDF. The value is **676 or 732 bytes**; the difference is entirely in the variable-length
container-GUID and provider-name strings, and is **not cluster-size-dependent** (the blob is produced by
the Windows EFS service, not by the cluster-aware driver layer). Offsets are value-relative:

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | Padding | 0 |
| 0x04 | 4 | Data-area size | metadata length |
| 0x08 | 4 | Content offset | 0x0C |
| 0x0C | 4 | Metadata length | repeats the data-area size |
| 0x14 | 4 | EFS state / version | 2 |
| 0x1C | 16 | Metadata GUID | per-file (one of only two per-file-varying regions) |
| 0x60 | 4 | DDF entry count | 1 (no DRF — no data-recovery agent) |
| 0x64 | (entry) | DDF entry | the single Data-Decryption-Field entry (base for the entry-relative fields below) |
| 0x94 | 28 | Credential SID | the EFS user's SID (`S-1-5-21-…`; matches an owner in the security table, OID 0x530) — fixed offset |
| 0xB0 | 20 | Public-key-info header | 5 u32s, fixed offset: hash length (0x14 = SHA-1) + the cguid / provider / cname string offsets, each relative to this header base |
| 0xC4 | 20 | Certificate thumbprint | SHA-1 of the user's EFS certificate — fixed offset |
| 0xD8 | var | Container-GUID string | UTF-16LE — start of the variable-length strings region |
| (var) | var | CSP provider string | UTF-16LE (e.g. `Microsoft Enhanced Cryptographic Provider v1.0`) |
| (var) | var | Key-container name | UTF-16LE |
| 0x64 + FEKoff | 256 | **Wrapped FEK** | the File Encryption Key, RSA-2048-wrapped — the **last field of the DDF entry** (at value+0x1A2 on 676-byte records, value+0x1DA on 732-byte) |

### The DDF entry (base = value+0x64)

| Entry offset | Field | Value |
|--------------|-------|-------|
| +0x00 | Entry length | spans value+0x64 → value_end − 2 |
| +0x04 | Certificate-hash length | 0x14 (20 = SHA-1) |
| +0x08 | FEK length | 0x100 (256 = RSA-2048) |
| +0x0C | FEK offset (entry-relative) | `FEK_offset + FEK_length = entry_length` — the FEK is the entry's last field |
| +0x18 | SID length | 0x1C (28) |

The certificate thumbprint and SID are constant per user/certificate; the **metadata GUID (0x1C) and the
256-byte wrapped FEK are the only per-file fields**. There is **no `EFSS` signature** in the value and
**no DRF** (the DDF entry count is 1). Everything except the RSA-wrapped FEK is plaintext metadata and
is fully decoded; the FEK is opaque by design.

## How EFS metadata is stored

ReFS does not implement EFS itself — the `$EFS` value is the standard Windows EFS metadata blob,
produced by the EFS user-mode (LSA) service and stored verbatim (`refs.sys` does not generate the crypto
fields). On disk it is one embedded single-instance sub-record (schema 0x200, type 0x100,
subtype 0x0005) with stream name `$EFS`. There is **no `$CBW4` stream** — that name does not exist on
disk or in the binary; it is a misread of a mangled C++ checksum-template token (`span<$$CBW4byte@utl>`),
unrelated to EFS.

An encrypted file also carries the **`0x4000` (FILE_ATTRIBUTE_ENCRYPTED)** file-attribute flag, set by
`RefsEncryptStream` and cleared on decrypt. EFS is supported from **v3.11+** (gated by
`RefsIsEncryptionSupported`). Related driver functions: `RefsSetEncryption`, `RefsEncryptStream`,
`RefsReadRawEncrypted`, `RefsWriteRawEncrypted`, `EfspFileRequiresEncryption`.

## Can the data be decrypted from a ReFS image?

**Not from the ReFS data volume alone.** The on-disk elements are necessary but not sufficient:

| Element | On the ReFS data volume? |
|---------|--------------------------|
| Encrypted file data (AES ciphertext) | **Yes** — the encrypted files' `$DATA` |
| RSA-wrapped FEK | **Yes** — the 256-byte blob in `$EFS` |
| Certificate thumbprint, key-container name, user SID | **Yes** — plaintext in `$EFS` (identifies *which* key is needed) |
| User's RSA private key (unwraps the FEK) | **No** — in the profile `…\Microsoft\Crypto\RSA\<SID>\`, DPAPI-protected |
| DPAPI master key + user password | **No** — in the profile `…\Microsoft\Protect\<SID>\`, gated by the password |

A stream scan of a ReFS *data* volume finds the encrypted data and the wrapped FEKs but **no RSA
private-key material, no `Crypto\RSA` containers, and no DPAPI master keys** — so the FEK cannot be
unwrapped from that image alone. To decrypt you additionally need the off-volume EFS chain: the user's
RSA private key + DPAPI master key + the password (or a domain data-recovery-agent key, or the password
hash from a SAM/LSASS source). If the ReFS volume *were* the system volume carrying the user profile,
that material would be present and the standard chain applies:
`password → DPAPI master key → RSA private key → unwrap FEK → AES-decrypt the file`. The `$EFS`
thumbprint / container / SID fields are the forensic pointers that identify exactly which key and user
to target.

## Cross-references

- [Attributes — Forensic Reference](README.md) — the attribute catalog and on-disk layout
- [Driver Interface](../concepts/driver_architecture.md) — the `cng.sys` import for EFS support

## Evidence

Schema 0x200 / type 0x100 and the `$EFS` stream name are confirmed by the string literal (E1) and the
decompiled driver (E2); the value layout, the DDF/FEK offsets, and the *no `$CBW4` / no `EFSS` / no DRF*
facts are raw-disk decoded (RD) across the corpus EFS records (value sizes 676 and 732). Findings:
**MD_ATTR_RA_009**, **MD_EFS_RA_005** (value sizes). See
[how this was verified](../methodology.md) to trace these to the exact images and measurements in
`analysis/`.
