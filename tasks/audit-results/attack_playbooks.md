# Attack playbooks — MITRE/threat-intel verification (agent a902bf6824bb71907)

11 playbooks. HEALTHY. All 6 software/group attributions correct (S0609 TRITON, S1045
PIPEDREAM, S0604 INDUSTROYER, S0093 HAVEX, S1072 INDUSTROYER2, VOLT TYPHOON=G1017).
All ~26 technique IDs exist (18 ICS T0xxx + 8 Enterprise T1xxx). Only 4 issues.

## FIX (4)
1. **T0845 → T0843** (semantic inversion — most important). In TRITON + INDUSTROYER
   "Upload Malicious Program Block" stages: T0845 = Program **Upload** (pull logic OFF a PLC,
   Collection). Pushing malicious logic TO a controller = **T0843 Program Download** (Lateral Movement).
2. **T1437.001 → T1071.001** in snort_validation (iSpyoo). T1437.001 is the **Mobile** matrix;
   a web-POST on an OT/IT host is Enterprise T1071.001 (already used elsewhere in the playbook).
3. **Snort SID 50300 mislabeled "TRITON DNS Beacon"** — real TRITON Talos SIDs are 45260/45477/45478.
   Re-label or swap. (5800xxx UMAS SIDs are CV's bundled Talos ICS range — plausible, not publicly verifiable.)
4. **T0882 minor WRONG_TACTIC** — framed as exfil channel but it's an Impact-tactic outcome
   (Theft of Operational Information). Acceptable/imprecise; Enterprise exfil = T1048. Low priority.

## Optional polish
- Add MITRE Group **G1017** to VOLT TYPHOON playbook's mitre_software_id/reference.
- Note: T0855 is being renamed to T1692.001 in newest ATT&CK but T0855 remains canonical.

## Verdict: attacks are realistic and well-attributed. Low-effort, high-value fixes only.
