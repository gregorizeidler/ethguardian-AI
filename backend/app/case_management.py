"""
Case Management System
- Create and manage investigation cases
- Role-Based Access Control (RBAC)
- Evidence collection and chain of custody
- Investigation templates and playbooks
- Task assignment
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import uuid


class CaseStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CasePriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UserRole(Enum):
    ANALYST = "analyst"
    SENIOR_ANALYST = "senior_analyst"
    MANAGER = "manager"
    ADMIN = "admin"
    AUDITOR = "auditor"


class CaseManagementSystem:
    """Comprehensive case management for AML investigations"""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        
        # Role permissions
        self.permissions = {
            UserRole.ANALYST: ["view_case", "add_evidence", "add_comment"],
            UserRole.SENIOR_ANALYST: ["view_case", "create_case", "add_evidence", "assign_task", "add_comment", "update_case"],
            UserRole.MANAGER: ["view_all_cases", "create_case", "assign_case", "approve_case", "close_case", "add_evidence", "assign_task", "add_comment", "update_case"],
            UserRole.ADMIN: ["*"],  # All permissions
            UserRole.AUDITOR: ["view_all_cases", "view_audit_trail"]
        }
        
        # Investigation templates
        self.templates = {
            "money_laundering": {
                "name": "Money Laundering Investigation",
                "steps": [
                    "Identify suspicious transactions",
                    "Trace fund origins",
                    "Map transaction network",
                    "Identify layering patterns",
                    "Document evidence",
                    "Prepare SAR report"
                ],
                "checklist": [
                    "Transaction history collected",
                    "Network graph analyzed",
                    "Patterns identified",
                    "Evidence documented",
                    "Report filed"
                ]
            },
            "fraud": {
                "name": "Fraud Investigation",
                "steps": [
                    "Document fraud indicators",
                    "Identify victims",
                    "Track stolen funds",
                    "Analyze attacker patterns",
                    "Collect evidence",
                    "Coordinate with law enforcement"
                ],
                "checklist": [
                    "Fraud type identified",
                    "Victims contacted",
                    "Funds traced",
                    "Evidence secured",
                    "Authorities notified"
                ]
            },
            "sanctions_screening": {
                "name": "Sanctions Screening Investigation",
                "steps": [
                    "Check OFAC list",
                    "Verify entity identity",
                    "Assess exposure",
                    "Document findings",
                    "File compliance report"
                ],
                "checklist": [
                    "Sanctions status verified",
                    "Risk assessed",
                    "Compliance documented"
                ]
            }
        }
    
    def create_case(self, title: str, address: str, case_type: str, priority: str, 
                    assigned_to: str, created_by: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new investigation case"""
        case_id = str(uuid.uuid4())
        timestamp = int(datetime.now().timestamp())
        
        # Get template if applicable
        template = self.templates.get(case_type, {})
        
        query = """
        CREATE (c:Case {
            case_id: $case_id,
            title: $title,
            address: $address,
            case_type: $case_type,
            priority: $priority,
            status: 'open',
            assigned_to: $assigned_to,
            created_by: $created_by,
            description: $description,
            created_at: $timestamp,
            updated_at: $timestamp,
            template_steps: $template_steps,
            template_checklist: $template_checklist
        })
        WITH c
        MATCH (a:Address {address: $address})
        CREATE (c)-[:INVESTIGATES]->(a)
        RETURN c
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                case_id=case_id,
                title=title,
                address=address,
                case_type=case_type,
                priority=priority,
                assigned_to=assigned_to,
                created_by=created_by,
                description=description or "",
                timestamp=timestamp,
                template_steps=template.get("steps", []),
                template_checklist=template.get("checklist", [])
            )
            
            # Log action
            self._log_action(
                case_id=case_id,
                user=created_by,
                action="case_created",
                details=f"Case created: {title}"
            )
            
            return {
                "case_id": case_id,
                "title": title,
                "address": address,
                "case_type": case_type,
                "priority": priority,
                "status": "open",
                "assigned_to": assigned_to,
                "created_by": created_by,
                "created_at": timestamp,
                "template": template,
                "message": "Case created successfully"
            }
    
    def get_case(self, case_id: str, user: str, user_role: str) -> Dict[str, Any]:
        """Get case details"""
        role = UserRole(user_role)
        
        # Check permissions
        if not self._has_permission(role, "view_case"):
            return {"error": "Insufficient permissions"}
        
        query = """
        MATCH (c:Case {case_id: $case_id})
        OPTIONAL MATCH (c)-[:INVESTIGATES]->(a:Address)
        OPTIONAL MATCH (c)-[:HAS_EVIDENCE]->(e:Evidence)
        OPTIONAL MATCH (c)<-[:ASSIGNED_TO]-(t:Task)
        RETURN c, 
               a.address as investigated_address,
               collect(DISTINCT e) as evidence,
               collect(DISTINCT t) as tasks
        """
        
        with self.driver.session() as session:
            result = session.run(query, case_id=case_id)
            record = result.single()
            
            if not record:
                return {"error": "Case not found"}
            
            case = dict(record["c"])
            
            return {
                "case": case,
                "investigated_address": record["investigated_address"],
                "evidence_count": len(record["evidence"]),
                "tasks_count": len(record["tasks"])
            }
    
    def add_evidence(self, case_id: str, evidence_type: str, description: str, 
                     source: str, added_by: str, user_role: str, 
                     file_hash: Optional[str] = None) -> Dict[str, Any]:
        """Add evidence to a case"""
        role = UserRole(user_role)
        
        if not self._has_permission(role, "add_evidence"):
            return {"error": "Insufficient permissions"}
        
        evidence_id = str(uuid.uuid4())
        timestamp = int(datetime.now().timestamp())
        
        query = """
        MATCH (c:Case {case_id: $case_id})
        CREATE (e:Evidence {
            evidence_id: $evidence_id,
            evidence_type: $evidence_type,
            description: $description,
            source: $source,
            file_hash: $file_hash,
            added_by: $added_by,
            added_at: $timestamp,
            chain_of_custody: [$added_by]
        })
        CREATE (c)-[:HAS_EVIDENCE]->(e)
        RETURN e
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                case_id=case_id,
                evidence_id=evidence_id,
                evidence_type=evidence_type,
                description=description,
                source=source,
                file_hash=file_hash or "",
                added_by=added_by,
                timestamp=timestamp
            )
            
            # Log action
            self._log_action(
                case_id=case_id,
                user=added_by,
                action="evidence_added",
                details=f"Evidence added: {evidence_type}"
            )
            
            return {
                "evidence_id": evidence_id,
                "message": "Evidence added successfully",
                "chain_of_custody": [added_by]
            }
    
    def assign_task(self, case_id: str, task_title: str, task_description: str,
                    assigned_to: str, assigned_by: str, user_role: str,
                    due_date: Optional[int] = None) -> Dict[str, Any]:
        """Assign a task to a team member"""
        role = UserRole(user_role)
        
        if not self._has_permission(role, "assign_task"):
            return {"error": "Insufficient permissions"}
        
        task_id = str(uuid.uuid4())
        timestamp = int(datetime.now().timestamp())
        
        query = """
        MATCH (c:Case {case_id: $case_id})
        CREATE (t:Task {
            task_id: $task_id,
            title: $task_title,
            description: $task_description,
            assigned_to: $assigned_to,
            assigned_by: $assigned_by,
            status: 'open',
            created_at: $timestamp,
            due_date: $due_date
        })
        CREATE (t)-[:ASSIGNED_TO]->(c)
        RETURN t
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                case_id=case_id,
                task_id=task_id,
                task_title=task_title,
                task_description=task_description,
                assigned_to=assigned_to,
                assigned_by=assigned_by,
                timestamp=timestamp,
                due_date=due_date
            )
            
            # Log action
            self._log_action(
                case_id=case_id,
                user=assigned_by,
                action="task_assigned",
                details=f"Task assigned to {assigned_to}: {task_title}"
            )
            
            return {
                "task_id": task_id,
                "message": "Task assigned successfully"
            }
    
    def update_case_status(self, case_id: str, new_status: str, updated_by: str, 
                          user_role: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """Update case status"""
        role = UserRole(user_role)
        
        if not self._has_permission(role, "update_case"):
            return {"error": "Insufficient permissions"}
        
        timestamp = int(datetime.now().timestamp())
        
        query = """
        MATCH (c:Case {case_id: $case_id})
        SET c.status = $new_status,
            c.updated_at = $timestamp,
            c.status_notes = $notes
        RETURN c
        """
        
        with self.driver.session() as session:
            result = session.run(
                query,
                case_id=case_id,
                new_status=new_status,
                timestamp=timestamp,
                notes=notes or ""
            )
            
            # Log action
            self._log_action(
                case_id=case_id,
                user=updated_by,
                action="status_updated",
                details=f"Status changed to {new_status}"
            )
            
            return {
                "case_id": case_id,
                "new_status": new_status,
                "message": "Case status updated"
            }
    
    def get_user_cases(self, user: str, user_role: str, status_filter: Optional[str] = None) -> Dict[str, Any]:
        """Get all cases for a user"""
        role = UserRole(user_role)
        
        # Managers and admins can see all cases
        if role in [UserRole.MANAGER, UserRole.ADMIN, UserRole.AUDITOR]:
            where_clause = "WHERE 1=1"
            params = {}
        else:
            where_clause = "WHERE c.assigned_to = $user OR c.created_by = $user"
            params = {"user": user}
        
        if status_filter:
            where_clause += " AND c.status = $status"
            params["status"] = status_filter
        
        query = f"""
        MATCH (c:Case)
        {where_clause}
        OPTIONAL MATCH (c)-[:INVESTIGATES]->(a:Address)
        RETURN c, a.address as investigated_address
        ORDER BY c.created_at DESC
        LIMIT 100
        """
        
        with self.driver.session() as session:
            result = session.run(query, **params)
            records = list(result)
            
            cases = []
            for record in records:
                case_data = dict(record["c"])
                case_data["investigated_address"] = record["investigated_address"]
                cases.append(case_data)
            
            return {
                "cases": cases,
                "total": len(cases)
            }
    
    def get_investigation_playbook(self, case_type: str) -> Dict[str, Any]:
        """Get investigation playbook for a case type"""
        template = self.templates.get(case_type)
        
        if not template:
            return {
                "error": "Playbook not found",
                "available_playbooks": list(self.templates.keys())
            }
        
        return {
            "case_type": case_type,
            "playbook": template,
            "available_playbooks": list(self.templates.keys())
        }
    
    def _has_permission(self, role: UserRole, permission: str) -> bool:
        """Check if role has permission"""
        role_permissions = self.permissions.get(role, [])
        return "*" in role_permissions or permission in role_permissions
    
    def _log_action(self, case_id: str, user: str, action: str, details: str):
        """Log action to audit trail"""
        timestamp = int(datetime.now().timestamp())
        
        query = """
        MATCH (c:Case {case_id: $case_id})
        CREATE (log:AuditLog {
            log_id: randomUUID(),
            case_id: $case_id,
            user: $user,
            action: $action,
            details: $details,
            timestamp: $timestamp
        })
        CREATE (c)-[:HAS_LOG]->(log)
        """
        
        with self.driver.session() as session:
            session.run(
                query,
                case_id=case_id,
                user=user,
                action=action,
                details=details,
                timestamp=timestamp
            )
    
    def get_audit_trail(self, case_id: str, user_role: str) -> Dict[str, Any]:
        """Get audit trail for a case"""
        role = UserRole(user_role)
        
        if not self._has_permission(role, "view_audit_trail"):
            return {"error": "Insufficient permissions"}
        
        query = """
        MATCH (c:Case {case_id: $case_id})-[:HAS_LOG]->(log:AuditLog)
        RETURN log
        ORDER BY log.timestamp DESC
        """
        
        with self.driver.session() as session:
            result = session.run(query, case_id=case_id)
            records = list(result)
            
            logs = [dict(record["log"]) for record in records]
            
            return {
                "case_id": case_id,
                "audit_trail": logs,
                "total_entries": len(logs)
            }

