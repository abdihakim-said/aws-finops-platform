import boto3
import json
from datetime import datetime, timedelta

def lambda_handler(event, context):
    organizations = boto3.client('organizations')
    ce = boto3.client('ce')
    
    results = {
        'account_analysis': [],
        'cost_anomalies': [],
        'budget_violations': [],
        'tagging_compliance': {}
    }
    
    # Get all accounts in organization
    try:
        accounts = organizations.list_accounts()
        
        for account in accounts['Accounts']:
            account_id = account['Id']
            account_name = account['Name']
            
            # Get cost data for each account
            cost_data = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                    'End': datetime.now().strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}]
            )
            
            # Find this account's costs
            account_cost = 0
            for result in cost_data['ResultsByTime']:
                for group in result['Groups']:
                    if group['Keys'][0] == account_id:
                        account_cost = float(group['Metrics']['BlendedCost']['Amount'])
                        break
            
            # Analyze cost trends and anomalies
            if account_cost > 10000:  # Accounts with >$10k spend
                # Check for cost anomalies (>50% increase)
                previous_month_cost = get_previous_month_cost(ce, account_id)
                if previous_month_cost > 0:
                    cost_change = ((account_cost - previous_month_cost) / previous_month_cost) * 100
                    
                    if cost_change > 50:
                        results['cost_anomalies'].append({
                            'account_id': account_id,
                            'account_name': account_name,
                            'current_cost': f"${account_cost:.2f}",
                            'previous_cost': f"${previous_month_cost:.2f}",
                            'increase_percentage': f"{cost_change:.1f}%",
                            'severity': 'HIGH' if cost_change > 100 else 'MEDIUM'
                        })
            
            # Check tagging compliance
            tagging_compliance = check_tagging_compliance(account_id)
            
            results['account_analysis'].append({
                'account_id': account_id,
                'account_name': account_name,
                'monthly_cost': f"${account_cost:.2f}",
                'tagging_compliance': f"{tagging_compliance:.1f}%",
                'cost_trend': 'INCREASING' if account_cost > previous_month_cost else 'STABLE'
            })
    
    except Exception as e:
        print(f"Error accessing Organizations: {str(e)}")
    
    # Check for budget violations across organization
    budgets = boto3.client('budgets')
    try:
        budget_list = budgets.describe_budgets(AccountId=boto3.Session().get_credentials().access_key[:12])
        
        for budget in budget_list.get('Budgets', []):
            budget_name = budget['BudgetName']
            budget_limit = float(budget['BudgetLimit']['Amount'])
            
            # Get actual spend vs budget
            actual_spend = get_budget_actual_spend(budgets, budget_name)
            
            if actual_spend > budget_limit * 0.8:  # >80% of budget
                results['budget_violations'].append({
                    'budget_name': budget_name,
                    'budget_limit': f"${budget_limit:.2f}",
                    'actual_spend': f"${actual_spend:.2f}",
                    'utilization': f"{(actual_spend/budget_limit*100):.1f}%",
                    'status': 'EXCEEDED' if actual_spend > budget_limit else 'WARNING'
                })
                
    except Exception as e:
        print(f"Error checking budgets: {str(e)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def get_previous_month_cost(ce, account_id):
    try:
        cost_data = ce.get_cost_and_usage(
            TimePeriod={
                'Start': (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
                'End': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['BlendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}]
        )
        
        for result in cost_data['ResultsByTime']:
            for group in result['Groups']:
                if group['Keys'][0] == account_id:
                    return float(group['Metrics']['BlendedCost']['Amount'])
    except:
        pass
    return 0

def check_tagging_compliance(account_id):
    # Simplified tagging compliance check
    # In real implementation, would check resource tagging across services
    return 75.0  # Placeholder compliance percentage

def get_budget_actual_spend(budgets_client, budget_name):
    # Simplified budget spend check
    return 850.0  # Placeholder actual spend
