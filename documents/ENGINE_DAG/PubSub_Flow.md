# 🌊 Ambient Agent: Pub/Sub Flow

CleanSlate AI features an ambient background capability, referred to as the **Weekly Organizer Node**. Instead of requiring the user to manually trigger a cleanup, this node allows the agent to organize files automatically on a scheduled cadence (e.g., weekly).

```mermaid
graph TD
    classDef trigger fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000;
    classDef node fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#000;
    classDef db fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000;
    classDef alert fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#000;

    Cron((Weekly Cron Job)):::trigger -->|Pub/Sub Event| WeeklyOrg[WeeklyOrganizerNode]:::node
    
    WeeklyOrg -.->|Reads| Prefs[(User Preferences)]:::db
    
    WeeklyOrg -->|Route: run| Discovery[FileDiscoveryNode]:::node
    
    Discovery --> Classify[ClassificationNode]:::node
    Classify --> Dedupe[DuplicateDetectionNode]:::node
    Dedupe --> Sensitive[SensitiveDetectionNode]:::node
    Sensitive --> Planner[OptimizationPlannerNode]:::node
    
    Planner -->|HITL Enabled| HITL[HITLApprovalNode]:::alert
    Planner -->|Fully Autonomous| Exec[ExecutionNode]:::node
    
    HITL -->|Approved| Exec
    HITL -->|Rejected| Summary[SummaryNode]:::node
    Exec --> Summary
    
    Summary -->|Dispatches| Notification((User Notification)):::trigger
```

## How it Works

#### 1. 🚨 **Trigger Mechanism**
   - The Weekly Organizer operates via a simulated Pub/Sub cron architecture. 
   - A background process triggers the `weekly_organizer_node` within the ADK graph.

#### 2. ⭐ **Preference Loading**
   - Upon triggering, the agent securely reads the user's saved preferences (e.g., target folders to organize, file types to target, whether to ask for approval or run fully autonomously).

#### 3. 🧵 **Workflow Routing**
   - Instead of routing through the conversational `MyPCAssistantNode`, the weekly trigger routes directly into the `FileDiscoveryNode`.
   - The sequence follows:
     `WeeklyOrganizerNode` -> `FileDiscoveryNode` -> `ClassificationNode` -> `DuplicateDetectionNode` -> `ExecutionNode`
   
#### 4. 🤝 **Autonomous Execution vs. HITL**
   - If the user prefers strict control, the DAG halts at `HITLApprovalNode` and sends an alert to the user's device, waiting for approval before execution.
   - If configured for full autonomy, it safely executes non-destructive actions (like categorizing files into folders) and moves sensitive files to the secure vault without interrupting the user.

5. 🔔 **Notification**
   - Finally, it routes to the `SummaryNode` to dispatch a notification and summary report regarding what was achieved in the background.
  
---
## 🔀 {} Code & ⇄ Routing:
**The core logic for the `Pub/Sub flow (Weekly Organizer`) is located here: app/nodes/[weekly_organizer_node.py](../../app/nodes/weekly_organizer_node.py)**

**And the `routing` that wires this node into the rest of the `DAG` is defined here: [app/agent.py](
../../app/agent.py)**
