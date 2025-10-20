import json
import boto3
import logging
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """ML-based cost anomaly detection with forecasting"""
    
    ce = boto3.client('ce')
    cloudwatch = boto3.client('cloudwatch')
    
    try:
        # Get recent anomalies from AWS Cost Anomaly Detection
        end_date = datetime.utcnow().strftime('%Y-%m-%d')
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        anomalies = ce.get_anomalies(
            DateInterval={'StartDate': start_date, 'EndDate': end_date}
        )
        
        # Analyze cost trends for ML forecasting
        cost_forecast = analyze_cost_trends(ce)
        
        # Generate ML insights
        ml_insights = generate_ml_insights(anomalies, cost_forecast)
        
        # Send metrics to CloudWatch
        send_ml_metrics(cloudwatch, ml_insights)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'anomalies_detected': len(anomalies.get('Anomalies', [])),
                'ml_forecast': cost_forecast,
                'risk_assessment': ml_insights,
                'recommendations': generate_recommendations(ml_insights)
            })
        }
        
    except Exception as e:
        logger.error(f"ML anomaly detection error: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def analyze_cost_trends(ce):
    """ML-based cost trend analysis and forecasting"""
    try:
        # Get 60 days of cost data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=60)
        
        response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date.strftime('%Y-%m-%d'),
                'End': end_date.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['BlendedCost']
        )
        
        # Extract daily costs
        daily_costs = []
        for result in response['ResultsByTime']:
            total_cost = sum(float(group['Metrics']['BlendedCost']['Amount']) 
                           for group in result['Groups'])
            daily_costs.append(total_cost)
        
        if len(daily_costs) < 14:
            return {'error': 'insufficient_data'}
        
        # Calculate ML metrics
        recent_avg = statistics.mean(daily_costs[-7:])
        historical_avg = statistics.mean(daily_costs[:-7])
        volatility = statistics.stdev(daily_costs) if len(daily_costs) > 1 else 0
        
        # Linear regression forecast
        forecast = ml_forecast(daily_costs, 30)
        
        return {
            'current_daily_avg': round(recent_avg, 2),
            'trend_change': round((recent_avg - historical_avg) / historical_avg * 100, 2),
            'volatility_score': round(volatility / recent_avg * 100, 2) if recent_avg > 0 else 0,
            'forecast_30_days': forecast,
            'confidence_score': calculate_confidence(daily_costs)
        }
        
    except Exception as e:
        logger.error(f"Cost trend analysis error: {str(e)}")
        return {'error': str(e)}

def ml_forecast(daily_costs, days_ahead):
    """Simple ML forecasting using linear regression"""
    if len(daily_costs) < 7:
        return []
    
    # Use last 14 days for trend calculation
    recent_data = daily_costs[-14:]
    x_values = list(range(len(recent_data)))
    
    # Linear regression calculation
    n = len(recent_data)
    sum_x = sum(x_values)
    sum_y = sum(recent_data)
    sum_xy = sum(x * y for x, y in zip(x_values, recent_data))
    sum_x2 = sum(x * x for x in x_values)
    
    # Calculate slope and intercept
    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return [recent_data[-1]] * days_ahead
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n
    
    # Generate forecast
    forecast = []
    for i in range(days_ahead):
        predicted = intercept + slope * (len(recent_data) + i)
        forecast.append(max(0, round(predicted, 2)))
    
    return forecast

def generate_ml_insights(anomalies, forecast):
    """Generate ML-powered insights and risk assessment"""
    insights = {
        'risk_level': 'low',
        'confidence_score': 0.85,
        'anomaly_frequency': 0,
        'cost_stability': 'stable',
        'predicted_monthly_cost': 0
    }
    
    # Analyze anomalies
    if anomalies.get('Anomalies'):
        high_impact_anomalies = [
            a for a in anomalies['Anomalies'] 
            if float(a.get('Impact', {}).get('MaxImpact', 0)) > 100
        ]
        insights['anomaly_frequency'] = len(high_impact_anomalies)
        
        if len(high_impact_anomalies) > 5:
            insights['risk_level'] = 'high'
        elif len(high_impact_anomalies) > 2:
            insights['risk_level'] = 'medium'
    
    # Analyze forecast trends
    if forecast.get('trend_change', 0) > 25:
        insights['risk_level'] = 'high'
        insights['cost_stability'] = 'volatile'
    elif forecast.get('trend_change', 0) > 10:
        insights['risk_level'] = 'medium' if insights['risk_level'] == 'low' else insights['risk_level']
    
    # Calculate predicted monthly cost
    if forecast.get('forecast_30_days'):
        insights['predicted_monthly_cost'] = round(sum(forecast['forecast_30_days']), 2)
    
    # Adjust confidence based on volatility
    volatility = forecast.get('volatility_score', 0)
    if volatility > 50:
        insights['confidence_score'] = 0.6
    elif volatility > 25:
        insights['confidence_score'] = 0.75
    
    return insights

def calculate_confidence(daily_costs):
    """Calculate ML model confidence based on data quality"""
    if len(daily_costs) < 7:
        return 0.3
    
    # More data = higher confidence
    data_score = min(len(daily_costs) / 30, 1.0) * 0.4
    
    # Lower volatility = higher confidence
    if len(daily_costs) > 1:
        volatility = statistics.stdev(daily_costs) / statistics.mean(daily_costs)
        stability_score = max(0, 1 - volatility) * 0.6
    else:
        stability_score = 0.5
    
    return round(data_score + stability_score, 2)

def generate_recommendations(ml_insights):
    """Generate ML-based recommendations"""
    recommendations = []
    
    if ml_insights['risk_level'] == 'high':
        recommendations.append({
            'priority': 'critical',
            'action': 'Implement immediate cost controls and budget alerts',
            'ml_confidence': ml_insights['confidence_score'],
            'impact': 'Prevent cost overruns'
        })
    
    if ml_insights['anomaly_frequency'] > 3:
        recommendations.append({
            'priority': 'high',
            'action': 'Enable AWS Cost Anomaly Detection with automated alerts',
            'ml_confidence': 0.9,
            'impact': 'Early anomaly detection'
        })
    
    if ml_insights['predicted_monthly_cost'] > 0:
        recommendations.append({
            'priority': 'medium',
            'action': f"Budget planning: ML predicts ${ml_insights['predicted_monthly_cost']:,.2f} monthly cost",
            'ml_confidence': ml_insights['confidence_score'],
            'impact': 'Improved financial forecasting'
        })
    
    return recommendations

def send_ml_metrics(cloudwatch, ml_insights):
    """Send ML insights as CloudWatch metrics"""
    try:
        risk_values = {'low': 1, 'medium': 2, 'high': 3}
        
        cloudwatch.put_metric_data(
            Namespace='CostOptimization/ML',
            MetricData=[
                {
                    'MetricName': 'MLRiskLevel',
                    'Value': risk_values.get(ml_insights['risk_level'], 1),
                    'Unit': 'None'
                },
                {
                    'MetricName': 'MLConfidenceScore',
                    'Value': ml_insights['confidence_score'],
                    'Unit': 'None'
                },
                {
                    'MetricName': 'AnomalyFrequency',
                    'Value': ml_insights['anomaly_frequency'],
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'PredictedMonthlyCost',
                    'Value': ml_insights['predicted_monthly_cost'],
                    'Unit': 'None'
                }
            ]
        )
        
    except Exception as e:
        logger.error(f"Error sending ML metrics: {str(e)}")
