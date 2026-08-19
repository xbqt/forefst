The byte-level on-disk layouts — metadata structure decoded, field by field.

**Boot & bootstrap** is the fixed chain a parser must walk before anything else: the VBR, superblock, and
checkpoint, and the well-known system OIDs they lead to. **B+-tree rows & pages** is the generic machinery
every table is built from — the node header, page and page-reference formats, directory-entry and extent
rows, and the reverse index. **System tables (the 13 roots)** decodes each checkpoint root in turn: the
object, schema, parent-child, container, and allocator tables, block reference counts, integrity state,
volume info, security, the reparse index, the upcase table, and the trash table. **Journals & logs** covers
the two change records — the USN change journal and the durable MLog transaction log.
