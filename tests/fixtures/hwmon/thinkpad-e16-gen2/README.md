# Capture: ThinkPad E16 Gen 2 — hwmon

- Machine: ThinkPad E16 Gen 2 (21MB), captured 2026-07-09, kernel 6.8.0-124-generic
- Redaction: nothing to redact (chip names, labels, temperatures only)
- Quirks captured (subset of the live tree, values verbatim):
  - thinkpad EC exposes unpopulated slots: temp3 reads 13 °C and temp7 reads
    2 °C on a machine idling at ~50 °C — implausible artifacts, not data.
    On the live machine temp8_input EXISTS but fails to read (EIO-style);
    fixtures can't encode an unreadable file, so it is absent here — both
    collapse to the same read_int→None path in the provider.
  - Unlabeled sensors are normal (acpitz temp1, several thinkpad slots).
  - coretemp slot numbering is non-contiguous (temp1, then temp10).
