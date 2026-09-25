# Security

## Safety model for automated changes

- `cost_optimizer` and `unused_resources_cleanup` can modify or delete resources. Both are **dry-run by default**. They only act when the Lambda has `DRY_RUN=false`, and an event with `{"dryRun": true}` always forces a dry run.
- Snapshots that back an AMI, snapshots created by AWS Backup, and snapshots tagged `finops:keep=true` are never deleted.
- A security group is treated as "in use" if any network interface references it, or another group's rules reference it.
- `tests/test_dry_run.py` enforces these rules in CI.

## Known gaps

- The Lambda IAM role still allows destructive EC2/RDS actions on `Resource: "*"`. In a real account, scope it with tag conditions (e.g. `aws:ResourceTag/finops:managed = true`).
- There is no approval workflow. For anything beyond dev, route proposed changes to a human (SNS/Slack → approve) instead of acting directly.

## Reporting

Please open a GitHub issue, or contact me via my GitHub profile, for anything security-related.
