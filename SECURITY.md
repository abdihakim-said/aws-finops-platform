# Security & Compliance

## Security Model

### IAM Least Privilege
- Lambda functions use minimal required permissions
- Cross-account access via AssumeRole only
- No hardcoded credentials or secrets

### Data Protection
- All data encrypted in transit (TLS 1.2+)
- CloudWatch logs encrypted at rest
- No PII or sensitive data stored

### Audit & Compliance
- All optimization actions logged to CloudTrail
- Cost allocation tags for financial governance
- Rollback capabilities for all automated changes

## Risk Mitigation

### Approval Workflows
- High-impact changes (>£1000) require approval
- Dry-run mode for testing optimizations
- Gradual rollout across environments

### Monitoring & Alerting
- Real-time failure detection
- Cost anomaly alerts within 5 minutes
- Performance degradation monitoring

## Compliance Frameworks
- **SOC 2 Type II** - Audit logging and access controls
- **ISO 27001** - Information security management
- **GDPR** - No personal data processing
- **PCI DSS** - Secure configuration management
