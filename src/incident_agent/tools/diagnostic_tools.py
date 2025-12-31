"""Tools for diagnostic queries, runbook lookup, and system health checks."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool

from ..utils import current_timestamp


# Mock runbook database (would be replaced with actual runbook system)
RUNBOOK_DATABASE = {
    "database": {
        "connection_timeout": {
            "title": "Database Connection Timeout Resolution",
            "steps": [
                "Check database server status and connectivity",
                "Verify connection pool configuration",
                "Review recent database performance metrics",
                "Check for blocking queries or deadlocks",
                "Restart connection pool if necessary",
                "Scale database resources if needed"
            ],
            "estimated_time": "15-30 minutes",
            "escalation_criteria": "If issue persists after connection pool restart"
        },
        "high_cpu": {
            "title": "Database High CPU Usage",
            "steps": [
                "Identify top CPU-consuming queries",
                "Check for missing indexes on frequently queried tables",
                "Review query execution plans",
                "Kill long-running or problematic queries",
                "Consider query optimization or caching",
                "Monitor CPU usage trends"
            ],
            "estimated_time": "20-45 minutes",
            "escalation_criteria": "CPU usage above 90% for more than 30 minutes"
        }
    },
    "api": {
        "high_latency": {
            "title": "API High Latency Resolution",
            "steps": [
                "Check API response time metrics",
                "Identify slow endpoints and database queries",
                "Review application logs for errors",
                "Check downstream service dependencies",
                "Verify load balancer and CDN configuration",
                "Scale API instances if needed"
            ],
            "estimated_time": "10-25 minutes",
            "escalation_criteria": "Latency above SLA thresholds for more than 15 minutes"
        },
        "error_rate": {
            "title": "API Error Rate Investigation",
            "steps": [
                "Analyze error logs and status code distribution",
                "Check for recent deployments or configuration changes",
                "Verify database and external service connectivity",
                "Review rate limiting and authentication systems",
                "Check for DDoS or unusual traffic patterns",
                "Implement circuit breakers if needed"
            ],
            "estimated_time": "15-30 minutes",
            "escalation_criteria": "Error rate above 5% for more than 10 minutes"
        }
    },
    "auth": {
        "login_failures": {
            "title": "Authentication Service Issues",
            "steps": [
                "Check authentication service health and logs",
                "Verify database connectivity for user data",
                "Review recent changes to authentication configuration",
                "Check for brute force attacks or security incidents",
                "Validate JWT token generation and validation",
                "Test authentication flow manually"
            ],
            "estimated_time": "10-20 minutes",
            "escalation_criteria": "Authentication completely unavailable for more than 5 minutes"
        }
    },
    "infrastructure": {
        "disk_space": {
            "title": "Disk Space Management",
            "steps": [
                "Identify directories consuming most disk space",
                "Clean up temporary files and old logs",
                "Archive or compress old data",
                "Check for log rotation configuration",
                "Monitor disk usage trends",
                "Add additional storage if needed"
            ],
            "estimated_time": "5-15 minutes",
            "escalation_criteria": "Disk usage above 95%"
        },
        "memory_leak": {
            "title": "Memory Leak Investigation",
            "steps": [
                "Identify processes with high memory usage",
                "Review application memory usage patterns",
                "Check for memory leaks in recent code changes",
                "Restart affected services if necessary",
                "Monitor memory usage trends",
                "Implement memory profiling if needed"
            ],
            "estimated_time": "20-40 minutes",
            "escalation_criteria": "Memory usage above 90% causing service instability"
        }
    }
}


@tool
def lookup_runbook_tool(
    affected_systems: List[str],
    symptoms: List[str],
    severity: str = "medium"
) -> Dict[str, Any]:
    """
    Look up relevant runbooks based on affected systems and symptoms.
    
    Args:
        affected_systems: List of affected systems/components
        symptoms: List of observed symptoms or keywords
        severity: Incident severity level
        
    Returns:
        Dictionary with matching runbooks and procedures
    """
    try:
        matching_runbooks = []
        
        # Search for runbooks based on affected systems and symptoms
        for system in affected_systems:
            system_lower = system.lower()
            
            if system_lower in RUNBOOK_DATABASE:
                system_runbooks = RUNBOOK_DATABASE[system_lower]
                
                # Look for symptom matches
                for symptom in symptoms:
                    symptom_lower = symptom.lower()
                    
                    for runbook_key, runbook in system_runbooks.items():
                        # Check if symptom matches runbook key or title
                        if (symptom_lower in runbook_key or 
                            symptom_lower in runbook["title"].lower() or
                            any(symptom_lower in step.lower() for step in runbook["steps"])):
                            
                            matching_runbooks.append({
                                "system": system,
                                "runbook_id": f"{system_lower}_{runbook_key}",
                                "title": runbook["title"],
                                "steps": runbook["steps"],
                                "estimated_time": runbook["estimated_time"],
                                "escalation_criteria": runbook["escalation_criteria"],
                                "relevance_score": 0.9  # Would be calculated based on matching algorithm
                            })
        
        # If no specific matches, provide general runbooks for the systems
        if not matching_runbooks:
            for system in affected_systems:
                system_lower = system.lower()
                if system_lower in RUNBOOK_DATABASE:
                    # Add the first runbook for each system as a fallback
                    first_runbook_key = list(RUNBOOK_DATABASE[system_lower].keys())[0]
                    first_runbook = RUNBOOK_DATABASE[system_lower][first_runbook_key]
                    
                    matching_runbooks.append({
                        "system": system,
                        "runbook_id": f"{system_lower}_{first_runbook_key}",
                        "title": first_runbook["title"],
                        "steps": first_runbook["steps"],
                        "estimated_time": first_runbook["estimated_time"],
                        "escalation_criteria": first_runbook["escalation_criteria"],
                        "relevance_score": 0.5
                    })
        
        # Sort by relevance score
        matching_runbooks.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return {
            "success": True,
            "total_runbooks_found": len(matching_runbooks),
            "runbooks": matching_runbooks[:5],  # Limit to top 5
            "search_criteria": {
                "affected_systems": affected_systems,
                "symptoms": symptoms,
                "severity": severity
            },
            "timestamp": current_timestamp().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to lookup runbooks: {str(e)}",
            "affected_systems": affected_systems,
            "symptoms": symptoms
        }


@tool
def query_metrics_tool(
    system: str,
    metric_type: str,
    time_range: str = "1h",
    aggregation: str = "avg"
) -> Dict[str, Any]:
    """
    Query system metrics for diagnostic purposes.
    
    Args:
        system: System to query metrics for
        metric_type: Type of metric (cpu, memory, disk, network, response_time, error_rate)
        time_range: Time range for metrics (5m, 15m, 1h, 6h, 24h)
        aggregation: Aggregation method (avg, max, min, sum)
        
    Returns:
        Dictionary with metric data and analysis
    """
    try:
        # Mock metric data (would be replaced with actual metrics system integration)
        import random
        
        # Generate mock data based on metric type
        if metric_type == "cpu":
            base_value = 45 if system != "database" else 65
            values = [base_value + random.uniform(-15, 25) for _ in range(20)]
            unit = "percent"
            threshold_warning = 70
            threshold_critical = 90
            
        elif metric_type == "memory":
            base_value = 60 if system != "api" else 75
            values = [base_value + random.uniform(-10, 20) for _ in range(20)]
            unit = "percent"
            threshold_warning = 80
            threshold_critical = 95
            
        elif metric_type == "response_time":
            base_value = 150 if system != "api" else 300
            values = [base_value + random.uniform(-50, 200) for _ in range(20)]
            unit = "milliseconds"
            threshold_warning = 500
            threshold_critical = 1000
            
        elif metric_type == "error_rate":
            base_value = 1.5 if system != "auth" else 3.2
            values = [max(0, base_value + random.uniform(-1, 3)) for _ in range(20)]
            unit = "percent"
            threshold_warning = 2
            threshold_critical = 5
            
        else:
            values = [random.uniform(0, 100) for _ in range(20)]
            unit = "units"
            threshold_warning = 70
            threshold_critical = 90
        
        # Calculate aggregated value
        if aggregation == "avg":
            current_value = sum(values) / len(values)
        elif aggregation == "max":
            current_value = max(values)
        elif aggregation == "min":
            current_value = min(values)
        else:
            current_value = sum(values)
        
        # Determine status
        if current_value >= threshold_critical:
            status = "critical"
        elif current_value >= threshold_warning:
            status = "warning"
        else:
            status = "normal"
        
        # Generate trend analysis
        recent_values = values[-5:]
        older_values = values[:5]
        recent_avg = sum(recent_values) / len(recent_values)
        older_avg = sum(older_values) / len(older_values)
        
        if recent_avg > older_avg * 1.1:
            trend = "increasing"
        elif recent_avg < older_avg * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "success": True,
            "system": system,
            "metric_type": metric_type,
            "current_value": round(current_value, 2),
            "unit": unit,
            "status": status,
            "trend": trend,
            "time_range": time_range,
            "aggregation": aggregation,
            "thresholds": {
                "warning": threshold_warning,
                "critical": threshold_critical
            },
            "data_points": len(values),
            "timestamp": current_timestamp().isoformat(),
            "recommendations": generate_metric_recommendations(metric_type, current_value, status, trend)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to query metrics: {str(e)}",
            "system": system,
            "metric_type": metric_type
        }


def generate_metric_recommendations(metric_type: str, value: float, status: str, trend: str) -> List[str]:
    """Generate recommendations based on metric analysis."""
    recommendations = []
    
    if status == "critical":
        if metric_type == "cpu":
            recommendations.extend([
                "Immediately investigate high CPU processes",
                "Consider scaling resources or load balancing",
                "Check for inefficient queries or algorithms"
            ])
        elif metric_type == "memory":
            recommendations.extend([
                "Investigate memory leaks or excessive memory usage",
                "Restart services if memory usage is critical",
                "Consider increasing available memory"
            ])
        elif metric_type == "response_time":
            recommendations.extend([
                "Investigate slow database queries or API calls",
                "Check network connectivity and latency",
                "Consider implementing caching or optimization"
            ])
        elif metric_type == "error_rate":
            recommendations.extend([
                "Immediately investigate error logs and causes",
                "Check for recent deployments or configuration changes",
                "Implement circuit breakers or fallback mechanisms"
            ])
    
    elif status == "warning":
        recommendations.extend([
            f"Monitor {metric_type} closely for further increases",
            "Review recent changes that might impact performance",
            "Prepare scaling or optimization measures"
        ])
    
    if trend == "increasing":
        recommendations.append(f"Trend shows {metric_type} is increasing - proactive action recommended")
    
    return recommendations


@tool
def check_system_health_tool(
    systems: List[str],
    include_dependencies: bool = True
) -> Dict[str, Any]:
    """
    Check overall health status of specified systems.
    
    Args:
        systems: List of systems to check
        include_dependencies: Whether to check system dependencies
        
    Returns:
        Dictionary with system health status
    """
    try:
        health_results = []
        
        for system in systems:
            # Mock health check (would be replaced with actual health check integration)
            import random
            
            # Simulate health status
            health_score = random.uniform(0.6, 1.0)
            
            if health_score >= 0.9:
                status = "healthy"
                issues = []
            elif health_score >= 0.7:
                status = "degraded"
                issues = [f"Minor performance issues detected in {system}"]
            else:
                status = "unhealthy"
                issues = [f"Significant issues detected in {system}", "Service may be impacted"]
            
            # Check key metrics
            metrics = {}
            for metric_type in ["cpu", "memory", "response_time"]:
                try:
                    metric_result = query_metrics_tool.invoke({
                        "system": system,
                        "metric_type": metric_type,
                        "time_range": "5m",
                        "aggregation": "avg"
                    })
                    if metric_result["success"]:
                        metrics[metric_type] = {
                            "value": metric_result["current_value"],
                            "status": metric_result["status"],
                            "unit": metric_result["unit"]
                        }
                except Exception as e:
                    # Skip metrics if there's an error
                    pass
            
            # Simulate dependency checks
            dependencies = []
            if include_dependencies:
                dep_names = []
                if system == "api":
                    dep_names = ["database", "auth"]
                elif system == "frontend":
                    dep_names = ["api", "cdn"]
                elif system == "auth":
                    dep_names = ["database"]
                
                for dep in dep_names:
                    dep_health = random.uniform(0.7, 1.0)
                    dep_status = "healthy" if dep_health >= 0.8 else "degraded"
                    dependencies.append({
                        "name": dep,
                        "status": dep_status,
                        "health_score": round(dep_health, 2)
                    })
            
            health_results.append({
                "system": system,
                "status": status,
                "health_score": round(health_score, 2),
                "issues": issues,
                "metrics": metrics,
                "dependencies": dependencies,
                "last_checked": current_timestamp().isoformat()
            })
        
        # Calculate overall health
        overall_scores = [result["health_score"] for result in health_results]
        overall_health = sum(overall_scores) / len(overall_scores)
        
        if overall_health >= 0.9:
            overall_status = "healthy"
        elif overall_health >= 0.7:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return {
            "success": True,
            "overall_status": overall_status,
            "overall_health_score": round(overall_health, 2),
            "systems_checked": len(systems),
            "healthy_systems": len([r for r in health_results if r["status"] == "healthy"]),
            "degraded_systems": len([r for r in health_results if r["status"] == "degraded"]),
            "unhealthy_systems": len([r for r in health_results if r["status"] == "unhealthy"]),
            "system_details": health_results,
            "timestamp": current_timestamp().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to check system health: {str(e)}",
            "systems": systems
        }


@tool
def generate_diagnostic_queries_tool(
    incident_type: str,
    affected_systems: List[str],
    symptoms: List[str]
) -> Dict[str, Any]:
    """
    Generate diagnostic queries and investigation steps.
    
    Args:
        incident_type: Type of incident (performance, outage, error, security)
        affected_systems: List of affected systems
        symptoms: List of observed symptoms
        
    Returns:
        Dictionary with diagnostic queries and investigation steps
    """
    try:
        diagnostic_queries = []
        investigation_steps = []
        
        # Generate queries based on incident type and systems
        for system in affected_systems:
            system_lower = system.lower()
            
            if incident_type == "performance":
                if system_lower in ["api", "backend"]:
                    diagnostic_queries.extend([
                        f"SELECT * FROM {system}_response_times WHERE timestamp > NOW() - INTERVAL 1 HOUR ORDER BY response_time DESC LIMIT 10",
                        f"SELECT endpoint, AVG(response_time) FROM {system}_metrics WHERE timestamp > NOW() - INTERVAL 1 HOUR GROUP BY endpoint ORDER BY AVG(response_time) DESC",
                        f"SELECT * FROM {system}_errors WHERE timestamp > NOW() - INTERVAL 1 HOUR AND error_type = 'timeout'"
                    ])
                    investigation_steps.extend([
                        f"Check {system} response time trends over the last hour",
                        f"Identify slowest endpoints in {system}",
                        f"Review {system} error logs for timeout issues"
                    ])
                
                elif system_lower == "database":
                    diagnostic_queries.extend([
                        "SHOW PROCESSLIST",
                        "SELECT * FROM information_schema.innodb_trx WHERE trx_started < NOW() - INTERVAL 30 SECOND",
                        "SELECT query, exec_count, avg_timer_wait FROM performance_schema.events_statements_summary_by_digest ORDER BY avg_timer_wait DESC LIMIT 10"
                    ])
                    investigation_steps.extend([
                        "Check for long-running database queries",
                        "Identify blocking transactions",
                        "Review slowest database queries"
                    ])
            
            elif incident_type == "outage":
                diagnostic_queries.extend([
                    f"SELECT * FROM {system}_health_checks WHERE timestamp > NOW() - INTERVAL 30 MINUTE AND status != 'healthy'",
                    f"SELECT * FROM {system}_uptime WHERE timestamp > NOW() - INTERVAL 1 HOUR",
                    f"SELECT * FROM infrastructure_events WHERE affected_service = '{system}' AND timestamp > NOW() - INTERVAL 2 HOUR"
                ])
                investigation_steps.extend([
                    f"Check {system} health check failures",
                    f"Review {system} uptime and availability",
                    f"Check infrastructure events affecting {system}"
                ])
            
            elif incident_type == "error":
                diagnostic_queries.extend([
                    f"SELECT error_type, COUNT(*) FROM {system}_errors WHERE timestamp > NOW() - INTERVAL 1 HOUR GROUP BY error_type ORDER BY COUNT(*) DESC",
                    f"SELECT * FROM {system}_errors WHERE timestamp > NOW() - INTERVAL 30 MINUTE ORDER BY timestamp DESC LIMIT 20",
                    f"SELECT * FROM {system}_deployments WHERE deployed_at > NOW() - INTERVAL 24 HOUR ORDER BY deployed_at DESC"
                ])
                investigation_steps.extend([
                    f"Analyze error patterns in {system}",
                    f"Review recent {system} error logs",
                    f"Check recent deployments to {system}"
                ])
            
            elif incident_type == "security":
                diagnostic_queries.extend([
                    f"SELECT * FROM {system}_security_events WHERE timestamp > NOW() - INTERVAL 2 HOUR ORDER BY severity DESC",
                    f"SELECT source_ip, COUNT(*) FROM {system}_access_logs WHERE timestamp > NOW() - INTERVAL 1 HOUR GROUP BY source_ip HAVING COUNT(*) > 100",
                    f"SELECT * FROM {system}_auth_failures WHERE timestamp > NOW() - INTERVAL 1 HOUR ORDER BY timestamp DESC"
                ])
                investigation_steps.extend([
                    f"Review {system} security events",
                    f"Check for suspicious IP addresses accessing {system}",
                    f"Analyze authentication failures in {system}"
                ])
        
        # Add symptom-specific queries
        for symptom in symptoms:
            symptom_lower = symptom.lower()
            
            if "timeout" in symptom_lower:
                diagnostic_queries.append("SELECT * FROM connection_timeouts WHERE timestamp > NOW() - INTERVAL 1 HOUR")
                investigation_steps.append("Investigate connection timeout patterns")
            
            elif "memory" in symptom_lower:
                diagnostic_queries.append("SELECT * FROM memory_usage WHERE timestamp > NOW() - INTERVAL 1 HOUR AND usage_percent > 80")
                investigation_steps.append("Check memory usage spikes")
            
            elif "cpu" in symptom_lower:
                diagnostic_queries.append("SELECT * FROM cpu_usage WHERE timestamp > NOW() - INTERVAL 1 HOUR AND usage_percent > 70")
                investigation_steps.append("Analyze CPU usage patterns")
        
        return {
            "success": True,
            "incident_type": incident_type,
            "affected_systems": affected_systems,
            "symptoms": symptoms,
            "diagnostic_queries": diagnostic_queries,
            "investigation_steps": investigation_steps,
            "total_queries": len(diagnostic_queries),
            "total_steps": len(investigation_steps),
            "timestamp": current_timestamp().isoformat(),
            "next_actions": [
                "Execute diagnostic queries in order of priority",
                "Document findings from each investigation step",
                "Correlate results across different systems",
                "Escalate if patterns indicate broader issues"
            ]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate diagnostic queries: {str(e)}",
            "incident_type": incident_type,
            "affected_systems": affected_systems
        }