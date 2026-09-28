# Security

## Safety model

- **Scanning never changes anything.** The scan function's IAM role has read permissions only, plus writing plans to its own bucket and publishing to its own topic.
- **Changes need a named approver and the plan digest.** The apply function acts only on actions listed in a stored plan, only if the caller supplies the digest of that exact plan, and only before the plan expires (7 days).
- **Every action is re-checked at apply time.** A volume that is no longer gp2, a snapshot whose source volume came back or that now backs an AMI, or an Elastic IP that was attached since the scan is skipped. If the check itself fails (for example throttling), the action is skipped, never assumed safe.
- **Applying is off by default.** The apply function returns `disabled` unless `enable_apply = true` in Terraform.
- **`finops:keep=true` is enforced twice:** in code, and by an explicit IAM `Deny` on the apply role.
- **The apply role can do three things:** `ec2:ModifyVolume`, `ec2:DeleteSnapshot`, `ec2:ReleaseAddress`. It cannot delete volumes, instances, databases or load balancers; those findings are report-only.
- **Plans contain account and resource IDs.** They are stored in a private, versioned, encrypted bucket that denies non-TLS access, and expire after 180 days.

## Reporting

Please open a GitHub issue, or contact me via my GitHub profile, for anything security-related.
