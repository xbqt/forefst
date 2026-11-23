The attributes are the metadata a file or a directory carries: its times and file attributes, its content, its
alternate data streams and snapshots, its reparse data, its extended attributes and its encryption metadata.

The two an examiner reads first are [$STANDARD_INFORMATION](STANDARD_INFORMATION.md) (the times, the file attributes,
the change-journal link) and [$DATA](DATA.md) (the content: bytes inline in the record, or on-disk extents).

ReFS has no `$FILE_NAME` attribute: a name is a row of its directory, and there is no 8.3 short name.

How the attributes are organised, and where each one sits in a record: [Attributes](../concepts/attributes.md) in
Concepts.

<!-- site: after-list -->

## A directory's own row, byte by byte

Each attribute's bytes are in its own colour and link to its page.

<!-- site: hexfig "attrmap_dir_win11refs2tspecials" "nocaption" -->

## A file's record with two alternate data streams, byte by byte

<!-- site: hexfig "attrmap_file_win11refs2tspecials" "nocaption" -->
