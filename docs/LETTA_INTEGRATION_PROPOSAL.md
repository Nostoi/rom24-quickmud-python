# Letta LLM Agent Integration Proposal for QuickMUD

**Status**: Proposal  
**Date**: December 26, 2025  
**Author**: AI Analysis  
**Difficulty**: Medium (3-5 weeks for basic integration)

---

## Executive Summary

This document proposes integrating [Letta](https://docs.letta.com/) (formerly MemGPT), a stateful LLM agent framework, into QuickMUD to create NPCs with persistent memory, conversational AI, and emergent behaviors. This would enable mobs to remember conversations, build relationships with players, share knowledge across NPCs, and create dynamic, personalized gameplay experiences.

**Key Innovation**: To our knowledge, no existing MUD has integrated modern stateful LLM agents with persistent memory systems. This would position QuickMUD as a pioneering hybrid of classic MUD gameplay with cutting-edge AI.

---

## What is Letta?

Letta is a framework for building stateful AI agents with persistent memory. Unlike traditional LLM APIs where you manage conversation history manually, Letta agents:

- **Maintain their own persistent memory** across sessions
- **Actively manage what to remember** using built-in tools
- **Support structured memory blocks** (persona, relationships, observations)
- **Store unlimited external memory** (archival storage, conversation history)
- **Execute custom tools** (perfect for MUD actions)

### Key Concepts

1. **Memory Blocks (Core Memory)**: Always-visible structured context
   - Persona: "I am Jareth the Blacksmith, master craftsman of Midgaard"
   - Relationships: "Known players: {Alice: trusted customer, Bob: haggler}"
   - Location: "Currently in: Midgaard Blacksmith Shop"

2. **Archival Memory**: Unlimited external storage, retrieved on-demand
   - Full conversation logs
   - Historical transactions
   - Observed events

3. **Custom Tools**: Python functions the agent can call
   - MUD commands: `do_say()`, `do_emote()`, `do_attack()`
   - Memory operations: `remember_player()`, `update_reputation()`
   - World queries: `check_inventory()`, `get_room_info()`

4. **Autonomous Memory Management**: Agents decide what to remember
   - Player mentions favorite color → agent updates memory block
   - Player betrays NPC → agent stores grudge in archival memory
   - Daily observations → agent summarizes into core memory

---

## Integration Feasibility: ✅ **MEDIUM DIFFICULTY**

### ✅ Why This Is Feasible

1. **Python SDK Available**
   - Letta provides clean Python SDK
   - Natural fit with QuickMUD's Python codebase
   - Simple API: create agent, send message, get response

2. **Excellent Architectural Fit**
   - QuickMUD already has `MobPrototype` and `MobInstance` classes
   - Existing MOBProg system provides scripting foundation
   - `spec_funs` system similar to Letta's tool concept
   - Event-driven game loop works well with async agent calls

3. **Memory System Alignment**
   - ROM mobs already have state (position, affects, inventory)
   - Letta adds conversational/relational memory layer
   - Core memory → short-term awareness (current room, recent events)
   - Archival memory → long-term knowledge (player history, faction events)

4. **Custom Tools Match MUD Actions Perfectly**
   - Letta tools = Python functions
   - QuickMUD commands = Python functions
   - Natural 1:1 mapping

### ⚠️ Challenges & Mitigation Strategies

| Challenge | Impact | Mitigation |
|-----------|--------|------------|
| **API Costs** | High at scale (100s of mobs) | Enable only for "named" NPCs; use cheaper models (GPT-3.5-turbo); implement sleep mode |
| **Latency** | 200ms-2s per LLM call | Async processing; hybrid approach (MOBProgs for combat, Letta for conversation) |
| **State Sync** | Letta memory vs game state divergence | Periodic sync tools; event-driven memory updates |
| **Hallucinations** | Agent "remembers" false information | Archival memory for facts; validate actions before execution |
| **Context Limits** | LLM context window constraints | Letta handles this automatically via memory hierarchy |

---

## Proposed Architecture

### 1. Core Components

```
┌─────────────────────────────────────────────────┐
│              QuickMUD Game Server               │
│                                                 │
│  ┌──────────────┐         ┌─────────────────┐  │
│  │ MobInstance  │◄───────►│  LettaAgent     │  │
│  │ (existing)   │         │  (new)          │  │
│  └──────────────┘         └─────────────────┘  │
│         │                          │            │
│         │                          │            │
│         ▼                          ▼            │
│  ┌──────────────┐         ┌─────────────────┐  │
│  │ ROM Commands │         │  Custom Tools   │  │
│  │ do_say()     │◄───────►│  attack()       │  │
│  │ do_kill()    │         │  say()          │  │
│  │ do_give()    │         │  remember()     │  │
│  └──────────────┘         └─────────────────┘  │
│                                                 │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │   Letta Backend     │
         │  (Cloud or Self-    │
         │   Hosted)           │
         │                     │
         │ ┌─────────────────┐ │
         │ │ Memory Blocks   │ │
         │ │ Archival Memory │ │
         │ │ Agent State     │ │
         │ └─────────────────┘ │
         └─────────────────────┘
```

### 2. New Python Modules

```
mud/
├── letta/
│   ├── __init__.py
│   ├── client.py              # Letta SDK wrapper
│   ├── mob_integration.py     # LettaMob mixin class
│   ├── tools.py               # Custom MUD tools for Letta
│   ├── memory_sync.py         # Game state → Letta memory sync
│   └── config.py              # Letta configuration
```

### 3. Integration Points

#### A. Mob Initialization (`mud/spawning/mob_spawner.py`)

```python
class MobInstance:
    def __init__(self, prototype, room):
        # ... existing initialization ...
        
        # NEW: Letta integration
        if prototype.letta_enabled:
            from mud.letta import create_letta_mob
            self.letta_agent = create_letta_mob(
                mob=self,
                persona=prototype.letta_persona,
                initial_memories=prototype.letta_memories
            )
```

#### B. Speech Processing (`mud/commands/communication.py`)

```python
async def do_say(char: Character, args: str) -> str:
    # Existing say logic (echo to room, etc.)
    message = f"{char.name} says '{args}'"
    send_to_room(char.in_room, message)
    
    # NEW: Trigger Letta mobs in room
    for mob in char.in_room.people:
        if hasattr(mob, 'letta_agent') and mob != char:
            asyncio.create_task(
                process_letta_response(mob, char, args)
            )
    
    return message

async def process_letta_response(mob, speaker, speech):
    """Process speech through Letta agent and execute response"""
    response = await mob.letta_agent.send_message(
        input=f"{speaker.name} says: {speech}",
        context={
            "room": mob.in_room.name,
            "people_present": [p.name for p in mob.in_room.people]
        }
    )
    
    # Execute agent's chosen actions
    for message in response.messages:
        if message.type == "tool_call":
            await execute_mob_tool(mob, message.tool_name, message.args)
        elif message.type == "assistant_message" and message.content:
            do_say(mob, message.content)
```

#### C. Observation System (`mud/letta/observation.py`)

```python
class MobObserver:
    """Lets Letta mobs observe and react to world events"""
    
    @staticmethod
    async def update_observations():
        """Called each game tick"""
        for mob in get_letta_enabled_mobs():
            observations = []
            
            # Room changes
            if mob.in_room.events_since_last_tick:
                observations.extend(mob.in_room.events_since_last_tick)
            
            # Inventory changes
            if mob.inventory_changed:
                observations.append(f"Inventory: {mob.inventory_summary}")
            
            # Health changes
            if mob.hit != mob.last_recorded_hit:
                observations.append(f"HP changed: {mob.hit}/{mob.max_hit}")
            
            # Send observations to agent
            if observations:
                await mob.letta_agent.send_observation(
                    "; ".join(observations)
                )
```

#### D. Custom Tools (`mud/letta/tools.py`)

```python
from letta_client import BaseTool
from pydantic import BaseModel

class MudActionTool(BaseTool):
    """Tool for performing MUD actions"""
    
    name: str = "perform_mud_action"
    description: str = "Perform a MUD action (say, emote, attack, etc.)"
    
    class ActionArgs(BaseModel):
        action: str  # "say", "emote", "attack", "give"
        target: str = None
        message: str = None
    
    args_schema = ActionArgs
    
    def run(self, action: str, target: str = None, message: str = None) -> str:
        mob = self.get_mob_context()  # Injected by framework
        
        if action == "say":
            return do_say(mob, message)
        elif action == "emote":
            return do_emote(mob, message)
        elif action == "attack":
            return do_kill(mob, target)
        elif action == "give":
            return do_give(mob, f"{target} {message}")
        else:
            return f"Unknown action: {action}"

class RememberPlayerTool(BaseTool):
    """Tool for storing player information"""
    
    name: str = "remember_player"
    description: str = "Store important information about a player"
    
    class RememberArgs(BaseModel):
        player_name: str
        fact: str
        importance: int = 5  # 1-10 scale
    
    args_schema = RememberArgs
    
    def run(self, player_name: str, fact: str, importance: int = 5) -> str:
        """Store in archival memory with metadata"""
        mob = self.get_mob_context()
        
        # Store in Letta archival memory
        return mob.letta_agent.archival_memory.insert(
            content=f"[{player_name}] {fact}",
            metadata={"importance": importance, "type": "player_fact"}
        )
```

---

## Implementation Roadmap

### Phase 1: Proof of Concept (1 week)

**Goal**: Single Letta-enabled mob with basic conversation

- [ ] Set up Letta Cloud account + API key
- [ ] Create `mud/letta/` module structure
- [ ] Implement `create_letta_mob()` for single test NPC
- [ ] Add basic conversation trigger (say/tell)
- [ ] Test memory persistence across sessions
- [ ] Document API costs for 10 interactions

**Success Criteria**:
- Mob remembers player name across logouts
- Mob responds contextually to repeated visits
- <$1 spent on API calls during testing

### Phase 2: Core Integration (2 weeks)

**Goal**: Production-ready foundation for Letta mobs

- [ ] Create `LettaMob` mixin class
- [ ] Implement 5-10 custom tools (say, emote, attack, give, remember)
- [ ] Add observation system (room events, combat, movement)
- [ ] Integrate with existing command handlers
- [ ] Add configuration system (enable/disable per mob)
- [ ] Write unit tests for Letta integration layer

**Success Criteria**:
- 3-5 named NPCs enabled with Letta
- Mobs respond to player actions appropriately
- No game-breaking latency (<500ms avg response)
- Test suite passes with Letta mocked

### Phase 3: Advanced Features (2 weeks)

**Goal**: Sophisticated AI behaviors

- [ ] Shared memory blocks (faction knowledge, city news)
- [ ] Mob-to-mob conversations
- [ ] Dynamic quest generation based on mob memories
- [ ] Integration with existing MOBProg system (hybrid mode)
- [ ] Admin commands (`letta_status`, `letta_memory`, `letta_debug`)
- [ ] Cost monitoring and alerts

**Success Criteria**:
- Mobs share knowledge (player reputation across NPCs)
- Mobs generate at least 1 coherent quest
- Hybrid MOBProg + Letta mode works seamlessly
- Cost dashboard tracks spending per mob

### Phase 4: Optimization & Scale Testing (ongoing)

**Goal**: Production readiness at scale

- [ ] Response caching (common greetings, etc.)
- [ ] Async/parallel agent processing
- [ ] Sleep mode (agents inactive when no players nearby)
- [ ] Model selection (GPT-4 for important NPCs, GPT-3.5 for common)
- [ ] Load testing (10+ concurrent Letta mobs)
- [ ] Self-hosting evaluation (cost vs control tradeoff)

**Success Criteria**:
- Support 10+ concurrent Letta mobs without lag
- Cost <$10/day for typical server load
- 95th percentile latency <1s
- Self-hosting option documented

---

## Cost & Performance Analysis

### Cost Estimates (Letta Cloud)

| Scenario | Model | Cost/1K Tokens | Tokens/Interaction | Cost/Interaction | Daily Cost (100 interactions) |
|----------|-------|----------------|--------------------|--------------------|-------------------------------|
| Simple NPC | GPT-3.5-turbo | $0.002 | 500 | $0.001 | $0.10 |
| Named NPC | GPT-4o-mini | $0.005 | 1000 | $0.005 | $0.50 |
| Important NPC | GPT-4o | $0.015 | 1500 | $0.023 | $2.30 |

**Estimated Monthly Costs**:
- 5 simple NPCs (shopkeepers, guards): $15/month
- 3 named NPCs (quest givers): $45/month
- 1 important NPC (major antagonist): $70/month
- **Total**: ~$130/month for 9 Letta-enabled mobs

**Cost Optimization Strategies**:
1. Cache common responses (greetings, shop info)
2. Use cheaper models for routine interactions
3. Implement "sleep mode" for NPCs in empty areas
4. Self-host for high-volume production use

### Performance Benchmarks

| Metric | Target | Typical | Worst Case |
|--------|--------|---------|------------|
| Response Latency | <500ms | 200-400ms | 1-2s |
| Concurrent Agents | 10+ | 5-10 | 20+ |
| Memory Footprint | <50MB/agent | 30-40MB | 100MB |
| API Rate Limits | N/A | 60 req/min | Letta manages |

---

## Example Use Cases

### 1. Shopkeeper with Transaction Memory

**Setup**:
```python
shopkeeper = create_letta_mob(
    name="Jareth the Blacksmith",
    persona="Gruff but fair master blacksmith. Values loyalty, dislikes haggling.",
    memory_blocks={
        "business": "Blacksmith shop in Midgaard. Sells weapons and armor.",
        "customers": "Track regular customers and their preferences.",
        "inventory": "Current stock levels and special orders."
    },
    tools=["say", "emote", "check_inventory", "remember_customer"]
)
```

**Interaction Flow**:
```
[First Visit]
Player: "Hi, do you sell swords?"
Jareth: "Aye, finest blades in Midgaard. New face, aren't you? Name's Jareth."
  → Agent stores: "New customer: {player_name}, interested in swords"

[Second Visit - Days Later]
Player: "Hi Jareth"
Jareth: "Welcome back! Here to see that sword you were asking about last week? I set one aside for you."
  → Agent retrieves: Customer history, shows personalized service

[Player Brings Friend]
Player: "This is my friend Bob"
Jareth: "Any friend of {player_name} is welcome. They're a good customer - never try to haggle me down!"
  → Agent uses relationship memory to inform social interaction
```

### 2. Quest Giver with Emergent Storytelling

**Setup**:
```python
quest_giver = create_letta_mob(
    name="Elder Morwen",
    persona="Ancient village elder, wise and cryptic. Concerned about recent goblin raids.",
    memory_blocks={
        "village_state": "Village peaceful but goblin attacks increasing.",
        "quests_given": "Track who has accepted quests and their progress.",
        "world_knowledge": "Knows history of region, rumors, political tensions."
    },
    tools=["say", "emote", "assign_quest", "check_quest_status", "observe_event"]
)
```

**Dynamic Quest Generation**:
```
[After Observing Goblin Attack]
Elder Morwen internally: "Three goblin raids this week. Players {Alice, Bob} are experienced. Should offer bounty quest."

Player: "Hello Elder"
Elder Morwen: "Thank the gods you're here! The goblins grow bolder - third attack this week. Would you help us? I can offer 500 gold for proof of their defeat."
  → Agent generates quest dynamically based on observed world events
  → Tracks player acceptance, progress, and completion
  → Adjusts reward based on player reputation
```

### 3. Faction Leader with Shared Memory

**Setup**:
```python
# Multiple NPCs share faction memory block
thieves_guild_memory = create_shared_memory(
    label="guild_knowledge",
    initial_value="Guild secrets, member roster, current jobs, rival faction status"
)

guild_leader = create_letta_mob(
    name="Shadowmaster Vexx",
    shared_memory=[thieves_guild_memory],
    tools=["say", "recruit_member", "assign_job", "update_guild_status"]
)

guild_fence = create_letta_mob(
    name="Slim the Fence",
    shared_memory=[thieves_guild_memory],
    tools=["say", "buy_stolen_goods", "check_guild_membership"]
)
```

**Shared Knowledge Flow**:
```
[Player talks to Guild Leader]
Player: "I want to join the Thieves Guild"
Vexx: "Prove yourself. Steal the mayor's signet ring."
  → Updates shared memory: "{player_name}: recruitment test - steal ring"

[Player talks to Fence across town]
Player: "I have this ring to sell"
Slim: "Ah yes, Vexx mentioned you. That's the test item - I'll hold it for the guild. Go report to Vexx."
  → Retrieves shared memory, knows player context without direct communication
```

---

## Technical Requirements

### Dependencies

```toml
# pyproject.toml additions
[tool.poetry.dependencies]
letta-client = "^0.4.0"  # Letta Python SDK
pydantic = "^2.0"        # For tool schemas (already required)
asyncio = "^3.4"         # For async agent calls (stdlib)
```

### Configuration

```yaml
# config/letta.yaml
letta:
  enabled: true
  backend: "cloud"  # or "self-hosted"
  api_key: "${LETTA_API_KEY}"  # From environment
  
  # Model selection
  models:
    default: "openai/gpt-3.5-turbo"
    important_npcs: "openai/gpt-4o"
    embedding: "openai/text-embedding-3-small"
  
  # Cost controls
  cost_limits:
    daily_max_usd: 10.0
    per_mob_max_usd: 2.0
    alert_threshold_usd: 8.0
  
  # Performance
  cache_responses: true
  cache_ttl_seconds: 300
  max_concurrent_agents: 10
  sleep_mode_enabled: true
  sleep_after_inactive_minutes: 15
  
  # Memory
  memory_blocks_default:
    - persona
    - location
    - relationships
  archival_memory_enabled: true
  max_archival_entries_per_mob: 1000
```

### Database Schema Extensions

```sql
-- New table for Letta-enabled mobs
CREATE TABLE letta_mobs (
    mob_vnum INTEGER PRIMARY KEY,
    letta_agent_id TEXT NOT NULL,
    letta_enabled BOOLEAN DEFAULT TRUE,
    persona TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP,
    total_interactions INTEGER DEFAULT 0,
    total_cost_usd REAL DEFAULT 0.0
);

-- Mob memory snapshots (for debugging/analysis)
CREATE TABLE letta_memory_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mob_vnum INTEGER,
    memory_blocks TEXT,  -- JSON
    snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mob_vnum) REFERENCES letta_mobs(mob_vnum)
);
```

---

## Security & Safety Considerations

### 1. Content Filtering
- **Issue**: LLMs might generate inappropriate content
- **Mitigation**: 
  - Use Letta's content filters
  - Implement custom profanity filter on responses
  - Admin review mode for new Letta mobs

### 2. Action Validation
- **Issue**: Agent might try invalid or game-breaking actions
- **Mitigation**:
  - Whitelist allowed tools per mob
  - Validate all tool calls before execution
  - Rate limit actions (e.g., max 1 attack per 6 seconds)

### 3. Resource Exhaustion
- **Issue**: Malicious player could spam interactions to drain API budget
- **Mitigation**:
  - Rate limit per player (e.g., 10 interactions/minute)
  - Cost tracking and automatic shutoff at threshold
  - Priority queue (important NPCs first)

### 4. Memory Pollution
- **Issue**: Players might try to "trick" agent memory
- **Mitigation**:
  - Admin tools to view/edit agent memory
  - Memory validation (flag suspicious patterns)
  - Regular memory backups

---

## Admin Tools & Monitoring

### Command-Line Tools

```bash
# View Letta mob status
> letta_status

Letta-Enabled Mobs: 9 active, 3 sleeping
API Costs Today: $2.34 / $10.00 limit
Active Agents: 5

Mob                  | Agent ID    | Interactions | Cost    | Status
---------------------|-------------|--------------|---------|--------
Jareth (blacksmith)  | agent-1234  | 47           | $0.58   | Active
Elder Morwen         | agent-5678  | 23           | $1.15   | Active
Guard Captain        | agent-9012  | 12           | $0.15   | Sleeping

# View mob memory
> letta_memory Jareth

=== MEMORY BLOCKS ===
[persona]
Gruff but fair master blacksmith. Values loyalty, dislikes haggling.

[business]
Blacksmith shop in Midgaard. Current stock: 12 swords, 8 shields, 3 helmets.

[customers]
Alice: Regular customer, bought 3 swords, always polite, preferred customer
Bob: New customer, interested in armor, tried to haggle (unsuccessful)

=== ARCHIVAL MEMORY (last 10 entries) ===
1. [2025-12-20] Alice purchased longsword for 150 gold
2. [2025-12-21] Bob asked about platemail prices
3. [2025-12-22] Village elder requested custom sword (special order)
...

# Debug conversation
> letta_debug Jareth last

=== LAST INTERACTION ===
Input: "Alice says: Hi Jareth, do you have any new swords?"
Agent Reasoning: "Alice is a regular customer. Should check inventory and be friendly."
Tool Calls: 
  - check_inventory(item_type="sword")
Response: "Welcome back Alice! Just got a beautiful elven blade in yesterday. Think you'd like it - lighter than your usual preference but razor sharp."
```

### Monitoring Dashboard

```python
# mud/letta/monitoring.py

class LettaMonitor:
    """Real-time monitoring of Letta agents"""
    
    def get_stats(self) -> dict:
        return {
            "active_agents": len(self.active_agents),
            "total_interactions_today": self.interaction_count,
            "cost_today_usd": self.cost_tracker.get_daily_cost(),
            "avg_response_time_ms": self.latency_tracker.get_average(),
            "errors_today": len(self.error_log),
            "top_active_mobs": self.get_top_mobs(5)
        }
    
    def alert_if_needed(self):
        """Send alerts for anomalies"""
        if self.cost_tracker.get_daily_cost() > self.config.alert_threshold:
            send_admin_alert(f"Letta costs: ${self.cost_tracker.get_daily_cost():.2f}")
        
        if self.latency_tracker.get_p95() > 2000:  # 2s
            send_admin_alert(f"Letta latency high: {self.latency_tracker.get_p95()}ms")
```

---

## Future Enhancements

### 1. Multi-Agent Systems
- Mob groups with shared goals (bandit gang, village council)
- Agent-to-agent conversations without player involvement
- Emergent faction dynamics

### 2. World-Level Memory
- City-wide news/rumors (all NPCs know major events)
- Economic memory (price fluctuations based on supply/demand)
- Political memory (faction wars, alliances)

### 3. Player Profiles
- Each player gets a Letta agent tracking their reputation
- NPCs query player agent: "What do other NPCs think of Alice?"
- Persistent player reputation across all NPCs

### 4. Dynamic Content Generation
- Quest generation based on world state
- Dialogue generation (no more static strings)
- Story arc progression driven by agent observations

### 5. Advanced Tools
- `cast_spell()` - Mobs can use magic via Letta
- `trade()` - Complex bartering negotiations
- `teach_skill()` - Dynamic skill training
- `craft_item()` - Custom item creation

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| High API costs | High | High | Strict cost limits, caching, model selection |
| Player abuse (spam) | Medium | Medium | Rate limiting, cost tracking per player |
| Agent hallucinations | Medium | Low | Fact validation, archival memory for truth |
| Latency issues | Medium | Medium | Async processing, response caching |
| Integration bugs | High | Medium | Extensive testing, gradual rollout |
| LLM service outage | Low | High | Graceful degradation to MOBProgs |

---

## Conclusion

Integrating Letta into QuickMUD is **technically feasible** with **medium difficulty** and would create a genuinely innovative player experience. The key to success is:

1. **Start small**: 5-10 named NPCs, not all mobs
2. **Hybrid approach**: Combine MOBProgs (reliable, fast) with Letta (rich, adaptive)
3. **Cost control**: Strict budgets, caching, model selection
4. **Gradual rollout**: PoC → Core Integration → Advanced Features → Production

**Recommended Next Steps**:
1. Create Letta Cloud account and test with single NPC
2. Prototype `mud/letta/` module structure
3. Implement 2-3 core tools (say, emote, remember)
4. Run cost/latency benchmarks
5. Decide: proceed with full integration or archive as experimental

**Potential Impact**:
- ✅ First MUD with stateful LLM agents
- ✅ Personalized gameplay (NPCs remember YOU)
- ✅ Emergent storytelling
- ✅ Viral marketing potential ("AI NPCs that actually remember you")

This could be a defining feature that sets QuickMUD apart from every other MUD in existence.

---

## References

- [Letta Documentation](https://docs.letta.com/)
- [Letta Quickstart](https://docs.letta.com/quickstart)
- [Letta Memory Guide](https://docs.letta.com/guides/agents/memory)
- [Letta Custom Tools](https://docs.letta.com/guides/agents/custom-tools)
- [MemGPT Paper (2023)](https://arxiv.org/abs/2310.08560) - Original research
- [QuickMUD MOBProg System](../mud/mobprog.py)
- [QuickMUD Mob Models](../mud/models/mob.py)

---

**Document Version**: 1.0  
**Last Updated**: December 26, 2025
