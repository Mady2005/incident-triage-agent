"""Team model for incident response team management."""

from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass


class TeamType(Enum):
    """Types of response teams."""
    SRE = "SRE"
    BACKEND = "Backend"
    FRONTEND = "Frontend"
    INFRASTRUCTURE = "Infrastructure"
    SECURITY = "Security"
    DATABASE = "Database"
    DEVOPS = "DevOps"
    NETWORK = "Network"


class TeamAvailability(Enum):
    """Team availability status."""
    AVAILABLE = "available"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"
    ON_CALL = "on_call"


@dataclass
class TeamCapability:
    """Represents a team's capability for handling specific incident types."""
    incident_type: str
    expertise_level: int  # 1-5 scale
    average_response_time: int  # minutes


@dataclass
class TeamMember:
    """Individual team member information."""
    name: str
    role: str
    contact_info: Dict[str, str]
    on_call: bool = False


class ResponseTeam:
    """Model for incident response teams."""
    
    def __init__(
        self,
        name: str,
        team_type: TeamType,
        capabilities: List[TeamCapability],
        escalation_path: List[str],
        members: Optional[List[TeamMember]] = None
    ):
        """Initialize response team."""
        self.name = name
        self.team_type = team_type
        self.capabilities = capabilities
        self.escalation_path = escalation_path
        self.members = members or []
        self.availability = TeamAvailability.AVAILABLE
        self.current_incidents: List[str] = []
        self.workload_score = 0
    
    def can_handle_incident_type(self, incident_type: str) -> bool:
        """Check if team can handle a specific incident type."""
        return any(cap.incident_type == incident_type for cap in self.capabilities)
    
    def get_expertise_level(self, incident_type: str) -> int:
        """Get team's expertise level for an incident type."""
        for capability in self.capabilities:
            if capability.incident_type == incident_type:
                return capability.expertise_level
        return 0
    
    def get_estimated_response_time(self, incident_type: str) -> int:
        """Get estimated response time for an incident type."""
        for capability in self.capabilities:
            if capability.incident_type == incident_type:
                return capability.average_response_time
        return 60  # Default 1 hour
    
    def assign_incident(self, incident_id: str) -> None:
        """Assign an incident to this team."""
        if incident_id not in self.current_incidents:
            self.current_incidents.append(incident_id)
            self._update_workload_score()
    
    def resolve_incident(self, incident_id: str) -> None:
        """Mark an incident as resolved for this team."""
        if incident_id in self.current_incidents:
            self.current_incidents.remove(incident_id)
            self._update_workload_score()
    
    def set_availability(self, availability: TeamAvailability) -> None:
        """Set team availability status."""
        self.availability = availability
    
    def get_on_call_members(self) -> List[TeamMember]:
        """Get list of on-call team members."""
        return [member for member in self.members if member.on_call]
    
    def is_available_for_new_incidents(self) -> bool:
        """Check if team is available for new incident assignments."""
        if self.availability == TeamAvailability.UNAVAILABLE:
            return False
        
        # Consider workload - teams with high workload are less available
        max_concurrent_incidents = 5  # Configurable threshold
        return len(self.current_incidents) < max_concurrent_incidents
    
    def _update_workload_score(self) -> None:
        """Update workload score based on current incidents."""
        self.workload_score = len(self.current_incidents)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert team to dictionary representation."""
        return {
            "name": self.name,
            "team_type": self.team_type.value,
            "availability": self.availability.value,
            "current_incidents": self.current_incidents,
            "workload_score": self.workload_score,
            "escalation_path": self.escalation_path,
            "capabilities": [
                {
                    "incident_type": cap.incident_type,
                    "expertise_level": cap.expertise_level,
                    "average_response_time": cap.average_response_time
                }
                for cap in self.capabilities
            ],
            "members": [
                {
                    "name": member.name,
                    "role": member.role,
                    "on_call": member.on_call
                }
                for member in self.members
            ]
        }


class TeamRegistry:
    """Registry for managing response teams."""
    
    def __init__(self):
        """Initialize team registry."""
        self.teams: Dict[str, ResponseTeam] = {}
        self._initialize_default_teams()
    
    def _initialize_default_teams(self) -> None:
        """Initialize default response teams."""
        # SRE Team
        sre_capabilities = [
            TeamCapability("outage", 5, 5),
            TeamCapability("performance", 4, 10),
            TeamCapability("monitoring", 5, 5),
            TeamCapability("infrastructure", 4, 15)
        ]
        self.register_team(ResponseTeam(
            "SRE",
            TeamType.SRE,
            sre_capabilities,
            ["Infrastructure", "Backend"]
        ))
        
        # Backend Team
        backend_capabilities = [
            TeamCapability("api", 5, 10),
            TeamCapability("database", 4, 15),
            TeamCapability("performance", 4, 20),
            TeamCapability("service", 5, 10)
        ]
        self.register_team(ResponseTeam(
            "Backend",
            TeamType.BACKEND,
            backend_capabilities,
            ["SRE", "Database"]
        ))
        
        # Security Team
        security_capabilities = [
            TeamCapability("security", 5, 5),
            TeamCapability("breach", 5, 2),
            TeamCapability("vulnerability", 5, 10),
            TeamCapability("compliance", 4, 30)
        ]
        self.register_team(ResponseTeam(
            "Security",
            TeamType.SECURITY,
            security_capabilities,
            ["SRE", "Infrastructure"]
        ))
        
        # Infrastructure Team
        infra_capabilities = [
            TeamCapability("infrastructure", 5, 10),
            TeamCapability("network", 4, 15),
            TeamCapability("deployment", 5, 10),
            TeamCapability("scaling", 4, 20)
        ]
        self.register_team(ResponseTeam(
            "Infrastructure",
            TeamType.INFRASTRUCTURE,
            infra_capabilities,
            ["SRE", "DevOps"]
        ))
    
    def register_team(self, team: ResponseTeam) -> None:
        """Register a new response team."""
        self.teams[team.name] = team
    
    def get_team(self, team_name: str) -> Optional[ResponseTeam]:
        """Get a team by name."""
        return self.teams.get(team_name)
    
    def get_available_teams(self) -> List[ResponseTeam]:
        """Get list of available teams."""
        return [team for team in self.teams.values() if team.is_available_for_new_incidents()]
    
    def find_best_team_for_incident(
        self, 
        incident_type: str, 
        severity: str = "medium"
    ) -> Optional[ResponseTeam]:
        """Find the best team for handling an incident."""
        available_teams = self.get_available_teams()
        
        # Filter teams that can handle this incident type
        capable_teams = [
            team for team in available_teams 
            if team.can_handle_incident_type(incident_type)
        ]
        
        if not capable_teams:
            # Fallback to SRE if no specific team can handle it
            return self.get_team("SRE")
        
        # Sort by expertise level (descending) and workload (ascending)
        capable_teams.sort(
            key=lambda t: (-t.get_expertise_level(incident_type), t.workload_score)
        )
        
        return capable_teams[0]
    
    def get_escalation_path(self, team_name: str) -> List[str]:
        """Get escalation path for a team."""
        team = self.get_team(team_name)
        return team.escalation_path if team else []
    
    def list_all_teams(self) -> List[str]:
        """Get list of all team names."""
        return list(self.teams.keys())