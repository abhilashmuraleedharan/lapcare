# Capture: ThinkPad E16 Gen 2 — storage_smart

- Machine: ThinkPad E16 Gen 2 (21MB, maintainer's reference machine)
- Captured: 2026-07-09, kernel 6.8.0-124-generic, smartmontools 7.4
- Method: `smartctl --json --all /dev/nvme0n1` (read-only) in a validation
  container with the block device passed through + CAP_SYS_ADMIN (the NVMe
  admin ioctl needs it — the same reason the ADR-0006 helper exists);
  sysfs files copied from the live `/sys/block`.
- Redaction: REDACTED (serial_number and namespace eui64 zeroed at capture
  time; no other identifiers present).
- Quirk captured here: the SK hynix HFS512GEM4X drive has no NVMe self-test
  log, so `smartctl --all` exits with bit 2 set ("Read Self-test Log failed:
  Invalid Field in Command") while the JSON is complete and healthy — see
  `smartctl.messages` in the JSON and ADR-0006 §12.
