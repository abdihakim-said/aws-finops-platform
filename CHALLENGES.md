# AWS FinOps Platform - Technical Challenges & Exercises

## 🎯 Challenge Categories

### 1. **Deployment & Infrastructure** (Beginner)
### 2. **Cost Optimization** (Intermediate) 
### 3. **Advanced Monitoring** (Advanced)
### 4. **Multi-Account Governance** (Expert)

---

## 🚀 Challenge 1: Emergency Deployment Recovery

**Scenario:** Your production deployment is stuck with Lambda functions in "Pending" state for 45+ minutes.

**Your Mission:**
1. Identify stuck functions
2. Safely remove problematic resources
3. Redeploy without data loss
4. Implement prevention measures

**Success Criteria:**
```bash
# All functions should be active
aws lambda list-functions --query 'Functions[?contains(FunctionName, `production-`)].State' --output text | grep -v Active && echo "FAIL" || echo "PASS"

# EventBridge rules enabled
aws events list-rules --name-prefix production- --query 'Rules[?State!=`ENABLED`]' --output text | wc -l | grep -q 0 && echo "PASS" || echo "FAIL"
```

**Time Limit:** 30 minutes

---

## 💰 Challenge 2: Cost Anomaly Investigation

**Scenario:** Your ML cost anomaly detector is triggering alerts for unusual spending patterns.

**Your Mission:**
1. Analyze the anomaly detection logs
2. Identify the root cause of cost spikes
3. Implement automated remediation
4. Create custom alerting rules

**Investigation Commands:**
```bash
# Check anomaly detector logs
aws logs filter-log-events \
  --log-group-name "/aws/lambda/production-ml-cost-anomaly-detector" \
  --start-time $(date -d '24 hours ago' +%s)000 \
  --region us-east-1

# Analyze cost patterns
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

**Success Criteria:**
- Identify service causing 90%+ of cost increase
- Create automated response within 15 minutes of detection
- Reduce false positive rate to <5%

**Time Limit:** 45 minutes

---

## 📊 Challenge 3: Dashboard Optimization

**Scenario:** Your CloudWatch dashboard shows "No data available" despite successful deployments.

**Your Mission:**
1. Diagnose why metrics aren't appearing
2. Create custom metrics for business KPIs
3. Build real-time cost savings tracker
4. Implement automated dashboard updates

**Custom Metrics to Create:**
```python
# Example: Cost savings metric
import boto3
cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='FinOps/CostSavings',
    MetricData=[
        {
            'MetricName': 'MonthlySavings',
            'Value': 15000.00,
            'Unit': 'None',
            'Dimensions': [
                {'Name': 'Environment', 'Value': 'production'},
                {'Name': 'OptimizationType', 'Value': 'EC2Rightsizing'}
            ]
        }
    ]
)
```

**Success Criteria:**
- Dashboard shows data for all 11 functions
- Custom business metrics visible
- Real-time cost tracking operational
- Automated alerts for optimization opportunities

**Time Limit:** 60 minutes

---

## 🏗️ Challenge 4: Multi-Region Deployment

**Scenario:** Expand your FinOps platform to 3 AWS regions with centralized monitoring.

**Your Mission:**
1. Deploy functions to us-west-2 and eu-west-1
2. Aggregate metrics in central region
3. Implement cross-region cost comparison
4. Create disaster recovery procedures

**Architecture Requirements:**
```
Primary: us-east-1 (Central monitoring)
Secondary: us-west-2 (West Coast workloads)  
Tertiary: eu-west-1 (European workloads)
```

**Success Criteria:**
- Functions deployed in all 3 regions
- Central dashboard shows all regions
- Cross-region cost analysis working
- <5 minute failover time

**Time Limit:** 90 minutes

---

## 🔐 Challenge 5: Security Hardening

**Scenario:** Implement enterprise-grade security for your FinOps platform.

**Your Mission:**
1. Enable AWS Config compliance monitoring
2. Implement least-privilege IAM policies
3. Add encryption for all data at rest/transit
4. Create security incident response automation

**Security Checklist:**
```bash
# Check IAM policy compliance
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:role/aws-finops-platform-production-lambda-role \
  --action-names ec2:TerminateInstances \
  --resource-arns "*"

# Verify encryption
aws lambda get-function --function-name production-cost-optimizer \
  --query 'Configuration.KMSKeyArn'

# Check VPC configuration
aws lambda get-function --function-name production-cost-optimizer \
  --query 'Configuration.VpcConfig'
```

**Success Criteria:**
- All functions use customer-managed KMS keys
- IAM policies follow least-privilege principle
- VPC endpoints configured for AWS services
- Security monitoring alerts operational

**Time Limit:** 120 minutes

---

## 🎮 Bonus Challenges

### Speed Run Challenge
**Deploy entire platform from scratch in under 15 minutes**
- Fresh AWS account
- Complete infrastructure
- All functions operational
- Dashboard showing data

### Cost Optimization Competition
**Achieve maximum cost savings in 24 hours**
- Identify optimization opportunities
- Implement automated fixes
- Measure actual savings
- Document ROI

### Chaos Engineering
**Platform survives random failures**
- Randomly delete resources
- Simulate AWS service outages  
- Test recovery procedures
- Measure MTTR (Mean Time To Recovery)

---

## 🏆 Scoring System

### Points Breakdown:
- **Deployment Challenges:** 100 points each
- **Cost Optimization:** 150 points each  
- **Advanced Monitoring:** 200 points each
- **Multi-Account/Region:** 300 points each
- **Security Hardening:** 250 points each

### Bonus Multipliers:
- **Under time limit:** 1.5x points
- **Zero downtime:** 2x points
- **Documentation included:** 1.2x points
- **Automated testing:** 1.3x points

### Achievement Levels:
- 🥉 **Bronze:** 500+ points
- 🥈 **Silver:** 1000+ points  
- 🥇 **Gold:** 1500+ points
- 💎 **Platinum:** 2000+ points

---

## 📚 Learning Resources

### AWS Documentation:
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Cost Explorer API](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/)
- [EventBridge Patterns](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html)

### Advanced Topics:
- [FinOps Foundation](https://www.finops.org/)
- [AWS Well-Architected Cost Optimization](https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

## 🎯 Challenge Submission

### Required Deliverables:
1. **Working code/configuration**
2. **Screenshot evidence**  
3. **Performance metrics**
4. **Lessons learned document**
5. **Improvement recommendations**

### Submission Format:
```
challenge-submission/
├── code/
├── screenshots/
├── metrics/
├── documentation/
└── README.md
```

**Good luck! 🚀**

---
*Challenge difficulty scales from real-world scenarios encountered during platform development*
