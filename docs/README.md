# AWS FinOps Platform Documentation

## 📚 Documentation Index

### Getting Started
- [Installation Guide](../README.md#quick-deployment)
- [Architecture Overview](../ARCHITECTURE.md)
- [Business Case](../BUSINESS_CASE.md)

### Technical Documentation
- [Security & Compliance](../SECURITY.md)
- [Cost Savings Calculator](../calculate-savings.py)
- [Performance Metrics](../monitoring/performance-metrics.json)

### Deployment Guides
- [Terraform Modules](../terraform/modules/)
- [Environment Configuration](../terraform/environments/)
- [CI/CD Pipeline](../.github/workflows/deploy.yml)

### Operations
- [Monitoring Setup](../monitoring/)
- [Demo Environment](../demo/)
- [Testing Guide](../tests/)

## 🎯 Key Features

### Cost Optimization Categories
1. **Storage Optimization** - EBS gp2→gp3, S3 lifecycle, snapshot cleanup
2. **Compute Right-sizing** - EC2/RDS instance optimization
3. **Spot Instance Orchestration** - 60-90% cost reduction
4. **Network Optimization** - NAT Gateway, VPC Endpoint recommendations
5. **EKS Cost Management** - Kubernetes resource optimization
6. **Multi-Account Governance** - Organization-wide cost control

### Business Impact
- **£21,796 annual savings** potential
- **8.3 month payback period**
- **45% ROI** in first year
- **95% automation** of cost optimization tasks

## 🚀 Quick Commands

```bash
# Deploy to production
./deploy-environment.sh prod apply

# Run cost analysis
python3 calculate-savings.py

# Run tests
pytest tests/ -v --cov

# Setup demo environment
./demo/setup-demo.sh
```

## 📊 Monitoring

- **CloudWatch Dashboard**: Real-time cost metrics
- **SNS Alerts**: Budget threshold notifications  
- **Performance Tracking**: Lambda execution metrics
- **Cost Anomaly Detection**: Automated spending alerts

## 🔧 Customization

The platform is designed for enterprise customization:
- Modular Terraform architecture
- Environment-specific configurations
- Pluggable optimization strategies
- Extensible monitoring framework
