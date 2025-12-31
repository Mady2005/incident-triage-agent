"""Incident triage router for severity classification and initial routing decisions."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from ..schemas import SeverityClassificationSchema, IncidentReport
from ..prompts import SEVERITY_CLASSIFICATION_PROMPT
from ..models.incident import Incident, IncidentSeverity
from ..utils import current_timestamp


class TriageRouter:
    """Router for incident triage and severity classification."""
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """Initialize the triage router with an LLM."""
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=1000
        )
        self.historical_incidents: List[Dict[str, Any]] = []
    
    def classify_severity(self, incident_report: IncidentReport) -> SeverityClassificationSchema:
        """
        Classify incident severity using LLM with structured output and historical patterns.
        
        Args:
            incident_report: The incident report to classify
            
        Returns:
            SeverityClassificationSchema with reasoning and classification
            
        Raises:
            ValidationError: If LLM output doesn't match expected schema
        """
        # Format the prompt with incident details
        prompt = SEVERITY_CLASSIFICATION_PROMPT.format(
            title=incident_report.title,
            description=incident_report.description,
            affected_systems=", ".join(incident_report.affected_systems),
            error_logs=incident_report.error_logs or "None provided",
            severity_indicators=", ".join(incident_report.severity_indicators),
            source=incident_report.source,
            reporter=incident_report.reporter
        )
        
        # Get structured output from LLM
        structured_llm = self.llm.with_structured_output(SeverityClassificationSchema)
        
        try:
            initial_result = structured_llm.invoke([HumanMessage(content=prompt)])
            
            # Validate that the result is properly structured
            if not isinstance(initial_result, SeverityClassificationSchema):
                raise ValidationError("LLM did not return expected schema")
            
            # Apply historical patterns to enhance severity assessment (Requirement 1.5)
            enhanced_result = self.apply_historical_patterns_to_severity_assessment(
                incident_report, initial_result
            )
            
            return enhanced_result
            
        except Exception as e:
            # Fallback classification if LLM fails
            fallback_severity = self._fallback_severity_classification(incident_report)
            
            # Still try to apply historical patterns to fallback
            fallback_classification = SeverityClassificationSchema(
                reasoning=f"LLM classification failed ({str(e)}), using fallback heuristics",
                severity=fallback_severity,
                security_incident=self._detect_security_indicators(incident_report),
                affected_systems=incident_report.affected_systems
            )
            
            try:
                return self.apply_historical_patterns_to_severity_assessment(
                    incident_report, fallback_classification
                )
            except Exception:
                # If historical pattern application also fails, return basic fallback
                return fallback_classification
    
    def _fallback_severity_classification(self, incident_report: IncidentReport) -> str:
        """
        Fallback severity classification using heuristics.
        
        Args:
            incident_report: The incident report to classify
            
        Returns:
            Severity level as string
        """
        # Check for critical keywords
        critical_keywords = [
            "outage", "down", "unavailable", "complete failure", "total failure",
            "security breach", "data breach", "unauthorized access", "hack"
        ]
        
        high_keywords = [
            "degraded", "slow", "timeout", "error rate", "partial failure",
            "performance", "latency", "memory leak"
        ]
        
        text_to_check = f"{incident_report.title} {incident_report.description}".lower()
        
        # Critical if security incident or critical keywords
        if self._detect_security_indicators(incident_report):
            return "critical"
        
        if any(keyword in text_to_check for keyword in critical_keywords):
            return "critical"
        
        # High if multiple systems affected or high keywords
        if len(incident_report.affected_systems) > 3:
            return "high"
        
        if any(keyword in text_to_check for keyword in high_keywords):
            return "high"
        
        # Medium if multiple systems or specific indicators
        if len(incident_report.affected_systems) > 1:
            return "medium"
        
        # Default to low
        return "low"
    
    def _detect_security_indicators(self, incident_report: IncidentReport) -> bool:
        """
        Detect if incident has security implications.
        
        Args:
            incident_report: The incident report to analyze
            
        Returns:
            True if security indicators are found
        """
        security_keywords = [
            "security", "breach", "unauthorized", "hack", "malware", "virus",
            "intrusion", "vulnerability", "exploit", "attack", "suspicious",
            "authentication", "authorization", "privilege", "injection",
            "xss", "csrf", "sql injection", "ddos", "phishing"
        ]
        
        text_to_check = f"{incident_report.title} {incident_report.description}".lower()
        
        # Check for security keywords
        if any(keyword in text_to_check for keyword in security_keywords):
            return True
        
        # Check severity indicators
        for indicator in incident_report.severity_indicators:
            if any(keyword in indicator.lower() for keyword in security_keywords):
                return True
        
        # Check affected systems for security-related components
        security_systems = ["auth", "authentication", "authorization", "security", "firewall"]
        for system in incident_report.affected_systems:
            if any(sec_sys in system.lower() for sec_sys in security_systems):
                return True
        
        return False
    
    def should_escalate_immediately(self, classification: SeverityClassificationSchema) -> bool:
        """
        Determine if incident should be escalated immediately.
        
        Args:
            classification: The severity classification result
            
        Returns:
            True if immediate escalation is needed
        """
        # Always escalate critical incidents
        if classification.severity == "critical":
            return True
        
        # Escalate security incidents regardless of severity
        if classification.security_incident:
            return True
        
        # Escalate if many systems are affected
        if len(classification.affected_systems) > 5:
            return True
        
        return False
    
    def get_notification_urgency(self, classification: SeverityClassificationSchema) -> str:
        """
        Get notification urgency level based on classification.
        
        Args:
            classification: The severity classification result
            
        Returns:
            Urgency level: "immediate", "urgent", or "normal"
        """
        if classification.severity == "critical" or classification.security_incident:
            return "immediate"
        elif classification.severity == "high":
            return "urgent"
        else:
            return "normal"
    
    def create_incident_from_classification(
        self, 
        incident_report: IncidentReport, 
        classification: SeverityClassificationSchema
    ) -> Incident:
        """
        Create an Incident object from report and classification.
        
        Args:
            incident_report: The original incident report
            classification: The severity classification result
            
        Returns:
            Incident object with severity and security flags set
        """
        incident = Incident(incident_report)
        
        # Set severity with reasoning
        incident.set_severity(classification.severity, classification.reasoning)
        
        # Mark as security incident if detected
        if classification.security_incident:
            incident.mark_as_security_incident()
        
        # Set escalation flag if needed
        if self.should_escalate_immediately(classification):
            incident.escalate(
                escalation_reason="Automatic escalation due to severity or security implications",
                target_team=None
            )
        
        return incident
    
    def prioritize_incidents(self, incidents: List[Incident]) -> List[Incident]:
        """
        Sort incidents by priority (severity and impact scope).
        Implements Requirements 1.2: Order incidents by severity and impact scope.
        
        Args:
            incidents: List of incidents to prioritize
            
        Returns:
            List of incidents sorted by priority (highest first)
        """
        return prioritize_incidents_with_impact_scope(incidents)
    
    def detect_critical_incidents(self, incidents: List[Incident]) -> List[Incident]:
        """
        Filter incidents that require immediate notification to primary on-call engineer.
        Implements Requirements 1.3: Immediately notify primary on-call for critical incidents.
        
        Args:
            incidents: List of incidents to check
            
        Returns:
            List of incidents requiring immediate notification, sorted by priority
        """
        return detect_critical_incidents_with_notification(incidents)
    
    def find_similar_incidents(self, incident: Incident) -> List[Dict[str, Any]]:
        """
        Find similar historical incidents for pattern matching.
        Implements Requirements 1.5: Reference historical patterns in severity assessment.
        
        Args:
            incident: Current incident to match against historical data
            
        Returns:
            List of similar incidents with similarity scores, pattern insights, and severity references
        """
        return match_historical_patterns_with_severity_reference(incident, self.historical_incidents)
    
    def add_historical_incident(self, incident_data: Dict[str, Any]) -> None:
        """
        Add incident to historical data for pattern matching.
        
        Args:
            incident_data: Dictionary containing incident information
        """
        self.historical_incidents.append(incident_data)
    
    def set_historical_incidents(self, historical_data: List[Dict[str, Any]]) -> None:
        """
        Set the complete historical incidents dataset.
        
        Args:
            historical_data: List of historical incident dictionaries
        """
        self.historical_incidents = historical_data
    
    def get_incident_priority_order(self, incidents: List[Incident]) -> List[str]:
        """
        Get the priority order of incident IDs based on severity and impact.
        
        Args:
            incidents: List of incidents to order
            
        Returns:
            List of incident IDs in priority order (highest priority first)
        """
        prioritized = self.prioritize_incidents(incidents)
        return [incident.report.id for incident in prioritized]
    
    def should_notify_immediately(self, incident: Incident) -> bool:
        """
        Determine if an incident requires immediate notification.
        
        Args:
            incident: The incident to evaluate
            
        Returns:
            True if immediate notification is required
        """
        # Critical incidents always need immediate notification
        if incident.severity == IncidentSeverity.CRITICAL:
            return True
        
        # Security incidents need immediate notification
        if incident.is_security_incident:
            return True
        
        # Incidents affecting many systems need immediate notification
        if len(incident.report.affected_systems) > 5:
            return True
        
        # Escalated incidents need immediate notification
        if incident.escalation_needed:
            return True
        
        return False
    
    def process_incident_batch_with_prioritization(self, incidents: List[Incident]) -> Dict[str, Any]:
        """
        Process a batch of incidents with comprehensive prioritization and ordering.
        Implements Requirements 1.2, 1.3, 1.5: Complete incident prioritization workflow.
        
        Args:
            incidents: List of incidents to process and prioritize
            
        Returns:
            Dictionary containing prioritized incidents, critical notifications, and historical insights
        """
        if not incidents:
            return {
                "prioritized_incidents": [],
                "critical_incidents": [],
                "immediate_notifications": [],
                "historical_insights": {},
                "processing_summary": {
                    "total_incidents": 0,
                    "critical_count": 0,
                    "security_count": 0,
                    "immediate_notification_count": 0
                }
            }
        
        # Step 1: Prioritize all incidents by severity and impact scope (Requirement 1.2)
        prioritized_incidents = self.prioritize_incidents(incidents)
        
        # Step 2: Detect critical incidents requiring immediate notification (Requirement 1.3)
        critical_incidents = self.detect_critical_incidents(incidents)
        
        # Step 3: Generate immediate notifications for critical incidents
        immediate_notifications = []
        for incident in critical_incidents:
            notification = {
                "incident_id": incident.report.id,
                "severity": incident.severity.value if incident.severity else "unknown",
                "notification_reason": getattr(incident, 'notification_metadata', {}).get('notification_reason', 'Critical incident detected'),
                "recipients": self.get_notification_recipients(incident),
                "urgency": "immediate",
                "message": f"CRITICAL: {incident.report.title} - {incident.report.description[:100]}...",
                "affected_systems": incident.report.affected_systems,
                "is_security_incident": incident.is_security_incident
            }
            immediate_notifications.append(notification)
        
        # Step 4: Apply historical pattern matching for enhanced insights (Requirement 1.5)
        historical_insights = {}
        for incident in prioritized_incidents[:5]:  # Apply to top 5 priority incidents
            similar_incidents = self.find_similar_incidents(incident)
            if similar_incidents:
                historical_insights[incident.report.id] = {
                    "similar_count": len(similar_incidents),
                    "top_similarity_score": similar_incidents[0]["similarity_score"],
                    "severity_guidance": similar_incidents[0].get("severity_assessment_guidance", {}),
                    "pattern_insights": similar_incidents[0].get("pattern_insights", []),
                    "severity_references": similar_incidents[0].get("severity_references", [])
                }
        
        # Step 5: Generate processing summary
        security_count = sum(1 for inc in incidents if inc.is_security_incident)
        processing_summary = {
            "total_incidents": len(incidents),
            "critical_count": len(critical_incidents),
            "security_count": security_count,
            "immediate_notification_count": len(immediate_notifications),
            "prioritization_timestamp": current_timestamp().isoformat(),
            "severity_distribution": self._get_severity_distribution(incidents),
            "system_impact_analysis": self._get_system_impact_analysis(incidents)
        }
        
        return {
            "prioritized_incidents": [inc.to_dict() for inc in prioritized_incidents],
            "critical_incidents": [inc.to_dict() for inc in critical_incidents],
            "immediate_notifications": immediate_notifications,
            "historical_insights": historical_insights,
            "processing_summary": processing_summary
        }
    
    def _get_severity_distribution(self, incidents: List[Incident]) -> Dict[str, int]:
        """Get distribution of incidents by severity level."""
        distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
        for incident in incidents:
            severity = incident.severity.value if incident.severity else "unknown"
            distribution[severity] += 1
        return distribution
    
    def _get_system_impact_analysis(self, incidents: List[Incident]) -> Dict[str, Any]:
        """Analyze system impact across all incidents."""
        system_counts = {}
        total_systems_affected = 0
        
        for incident in incidents:
            total_systems_affected += len(incident.report.affected_systems)
            for system in incident.report.affected_systems:
                system_counts[system] = system_counts.get(system, 0) + 1
        
        # Find most impacted systems
        top_systems = sorted(system_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_systems_affected": total_systems_affected,
            "unique_systems_count": len(system_counts),
            "average_systems_per_incident": total_systems_affected / max(len(incidents), 1),
            "most_impacted_systems": top_systems,
            "widespread_impact_incidents": len([inc for inc in incidents if len(inc.report.affected_systems) > 3])
        }
    
    def get_notification_recipients(self, incident: Incident) -> List[str]:
        """
        Get list of notification recipients based on incident characteristics.
        
        Args:
            incident: The incident to determine recipients for
            
        Returns:
            List of recipient identifiers (teams, individuals, etc.)
        """
        recipients = []
        
        # Always notify primary on-call for critical incidents
        if incident.severity == IncidentSeverity.CRITICAL:
            recipients.append("primary-oncall")
        
        # Security incidents notify security team
        if incident.is_security_incident:
            recipients.extend(["security-team", "security-oncall"])
        
        # High severity incidents notify team leads
        if incident.severity in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH]:
            recipients.append("team-leads")
        
        # Incidents affecting multiple systems notify SRE team
        if len(incident.report.affected_systems) > 3:
            recipients.append("sre-team")
        
        return list(set(recipients))  # Remove duplicates
        """
        Get list of notification recipients based on incident characteristics.
        
        Args:
            incident: The incident to determine recipients for
            
        Returns:
            List of recipient identifiers (teams, individuals, etc.)
        """
        recipients = []
        
        # Always notify primary on-call for critical incidents
        if incident.severity == IncidentSeverity.CRITICAL:
            recipients.append("primary-oncall")
        
        # Security incidents notify security team
        if incident.is_security_incident:
            recipients.extend(["security-team", "security-oncall"])
        
        # High severity incidents notify team leads
        if incident.severity in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH]:
            recipients.append("team-leads")
        
        # Incidents affecting multiple systems notify SRE team
        if len(incident.report.affected_systems) > 3:
            recipients.append("sre-team")
        
        return list(set(recipients))  # Remove duplicates
    
    def apply_historical_patterns_to_severity_assessment(
        self, 
        incident_report: IncidentReport, 
        initial_classification: SeverityClassificationSchema
    ) -> SeverityClassificationSchema:
        """
        Apply historical patterns to enhance severity assessment.
        Implements Requirement 1.5: Reference historical patterns in severity assessment.
        
        Args:
            incident_report: The incident report being classified
            initial_classification: Initial severity classification from LLM
            
        Returns:
            Enhanced classification with historical pattern insights
        """
        # Create temporary incident for pattern matching
        temp_incident = Incident(incident_report)
        temp_incident.set_severity(initial_classification.severity, initial_classification.reasoning)
        if initial_classification.security_incident:
            temp_incident.mark_as_security_incident()
        
        # Find similar historical incidents
        similar_incidents = self.find_similar_incidents(temp_incident)
        
        if not similar_incidents:
            # No historical patterns found, return original classification
            return initial_classification
        
        # Analyze historical patterns for severity insights
        historical_severities = []
        pattern_insights = []
        severity_adjustments = []
        
        for similar in similar_incidents:
            hist_severity = similar.get("severity")
            similarity_score = similar.get("similarity_score", 0)
            severity_refs = similar.get("severity_references", [])
            
            if hist_severity and similarity_score > 0.4:  # High confidence matches
                historical_severities.append((hist_severity, similarity_score))
                pattern_insights.extend(severity_refs)
        
        # Determine if severity should be adjusted based on patterns
        if historical_severities:
            # Weight historical severities by similarity score
            severity_weights = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            current_weight = severity_weights.get(initial_classification.severity, 2)
            
            weighted_historical_score = 0
            total_weight = 0
            
            for hist_sev, sim_score in historical_severities:
                hist_weight = severity_weights.get(hist_sev, 2)
                weighted_historical_score += hist_weight * sim_score
                total_weight += sim_score
            
            if total_weight > 0:
                avg_historical_weight = weighted_historical_score / total_weight
                
                # Suggest severity adjustment if historical pattern differs significantly
                if abs(avg_historical_weight - current_weight) >= 1.0:
                    if avg_historical_weight > current_weight:
                        severity_adjustments.append("Historical patterns suggest higher severity")
                    else:
                        severity_adjustments.append("Historical patterns suggest lower severity")
        
        # Enhanced reasoning with historical context
        enhanced_reasoning = initial_classification.reasoning
        
        if pattern_insights:
            enhanced_reasoning += f"\n\nHistorical Pattern Analysis:\n"
            for insight in pattern_insights[:3]:  # Top 3 insights
                enhanced_reasoning += f"- {insight}\n"
        
        if severity_adjustments:
            enhanced_reasoning += f"\nSeverity Assessment Notes:\n"
            for adjustment in severity_adjustments:
                enhanced_reasoning += f"- {adjustment}\n"
        
        # Add pattern match summary
        if similar_incidents:
            match_count = len(similar_incidents)
            top_similarity = similar_incidents[0].get("similarity_score", 0)
            enhanced_reasoning += f"\nFound {match_count} similar historical incidents (top match: {top_similarity:.2f} similarity)"
        
        return SeverityClassificationSchema(
            reasoning=enhanced_reasoning,
            severity=initial_classification.severity,  # Keep original severity for now
            security_incident=initial_classification.security_incident,
            affected_systems=initial_classification.affected_systems
        )


def prioritize_incidents(incidents: List[Incident]) -> List[Incident]:
    """
    Sort incidents by priority (severity and impact).
    
    Args:
        incidents: List of incidents to prioritize
        
    Returns:
        List of incidents sorted by priority (highest first)
    """
    def get_priority_score(incident: Incident) -> tuple:
        """Get priority score for sorting."""
        # Primary sort by severity (critical=4, high=3, medium=2, low=1)
        severity_scores = {
            IncidentSeverity.CRITICAL: 4,
            IncidentSeverity.HIGH: 3,
            IncidentSeverity.MEDIUM: 2,
            IncidentSeverity.LOW: 1
        }
        
        severity_score = severity_scores.get(incident.severity, 0)
        
        # Security incidents get priority boost
        security_boost = 1 if incident.is_security_incident else 0
        
        # More affected systems = higher priority
        system_count = len(incident.report.affected_systems)
        
        # Escalated incidents get priority boost
        escalation_boost = 1 if incident.escalation_needed else 0
        
        # Earlier incidents get slight priority (negative timestamp for reverse sort)
        time_priority = -incident.created_at.timestamp()
        
        # Calculate composite priority score
        composite_score = (severity_score + security_boost + escalation_boost) * 100 + system_count
        
        return (composite_score, time_priority)
    
    return sorted(incidents, key=get_priority_score, reverse=True)


def detect_critical_incidents(incidents: List[Incident]) -> List[Incident]:
    """
    Filter incidents that require immediate notification.
    
    Args:
        incidents: List of incidents to check
        
    Returns:
        List of incidents requiring immediate notification
    """
    critical_incidents = []
    
    for incident in incidents:
        requires_immediate_notification = False
        
        # Critical severity incidents
        if incident.severity == IncidentSeverity.CRITICAL:
            requires_immediate_notification = True
        
        # Security incidents regardless of severity
        elif incident.is_security_incident:
            requires_immediate_notification = True
        
        # Incidents affecting many systems (potential widespread impact)
        elif len(incident.report.affected_systems) > 5:
            requires_immediate_notification = True
        
        # Escalated incidents
        elif incident.escalation_needed:
            requires_immediate_notification = True
        
        # High severity incidents affecting critical systems
        elif (incident.severity == IncidentSeverity.HIGH and 
              any(system.lower() in ["auth", "payment", "database", "core"] 
                  for system in incident.report.affected_systems)):
            requires_immediate_notification = True
        
        if requires_immediate_notification:
            critical_incidents.append(incident)
    
    # Sort critical incidents by priority
    return prioritize_incidents(critical_incidents)


def match_historical_patterns(
    incident: Incident, 
    historical_incidents: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Find similar historical incidents for pattern matching.
    
    Args:
        incident: Current incident to match
        historical_incidents: List of historical incident data
        
    Returns:
        List of similar incidents with similarity scores and pattern insights
    """
    if not historical_incidents:
        return []
    
    similar_incidents = []
    current_title = incident.report.title.lower()
    current_systems = set(system.lower() for system in incident.report.affected_systems)
    current_description = incident.report.description.lower()
    
    for hist_incident in historical_incidents:
        similarity_score = 0
        pattern_insights = []
        
        # Title similarity (weighted keyword matching)
        hist_title = hist_incident.get("title", "").lower()
        title_words = set(word for word in current_title.split() if len(word) > 3)  # Filter short words
        hist_title_words = set(word for word in hist_title.split() if len(word) > 3)
        
        common_title_words = title_words & hist_title_words
        if common_title_words:
            title_similarity = len(common_title_words) / max(len(title_words), len(hist_title_words), 1)
            similarity_score += 0.3 * title_similarity
            pattern_insights.append(f"Similar keywords: {', '.join(common_title_words)}")
        
        # System overlap (exact and partial matches)
        hist_systems = set(system.lower() for system in hist_incident.get("affected_systems", []))
        exact_system_overlap = len(current_systems & hist_systems)
        
        if exact_system_overlap > 0:
            system_similarity = exact_system_overlap / max(len(current_systems), len(hist_systems), 1)
            similarity_score += 0.4 * system_similarity
            pattern_insights.append(f"Common systems: {', '.join(current_systems & hist_systems)}")
        
        # Partial system name matching (e.g., "api-gateway" matches "api")
        partial_matches = 0
        for curr_sys in current_systems:
            for hist_sys in hist_systems:
                if curr_sys in hist_sys or hist_sys in curr_sys:
                    partial_matches += 1
                    break
        
        if partial_matches > 0:
            similarity_score += 0.1 * (partial_matches / max(len(current_systems), 1))
        
        # Severity pattern matching
        if incident.severity and hist_incident.get("severity") == incident.severity.value:
            similarity_score += 0.15
            pattern_insights.append(f"Same severity level: {incident.severity.value}")
        
        # Security incident pattern
        hist_security = hist_incident.get("is_security_incident", False)
        if hist_security == incident.is_security_incident and incident.is_security_incident:
            similarity_score += 0.1
            pattern_insights.append("Both are security incidents")
        
        # Description similarity (enhanced keyword matching)
        hist_description = hist_incident.get("description", "").lower()
        desc_words = set(word for word in current_description.split() if len(word) > 4)  # Filter short words
        hist_desc_words = set(word for word in hist_description.split() if len(word) > 4)
        
        common_desc_words = desc_words & hist_desc_words
        if len(common_desc_words) >= 2:  # At least 2 meaningful common words
            desc_similarity = len(common_desc_words) / max(len(desc_words), len(hist_desc_words), 1)
            similarity_score += 0.15 * desc_similarity
            pattern_insights.append(f"Similar description terms: {', '.join(list(common_desc_words)[:3])}")
        
        # Time-based patterns (if resolution time is available)
        hist_resolution_time = hist_incident.get("resolution_time_minutes")
        if hist_resolution_time:
            pattern_insights.append(f"Historical resolution time: {hist_resolution_time} minutes")
        
        # Resolution approach patterns
        hist_resolution_actions = hist_incident.get("resolution_actions", [])
        if hist_resolution_actions:
            pattern_insights.append(f"Previous resolution approaches: {len(hist_resolution_actions)} actions taken")
        
        # Only include if similarity is above threshold
        if similarity_score > 0.25:  # Lowered threshold for better matching
            similar_incidents.append({
                **hist_incident,
                "similarity_score": similarity_score,
                "pattern_insights": pattern_insights,
                "match_confidence": "high" if similarity_score > 0.6 else "medium" if similarity_score > 0.4 else "low"
            })
    
    # Sort by similarity score (highest first)
    similar_incidents.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    # Return top 5 most similar with enhanced pattern information
    return similar_incidents[:5]


def prioritize_incidents_with_impact_scope(incidents: List[Incident]) -> List[Incident]:
    """
    Sort incidents by priority considering severity and impact scope.
    Enhanced version that considers impact scope more comprehensively.
    
    Args:
        incidents: List of incidents to prioritize
        
    Returns:
        List of incidents sorted by priority (highest first)
    """
    def get_enhanced_priority_score(incident: Incident) -> tuple:
        """Get enhanced priority score for sorting with impact scope consideration."""
        # Primary sort by severity (critical=4, high=3, medium=2, low=1)
        severity_scores = {
            IncidentSeverity.CRITICAL: 4,
            IncidentSeverity.HIGH: 3,
            IncidentSeverity.MEDIUM: 2,
            IncidentSeverity.LOW: 1
        }
        
        severity_score = severity_scores.get(incident.severity, 0)
        
        # Security incidents get priority boost
        security_boost = 1 if incident.is_security_incident else 0
        
        # Impact scope calculation - more sophisticated than just system count
        system_count = len(incident.report.affected_systems)
        
        # Critical systems get higher impact score
        critical_systems = {"auth", "payment", "database", "core", "api-gateway", "load-balancer"}
        critical_system_count = sum(1 for system in incident.report.affected_systems 
                                  if any(crit in system.lower() for crit in critical_systems))
        
        # Impact scope score: base system count + critical system multiplier
        impact_scope_score = system_count + (critical_system_count * 2)
        
        # Escalated incidents get priority boost
        escalation_boost = 2 if incident.escalation_needed else 0
        
        # Time-based priority - older incidents get slight boost to prevent starvation
        time_priority = -incident.created_at.timestamp()
        
        # Calculate composite priority score
        # Format: (severity + security + escalation) * 1000 + impact_scope * 10 + time_factor
        composite_score = (severity_score + security_boost + escalation_boost) * 1000 + impact_scope_score * 10
        
        return (composite_score, time_priority)
    
    return sorted(incidents, key=get_enhanced_priority_score, reverse=True)


def detect_critical_incidents_with_notification(incidents: List[Incident]) -> List[Incident]:
    """
    Filter incidents that require immediate notification to primary on-call engineer.
    Enhanced version that ensures critical severity incidents trigger immediate notification.
    
    Args:
        incidents: List of incidents to check
        
    Returns:
        List of incidents requiring immediate notification, sorted by priority
    """
    critical_incidents = []
    
    for incident in incidents:
        requires_immediate_notification = False
        notification_reason = ""
        
        # Critical severity incidents - ALWAYS require immediate notification (Requirement 1.3)
        if incident.severity == IncidentSeverity.CRITICAL:
            requires_immediate_notification = True
            notification_reason = "Critical severity incident detected"
        
        # Security incidents regardless of severity - immediate notification
        elif incident.is_security_incident:
            requires_immediate_notification = True
            notification_reason = "Security incident detected"
        
        # Incidents affecting many systems (potential widespread impact)
        elif len(incident.report.affected_systems) > 5:
            requires_immediate_notification = True
            notification_reason = "Widespread system impact detected"
        
        # Escalated incidents - already determined to need escalation
        elif incident.escalation_needed:
            requires_immediate_notification = True
            notification_reason = "Incident escalation required"
        
        # High severity incidents affecting critical systems
        elif (incident.severity == IncidentSeverity.HIGH and 
              any(system.lower() in ["auth", "payment", "database", "core"] 
                  for system in incident.report.affected_systems)):
            requires_immediate_notification = True
            notification_reason = "High severity incident affecting critical systems"
        
        # Multiple high/critical incidents in short timeframe (cascade detection)
        elif incident.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]:
            # Check for other high/critical incidents in last 30 minutes
            from datetime import timedelta
            recent_threshold = incident.created_at - timedelta(minutes=30)
            recent_critical_count = sum(1 for inc in incidents 
                                      if inc.severity in [IncidentSeverity.HIGH, IncidentSeverity.CRITICAL]
                                      and inc.created_at >= recent_threshold
                                      and inc.report.id != incident.report.id)
            
            if recent_critical_count >= 2:  # 3+ high/critical incidents in 30 min
                requires_immediate_notification = True
                notification_reason = "Multiple critical incidents detected - potential cascade"
        
        if requires_immediate_notification:
            # Add notification metadata to incident for tracking
            if not hasattr(incident, 'notification_metadata'):
                incident.notification_metadata = {}
            
            incident.notification_metadata.update({
                'requires_immediate_notification': True,
                'notification_reason': notification_reason,
                'notification_recipients': ['primary-oncall'],
                'notification_urgency': 'immediate'
            })
            
            critical_incidents.append(incident)
    
    # Sort critical incidents by priority using enhanced prioritization
    return prioritize_incidents_with_impact_scope(critical_incidents)


def match_historical_patterns_with_severity_reference(
    incident: Incident, 
    historical_incidents: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Find similar historical incidents and reference patterns in severity assessment.
    Enhanced version that provides severity assessment insights from historical patterns.
    
    Args:
        incident: Current incident to match
        historical_incidents: List of historical incident data
        
    Returns:
        List of similar incidents with similarity scores, pattern insights, and severity references
    """
    if not historical_incidents:
        return []
    
    similar_incidents = []
    current_title = incident.report.title.lower()
    current_systems = set(system.lower() for system in incident.report.affected_systems)
    current_description = incident.report.description.lower()
    
    for hist_incident in historical_incidents:
        similarity_score = 0
        pattern_insights = []
        severity_references = []
        
        # Title similarity (weighted keyword matching)
        hist_title = hist_incident.get("title", "").lower()
        title_words = set(word for word in current_title.split() if len(word) > 3)
        hist_title_words = set(word for word in hist_title.split() if len(word) > 3)
        
        common_title_words = title_words & hist_title_words
        if common_title_words:
            title_similarity = len(common_title_words) / max(len(title_words), len(hist_title_words), 1)
            similarity_score += 0.3 * title_similarity
            pattern_insights.append(f"Similar keywords: {', '.join(common_title_words)}")
        
        # System overlap (exact and partial matches)
        hist_systems = set(system.lower() for system in hist_incident.get("affected_systems", []))
        exact_system_overlap = len(current_systems & hist_systems)
        
        if exact_system_overlap > 0:
            system_similarity = exact_system_overlap / max(len(current_systems), len(hist_systems), 1)
            similarity_score += 0.4 * system_similarity
            pattern_insights.append(f"Common systems: {', '.join(current_systems & hist_systems)}")
        
        # Partial system name matching
        partial_matches = 0
        for curr_sys in current_systems:
            for hist_sys in hist_systems:
                if curr_sys in hist_sys or hist_sys in curr_sys:
                    partial_matches += 1
                    break
        
        if partial_matches > 0:
            similarity_score += 0.1 * (partial_matches / max(len(current_systems), 1))
        
        # Severity pattern matching with reference insights
        hist_severity = hist_incident.get("severity")
        if hist_severity:
            if incident.severity and hist_severity == incident.severity.value:
                similarity_score += 0.15
                severity_references.append(f"Historical severity matches current: {hist_severity}")
            elif incident.severity:
                # Provide severity reference even if different
                severity_references.append(
                    f"Historical severity was {hist_severity}, current is {incident.severity.value}"
                )
            else:
                # Suggest severity based on historical pattern
                severity_references.append(
                    f"Similar incidents were typically classified as {hist_severity}"
                )
        
        # Security incident pattern
        hist_security = hist_incident.get("is_security_incident", False)
        if hist_security == incident.is_security_incident and incident.is_security_incident:
            similarity_score += 0.1
            pattern_insights.append("Both are security incidents")
            severity_references.append("Security incidents typically require immediate escalation")
        elif hist_security and not incident.is_security_incident:
            severity_references.append("Similar incidents had security implications - review for security indicators")
        
        # Description similarity (enhanced keyword matching)
        hist_description = hist_incident.get("description", "").lower()
        desc_words = set(word for word in current_description.split() if len(word) > 4)
        hist_desc_words = set(word for word in hist_description.split() if len(word) > 4)
        
        common_desc_words = desc_words & hist_desc_words
        if len(common_desc_words) >= 2:
            desc_similarity = len(common_desc_words) / max(len(desc_words), len(hist_desc_words), 1)
            similarity_score += 0.15 * desc_similarity
            pattern_insights.append(f"Similar description terms: {', '.join(list(common_desc_words)[:3])}")
        
        # Resolution time patterns for severity assessment
        hist_resolution_time = hist_incident.get("resolution_time_minutes")
        if hist_resolution_time:
            if hist_resolution_time < 30:
                severity_references.append("Similar incidents were resolved quickly (< 30 min) - may indicate lower severity")
            elif hist_resolution_time > 240:  # 4 hours
                severity_references.append("Similar incidents took extended time (> 4 hours) - may indicate higher complexity")
            else:
                severity_references.append(f"Similar incidents typically resolved in {hist_resolution_time} minutes")
        
        # Resolution approach patterns
        hist_resolution_actions = hist_incident.get("resolution_actions", [])
        if hist_resolution_actions:
            pattern_insights.append(f"Previous resolution approaches: {len(hist_resolution_actions)} actions taken")
            
            # Extract common resolution patterns
            action_types = [action.get("action_type", "") for action in hist_resolution_actions if isinstance(action, dict)]
            if action_types:
                severity_references.append(f"Common resolution actions: {', '.join(set(action_types))}")
        
        # Escalation patterns
        hist_escalated = hist_incident.get("escalation_needed", False)
        if hist_escalated:
            severity_references.append("Similar incidents required escalation - consider higher severity")
        
        # Impact scope patterns
        hist_system_count = len(hist_incident.get("affected_systems", []))
        current_system_count = len(incident.report.affected_systems)
        
        if hist_system_count > current_system_count:
            severity_references.append(f"Similar incidents affected more systems ({hist_system_count} vs {current_system_count}) - monitor for spread")
        elif hist_system_count < current_system_count:
            severity_references.append(f"Current incident affects more systems than similar historical incidents - consider higher severity")
        
        # Only include if similarity is above threshold
        if similarity_score > 0.25:
            similar_incidents.append({
                **hist_incident,
                "similarity_score": similarity_score,
                "pattern_insights": pattern_insights,
                "severity_references": severity_references,
                "match_confidence": "high" if similarity_score > 0.6 else "medium" if similarity_score > 0.4 else "low",
                "severity_assessment_guidance": {
                    "historical_severity": hist_severity,
                    "resolution_time_pattern": hist_resolution_time,
                    "escalation_pattern": hist_escalated,
                    "system_impact_comparison": {
                        "historical_systems": hist_system_count,
                        "current_systems": current_system_count
                    }
                }
            })
    
    # Sort by similarity score (highest first)
    similar_incidents.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    # Return top 5 most similar with enhanced severity assessment guidance
    return similar_incidents[:5]


def get_incident_trends(incidents: List[Incident], time_window_hours: int = 24) -> Dict[str, Any]:
    """
    Analyze incident trends over a time window.
    
    Args:
        incidents: List of incidents to analyze
        time_window_hours: Time window for trend analysis in hours
        
    Returns:
        Dictionary containing trend analysis
    """
    from datetime import timedelta
    
    if not incidents:
        return {"total_incidents": 0, "trends": {}}
    
    # Filter incidents within time window
    now = current_timestamp()
    cutoff_time = now - timedelta(hours=time_window_hours)
    recent_incidents = [inc for inc in incidents if inc.created_at >= cutoff_time]
    
    # Analyze trends
    severity_counts = {}
    system_counts = {}
    security_count = 0
    
    for incident in recent_incidents:
        # Count by severity
        severity = incident.severity.value if incident.severity else "unknown"
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Count by affected systems
        for system in incident.report.affected_systems:
            system_counts[system] = system_counts.get(system, 0) + 1
        
        # Count security incidents
        if incident.is_security_incident:
            security_count += 1
    
    # Identify concerning trends
    alerts = []
    if severity_counts.get("critical", 0) > 2:
        alerts.append(f"High number of critical incidents: {severity_counts['critical']}")
    
    if security_count > 1:
        alerts.append(f"Multiple security incidents: {security_count}")
    
    # Find most affected systems
    top_systems = sorted(system_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    return {
        "total_incidents": len(recent_incidents),
        "time_window_hours": time_window_hours,
        "severity_distribution": severity_counts,
        "most_affected_systems": top_systems,
        "security_incidents": security_count,
        "trend_alerts": alerts,
        "average_systems_per_incident": sum(len(inc.report.affected_systems) for inc in recent_incidents) / max(len(recent_incidents), 1)
    }