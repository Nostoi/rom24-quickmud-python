# TODO

- [x] Step 1: Define Python Data Models (Autonomous Codex Execution)
- [x] Step 2: Build Parsers to Load Game Data from Text Files
- [x] Step 3: Replace the Rooms and Areas Subsystem (Environment Management)
- [x] Step 4: Migrate NPC and Object Management (Prototypes to Instances)
- [x] Step 5: Implement the Command Interpreter and Game Logic


## 🧱 Step 1: Define Python Data Models (Autonomous Codex Execution)

**Objective**: Create Python data classes that accurately represent the core structs in the C codebase `rom24-quickmud` (QuickMUD). This lays the foundation for the rest of the system by modeling Rooms, Areas, Mobs, Objects, and related constants.

---

### 🧠 Codex Must Know:

- C structs are located in `merc.h`, `structs.h`, and similar headers.
- Each entity (e.g., ROOM_INDEX_DATA, MOB_INDEX_DATA) maps to a class in Python using `@dataclass`.
- Ignore raw pointers and memory allocation in translation.
- Use idiomatic Python types (`int`, `str`, `List`, `Dict`, `Optional`) and avoid C-style syntax.
- Bitfields and enums in C should be mapped to `Enum` or constant dictionaries.
- Fields using linked lists (`*next`) should become `List[Type]` or similar in Python.
- All class names should use PascalCase and file names should be snake_case.

---

### 📁 Target File Structure:

```
mud/
├── models/
│   ├── __init__.py
│   ├── area.py
│   ├── room.py
│   ├── mob.py
│   ├── obj.py
│   ├── character.py
│   └── constants.py
```

---

### ✅ Tasks and Subtasks

#### 1. Extract and Translate Structs

**1.1 Parse Struct Definitions:**
- Input: `merc.h`, `tables.c`, and other relevant files.
- Output: List of struct definitions (e.g., `ROOM_INDEX_DATA`, `AREA_DATA`, `MOB_INDEX_DATA`, `OBJ_INDEX_DATA`, `CHAR_DATA`).
- Approach:
  - Use regex or C parser to identify all `typedef struct` blocks.
  - Collect field names, types, and comments for documentation.

**1.2 Translate Structs to Python Dataclasses:**
- Output: Python dataclasses in separate files (`room.py`, `mob.py`, etc.).
- Approach:
  - Translate C types to Python (`char *` → `str`, `int` → `int`, `bool` → `bool`, `sh_int` → `int`).
  - Convert `*next` pointers or linked lists into `List[Type]`.
  - Replace bitfields with `Enum` or `Set[str]` fields (to be implemented later).
  - Add docstrings with original field names and notes for future reference.

#### 2. Model Inter-Entity Relationships

**2.1 Define References Between Classes:**
- e.g., `Room` should reference `Area`, `Exit`, `ObjectInstance`, `Character`, etc.
- Use `Optional["Type"]` and forward declarations as needed.

**2.2 Build `__repr__()` or `__str__()` Methods:**
- Output: Readable debug output for each entity (e.g., Room prints name, vnum).
- Helps with later snapshot tests and logging.

#### 3. Create Constants and Enums

**3.1 Extract Constant Tables:**
- Input: C tables like `const struct flag_type item_table[]`, `position_table[]`, etc.
- Output: Enum or dictionary equivalents in `constants.py`.
- Format:
  ```python
  class ItemType(Enum):
      WEAPON = 1
      ARMOR = 2
      POTION = 3
  ```

**3.2 Replace Magic Numbers in Dataclasses:**
- Ensure dataclasses reference Enums or constants instead of raw integers.

#### 4. Generate Index Registry Maps

**4.1 Create VNUM-to-Instance Registry:**
- Output: Dicts like `room_registry: Dict[int, Room]` to enable global lookup.
- These will be populated in the loading step later.

---

### 🧪 Final Output for Step 1:

- `mud/models/*.py` files containing complete dataclass definitions
- `mud/models/constants.py` with enums and flags
- Registry templates (e.g., empty `room_registry = {}` in `room.py`)
- Optional: `test_model_instantiation.py` to verify model creation with dummy data

---

### ✅ Completion Criteria:

- All core structs from C are represented as Python dataclasses
- Fields are typed, documented, and linked across models
- No compilation/runtime errors when importing models
- Dummy instances can be created and printed for debug

---

### 🛠️ Follow-up Dependency:

- Step 2 (Area File Parsing) will depend on these models being importable and complete

## 📦 Step 2: Build Parsers to Load Game Data from Text Files

**Objective**: Implement Python parsers that read legacy `.are` (ROM area) text files and convert them into fully populated Python dataclass instances (e.g. `Room`, `Mob`, `Obj`, `Area`). This allows the Python engine to load the existing game world data from files.

---

### 🧠 Codex Must Know:

- `.are` files contain sectioned text data using markers like `#AREA`, `#ROOMS`, `#MOBILES`, etc.
- Strings are terminated with `~`, often multi-line.
- Fields follow a strict sequence per section, sometimes with bitflag integers.
- Exit data (`D0`, `D1`, etc.) and resets (`M`, `O`, etc.) are inline.
- Comments start with `*`, and section end is marked with `S`.
- C functions like `fread_string`, `fread_number`, `load_rooms`, and `load_mobiles` show the parsing logic to replicate.

---

### 📁 Target File Structure:

```
mud/
├── loaders/
│   ├── __init__.py
│   ├── base_loader.py
│   ├── area_loader.py
│   ├── room_loader.py
│   ├── mob_loader.py
│   ├── obj_loader.py
│   ├── reset_loader.py
│   └── helpers.py
```

---

### ✅ Tasks and Subtasks

#### 1. Base Loader Utilities

**1.1 Implement a BaseTokenizer:** ✅
- Output: `BaseTokenizer` class in `base_loader.py`
- Behavior:
  - `.next_line()` → return next line from file (skipping comments).
  - `.peek_line()` → preview without consuming.
  - `.read_string_tilde()` → read lines until `~`.
  - `.read_number()` → parse next token as int.
  - Optional `.read_flags()` → parse int and map to enums later.

**1.2 Write Utility Parsers:** ✅ (minimal for exits handled in loaders)
- `parse_exits(tokenizer: BaseTokenizer)` → returns exit dict for a room.
- `parse_affects()`, `parse_stats()`, etc., as needed.
- Reuse logic across mobs, rooms, objects.

---

#### 2. Top-Level Area Loader

**2.1 Implement `load_area_file(filepath: str)` in `area_loader.py`:** ✅
- Reads full `.are` file and dispatches section parsers based on headers:
  - `#AREA`, `#MOBILES`, `#OBJECTS`, `#ROOMS`, `#RESETS`, etc.
- Returns: `Area` instance with lists of contained rooms/mobs/objs/etc.

**2.2 Add section dispatch mapping:** ✅
```python
SECTION_HANDLERS = {
  "#MOBILES": load_mobiles,
  "#OBJECTS": load_objects,
  "#ROOMS": load_rooms,
  "#RESETS": load_resets,
}
```

---

#### 3. Section-Specific Parsers

**3.1 `load_rooms(tokenizer) → List[Room]` in `room_loader.py`** ✅
- Parse vnum, name, description, flags, sector type.
- Detect and parse `D0`–`D5` exits (multiple per room).
- Stop on line with `S`.

**3.2 `load_mobiles(tokenizer) → List[MobPrototype]` in `mob_loader.py`** ✅
- Parse vnum, keywords, short/long desc, act flags, alignment, stats.
- Track all vnums in a registry: `mob_registry[vnum] = instance`

**3.3 `load_objects(tokenizer) → List[ObjPrototype]` in `obj_loader.py`** ✅
- Parse vnum, name/short desc, type/flags/values, affects.

**3.4 `load_resets(tokenizer) → List[Reset]` in `reset_loader.py`** ✅ (simplified)
- Parse one-line resets starting with `M`, `O`, `P`, etc.
- Store them in area or room for later population.

---

#### 4. Global Registries for VNUM Lookup

**4.1 Create central registry file `mud/registry.py`:** ✅
```python
room_registry = {}
mob_registry = {}
obj_registry = {}
area_registry = {}
```
- These are populated during loading for quick access.
- Later used to resolve exits, resets, and gameplay mechanics.

---

#### 5. Load All Areas from Master File

**5.1 Implement `load_all_areas(list_path="area.lst")`:** ✅
- Read each `.are` path from master list file (like `area.lst` in root dir).
- For each file, call `load_area_file()`, store results.
- At end: all registries are filled, world is loaded in memory.

---

### 🧪 Final Output for Step 2:

- All area files in `area.lst` are parsed into live Python objects.
- Each registry (`room_registry`, etc.) has accurate mappings.
- Resets and exits are captured for future processing.
- No exceptions raised on valid area files.
- `test_load_midgaard.py` verifies room 3001 is correct (sample test).
✔ `test_load_midgaard.py` verifies room 3001 is correct (sample test).

---

### ✅ Completion Criteria:

- `load_all_areas()` successfully parses all files from `area.lst`
- World entities match expected counts (e.g., # of rooms, mobs)
- `Room` objects contain correct exits, names, and links
- All strings are trimmed of `~` and whitespace
- Snapshot JSON dump of a loaded area matches known-good output

---

### 🛠️ Follow-up Dependency:

- Step 3 (Linking Exits & Movement) depends on `room_registry` and populated fields
- Step 6 (DB migration) will reuse these loaders for import

## 🚪 Step 3: Replace the Rooms and Areas Subsystem (Environment Management)

**Objective**: Use the loaded `Room`, `Area`, and related data classes to model the **navigable world**. Implement linking of exits, movement between rooms, and utility functions like `look()`.

---

### 🧠 Codex Must Know:

- All rooms are loaded and stored in `room_registry[vnum]`.
- Exits are stored as direction → target vnum in each Room.
- Room instances may contain lists of characters and objects.
- Movement involves updating a character's room and updating both rooms' character lists.
- Some exits may be invalid or unlinked – these must be checked and optionally warned about.

---

### 📁 Target File Structure:

```
mud/
├── world/
│   ├── __init__.py
│   ├── world_state.py
│   ├── movement.py
│   ├── linking.py
│   └── look.py
```

---

### ✅ Tasks and Subtasks

#### 1. Exit Linking and Validation

**1.1 Implement `link_exits()` in `linking.py`:** ✅
- Input: `room_registry` populated from Step 2.
- For each room:
  - Iterate its `exits` dictionary (e.g. `{"north": 3010}`).
  - If target vnum exists in `room_registry`, replace with reference: `room.exits["north"] = target_room`.
  - If missing, log a warning: `Unlinked exit in room 3001 -> north (target 9999 not found)`.
- Add optional `room.unlinked_exits` set for diagnostics.

**1.2 Add a one-time exit fix routine:** ✅
- Ensure this is called after loading areas and before gameplay starts.
- `fix_all_exits()` could live in `world_state.py`.

---

#### 2. Movement Logic

**2.1 Implement `move_character(char: Character, direction: str) -> str` in `movement.py`:** ✅
- Check if `direction` exists in `char.room.exits`.
- If not: return `"You cannot go that way."`
- Else:
  - Remove character from current room’s character list.
  - Add to target room’s character list.
  - Update `char.room = target_room`.
  - Return movement message: `"You walk north to <room name>."`

**2.2 Optional: Room-level utility methods** ✅
- `Room.add_character(char: Character)`
- `Room.remove_character(char: Character)`
- These manage bidirectional state updates.

---

#### 3. Room Inspection (`look` Command)

**3.1 Implement `look(char: Character) -> str` in `look.py`:** ✅
- Output includes:
  - Room name (`room.name`)
  - Description (`room.description`)
  - Visible exits: `"Exits: north east west"`
  - Objects: list all in room
  - Characters: list other characters in room (not self)

**3.2 Format exit display nicely:** ✅
- Match expected ROM output: `[Exits: north south]` or custom styles.

**3.3 Test with a simulated character in room 3001:** ✅
- Should output all fields cleanly.

---

#### 4. World State Utility

**4.1 Add `initialize_world()` in `world_state.py`:** ✅
- Calls:
  - `load_all_areas()` (Step 2)
  - `fix_all_exits()`
- Returns: populated world state with registries and linked rooms.

**4.2 Add `create_test_character(name, room_vnum)` function:** ✅
- Spawns a new `Character` and places it in the correct Room.
- Useful for test harnesses and dummy input simulation.

---

### 🧪 Final Output for Step 3:

- Linked room graph (all exits resolved to actual Room instances).
- Characters can move between rooms using `move_character`.
- Room descriptions rendered correctly with exits and contents.
- Logging present for invalid exits or dead links.

---

### ✅ Completion Criteria:

- All rooms have valid references (or clean warnings if not).
- Movement produces correct state changes and messages.
- `look()` shows accurate state for any room and character.
- Sample test: moving a character north from 3001 and using `look()` in each room.

---

### 🛠️ Follow-up Dependency:

- Step 4 (Mob/Object spawning) assumes rooms are properly linked and traversable.
- Step 5 (Command interpreter) will call `look()` and `move_character()` from this step.

## 🧍‍♂️ Step 4: Migrate NPC and Object Management (Prototypes to Instances)

**Objective**: Implement the logic to spawn mobs (NPCs) and objects from prototypes into the world. Ensure spawned instances can be added to rooms, characters, or containers, and that all links and state are consistent.

---

### 🧠 Codex Must Know:

- Mob and object prototypes are already loaded into `mob_registry` and `obj_registry` from Step 2.
- Instances of NPCs and items must be created from prototypes using deep copies or constructors.
- Room instances contain lists of objects and characters.
- Characters can hold inventory (list of objects) and equip items.
- Reset instructions define where to spawn mobs and objects (parsed in Step 2).
- Game should support a one-time initial spawn (no ticking resets yet).

---

### 📁 Target File Structure:

```
mud/
├── spawning/
│   ├── __init__.py
│   ├── mob_spawner.py
│   ├── obj_spawner.py
│   ├── reset_handler.py
│   └── templates.py
```

---

### ✅ Tasks and Subtasks

#### 1. Define Spawnable Templates

**1.1 Create `MobInstance` and `ObjectInstance` dataclasses in `templates.py`:** ✅
- Fields:
  - `MobInstance`: name, level, current_hp, prototype_ref, inventory, location
  - `ObjectInstance`: name, type, prototype_ref, location, contained_items
- Provide `from_prototype(proto: MobPrototype) -> MobInstance` constructors.

**1.2 Attach utility methods:** ✅
- `.move_to_room(room: Room)`
- `.add_to_inventory(obj: ObjectInstance)`
- `.equip(obj, slot)` (stub if needed)

---

#### 2. Implement Spawner Functions

**2.1 In `mob_spawner.py`:** ✅
```python
def spawn_mob(vnum: int) -> MobInstance:
    proto = mob_registry[vnum]
    mob = MobInstance.from_prototype(proto)
    return mob
```

**2.2 In `obj_spawner.py`:** ✅
```python
def spawn_object(vnum: int) -> ObjectInstance:
    proto = obj_registry[vnum]
    obj = ObjectInstance.from_prototype(proto)
    return obj
```

**2.3 Optionally support limits per prototype:**
- e.g., `if proto.count >= proto.max_instances: return None`

---

#### 3. Handle Resets for Initial World Population

**3.1 In `reset_handler.py`, define `apply_resets(area: Area)`:** ✅
- Iterate over `area.resets`.
- For each reset:
  - `M <mob_vnum> <room_vnum>` → spawn mob and place in room.
  - `O <obj_vnum> <room_vnum>` → spawn obj and place in room.
  - `G <obj_vnum>` or `E <obj_vnum> <slot>` → give or equip to last spawned mob.
  - `P <obj_vnum> <container_vnum>` → put in container.
- Maintain context (e.g., last mob spawned) to apply nested resets.

**3.2 Implement logging for invalid vnums or targets.** ✅

---

#### 4. Integrate with Room and Character State

**4.1 Add methods:** ✅
- `Room.add_object(obj)`
- `Room.add_mob(mob)`
- `Character.add_object(obj)`
- `Character.equip_object(obj, slot)` (stub if not implemented)

**4.2 Update `initialize_world()` to apply resets after linking exits.** ✅

---

### 🧪 Final Output for Step 4:

- Rooms populated with mobs and objects as specified in reset lists.
- Spawned mobs have correct stats and names based on prototype.
- Spawned objects placed in rooms, mobs, or containers appropriately.
- Can list room contents to verify population.

---

### ✅ Completion Criteria:

- Calling `initialize_world()` results in populated rooms.
- Room `3001` contains expected mobs/objects from area file.
- No missing vnum errors in resets.
- `look()` command shows mobs and objects present.
- Instances are independent of prototypes (no shared mutable state).

---

### 🛠️ Follow-up Dependency:

- Step 5 (Command interpreter) uses this logic to manipulate game state.
- Step 6 (Networking) assumes mobs/objects are visible in-game.

## 🗣️ Step 5: Implement the Command Interpreter and Game Logic

**Objective**: Create a robust command handling system that maps player inputs (e.g., `look`, `north`, `get sword`) to Python functions operating on the game state. Handle movement, inspection, object interaction, and basic feedback logic.

---

### 🧠 Codex Must Know:

- Characters are placed in rooms using the world model from Step 3.
- Room and object spawning is complete from Step 4.
- Each player command is a string line (e.g. `"look"`, `"get sword"`).
- ROM-style MUDs use `do_*` naming convention for commands.
- Some commands affect only the speaker (`look`), others affect room state (`drop`, `say`).
- Commands must produce output strings to be displayed to the player.
- Later steps will route these to telnet clients.

---

### 📁 Target File Structure:

```
mud/
├── commands/
│   ├── __init__.py
│   ├── dispatcher.py
│   ├── movement.py
│   ├── inspection.py
│   ├── inventory.py
│   ├── communication.py
│   └── combat.py
```

---

### ✅ Tasks and Subtasks

#### 1. Command Dispatch System

**1.1 Implement command registry in `dispatcher.py`:** ✅
```python
COMMANDS = {
  "look": do_look,
  "north": do_north,
  "south": do_south,
  "east": do_east,
  "west": do_west,
  "up": do_up,
  "down": do_down,
  "get": do_get,
  "drop": do_drop,
  "say": do_say,
}
```

**1.2 Add `process_command(char, input_str) -> str`:** ✅
- Tokenize `input_str` into `command` and `argument`.
- Lookup `COMMANDS[command]`.
- Call corresponding function with `(char, argument)`.
- Return output string (or list of lines) to be sent to user.

---

#### 2. Movement Commands (in `movement.py`)

**2.1 Define `do_north`, `do_south`, etc.:** ✅
- Call `move_character(char, "north")` from Step 3.
- Return movement message or error string.

---

#### 3. Inspection Commands (in `inspection.py`)

**3.1 Implement `do_look(char, args)`:** ✅
- Call `look(char)` from Step 3.
- Return full description of room, exits, contents, and other characters.

---

#### 4. Inventory Commands (in `inventory.py`)

**4.1 Implement `do_get(char, args)`:** ✅
- Parse target object name from args.
- Check if object exists in current room.
- Move to char’s inventory.
- Return message like `"You pick up a sword."`.

**4.2 Implement `do_drop(char, args)`:** ✅
- Remove object from inventory, place in room.
- Return confirmation.

**4.3 Optional: Add `do_inventory` to list carried items.** ✅

---

#### 5. Communication Commands (in `communication.py`)

**5.1 Implement `do_say(char, args)`:** ✅
- Return message `"You say, 'X'"` to speaker.
- Broadcast message to other characters in room: `"<Name> says, 'X'"`.

**5.2 Add room broadcast utility in `Room`:** ✅
```python
def broadcast(self, message: str, exclude=None)
```

---

#### 6. Error Handling and Fallbacks

**6.1 In `process_command()`, handle:** ✅
- Unknown commands: `"Huh?"`
- Empty input: ignore or return `"What?"`
- Missing arguments: `"Get what?"`

**6.2 Normalize input:** ✅
- Lowercase command.
- Trim whitespace.

---

#### 7. Simulated Driver for Testing

**7.1 Add `run_test_session()` function:** ✅
- Create test character in room.
- Feed a list of commands:
  - `["look", "get sword", "north", "say hello"]`
- Print each output to verify logic.

---

### 🧪 Final Output for Step 5:

- `process_command(char, "look")` → room description string.
- `process_command(char, "north")` → movement confirmation.
- `process_command(char, "get sword")` → updates inventory and returns text.
- Multiple commands tested in sequence with state transitions.

---

### ✅ Completion Criteria:

- Command routing is functional via `process_command`.
- Each command produces correct output and changes state.
- Behavior matches expectations from legacy ROM commands.
- Invalid input handled gracefully (no crashes or silent failures).
- Commands are modular and easy to extend.

---

### 🛠️ Follow-up Dependency:

- Step 6 (Networking) uses `process_command()` to respond to telnet clients.
- Step 7 (Testing and validation) will snapshot outputs for regression safety.

## ✅ Step 6: Introduce Networking (Asynchronous Server)

**Objective**: Create an asynchronous Telnet-compatible server using Python’s `asyncio` that accepts multiple concurrent connections, manages client input/output, and interfaces with the command interpreter from Step 5.

---

### 🧠 Codex Must Know:

- Each client connects via Telnet (TCP), line-by-line.
- `asyncio.start_server()` is used to bind the server to port 4000.
- Each connection maps to a `Character` object and input loop.
- Input is processed via `process_command(char, input_str)` (from Step 5).
- Each player must have a persistent I/O stream and character state.
- Output must use `\r\n` for Telnet compatibility.
- Prompting and login can be stubbed initially (e.g. name only).

---

### 📁 Target File Structure:

```
mud/
├── net/
│   ├── __init__.py
│   ├── telnet_server.py
│   ├── connection.py
│   ├── session.py
│   └── protocol.py
```

---

### ✅ Tasks and Subtasks

#### 1. Asynchronous Server Setup

**1.1 In `telnet_server.py`:**
- Implement `async def start_server()`:
  - Binds to `host='0.0.0.0', port=4000`
  - Uses `asyncio.start_server(handle_connection, host, port)`

**1.2 Add `if __name__ == "__main__"` runner to launch server.**

---

#### 2. Client Connection Handler

**2.1 In `connection.py`:**
- Define `async def handle_connection(reader, writer):`
  - Send welcome banner: `writer.write(b"Welcome to PythonMUD\r\n")`
  - Ask for name: `writer.write(b"What is your name?\r\n")`
  - Read input: `name = await reader.readline()`
  - Strip and lowercase name.
  - Create a new `Character` for the session.
  - Store connection in `char.connection = writer`.

**2.2 Start gameplay loop:**
- `while True:` loop:
  - Prompt with `> `.
  - Await input line.
  - Call `process_command(char, input_str)`
  - Send output via `writer.write(...) + await writer.drain()`

---

#### 3. Session Management

**3.1 In `session.py`:**
- Create `Session` dataclass:
  - Fields: `name`, `character`, `reader`, `writer`
- Optional: Store in global `SESSIONS: Dict[str, Session]`

**3.2 Add connection logging for diagnostics.**

---

#### 4. Output Handling

**4.1 Standardize `send_to_char(char, message)` helper:**
- Writes `message + "\r\n"` to `char.connection` (writer stream).
- Handles multi-line or list of outputs.

**4.2 Add prompt handling:**
- Always append `"> "` at end of command cycle.

---

#### 5. Broadcast Utilities

**5.1 In `protocol.py`:**
- Define `broadcast_room(room, message, exclude=None)`
  - Iterates over `room.characters`, calls `send_to_char()` for each.

**5.2 Use in `do_say()` and movement announcements.**

---

#### 6. Disconnection & Cleanup

**6.1 On EOF or disconnect:**
- Break loop, close `writer`.
- Remove character from room.
- Remove session from global session list.

---

### 🧪 Final Output for Step 6:

- Telnet client connects and sees a greeting.
- Enters name and is placed in default room (e.g. Midgaard temple).
- Types commands (`look`, `north`, etc.) and receives responses.
- Other players in room receive broadcast messages (e.g., `say hello`).

---

### ✅ Completion Criteria:

- Server accepts multiple concurrent clients via Telnet.
- Each connection maps to an independent character session.
- Input is read and passed to `process_command`.
- Output is formatted and delivered to correct player(s).
- Prompts appear after each command.
- Graceful disconnect without exceptions.

---

### 🛠️ Follow-up Dependency:

- Step 7 (Validation) will run scripted sessions through this server.
- Step 8 (Persistence) may attach DB-backed player login.

## ✅ Step 7: Validate and Refine – Iterative Testing & AI Collaboration

**Objective**: Implement an automated test suite and human-AI workflows to validate correctness of the Python MUD’s logic, ensure parity with the original C version, and improve reliability via continuous testing, snapshot comparisons, and scripted test sessions.

---

### 🧠 Codex Must Know:

- Commands are handled by `process_command(char, input_str)`.
- Game state is managed by Python objects: `Character`, `Room`, `MobInstance`, etc.
- The server can be run in a headless mode for offline tests.
- Step 2-6 outputs are deterministic and snapshot-friendly.
- Original behavior of the C MUD can be emulated for test assertions.

---

### 📁 Target File Structure:

```
mud/
├── tests/
│   ├── __init__.py
│   ├── test_commands.py
│   ├── test_world_load.py
│   ├── test_resets.py
│   ├── test_snapshot.py
│   └── scripts/
│       └── scripted_session.py
```

---

### ✅ Tasks and Subtasks

#### 1. Unit Tests for Core Systems

**1.1 `test_world_load.py`:**
- Load all areas from `area.lst`.
- Assert correct count of rooms, mobs, objs.
- Assert specific known room vnum exists (e.g. 3001).
- Assert that exits are linked (e.g. `room.exits["north"] is Room`).

**1.2 `test_resets.py`:**
- Apply resets for a sample area.
- Verify mobs/objects appear in correct rooms.
- Assert inventory relationships (e.g. mob has item).

**1.3 `test_commands.py`:**
- Create a dummy `Character` in a test room.
- Call `process_command(char, "look")` and assert output contains room name.
- Call movement commands and verify room transitions.
- Test `say`, `get`, `drop`, `inventory`.

---

#### 2. Snapshot Testing

**2.1 Implement `to_snapshot(obj)` in `test_snapshot.py`:**
- Serialize room state, inventory, and visible characters to dict/JSON.
- Write expected snapshot outputs to file: `snapshots/room_3001.json`.
- Compare actual to expected: diff on field-level.

**2.2 Add utility to `pytest` to auto-generate snapshots on first run.**

---

#### 3. Scripted Session Simulation

**3.1 In `scripted_session.py`:**
- Define a scripted sequence:
```python
script = [
  "look",
  "get sword",
  "north",
  "look",
  "say hello",
  "inventory"
]
```
- Feed each command to `process_command()` and capture results.
- Assert expected output for each step.

**3.2 Optional: Run this script through telnet client via subprocess (integration test).**

---

#### 4. Human-AI Assisted Test Expansion

**4.1 Prompt AI to identify edge cases for commands:**
- e.g., invalid direction, trying to pick up nonexistent item, talking in empty room.
- Use results to generate more test cases.

**4.2 Use AI to verify functional parity:**
- Input: Original C server output logs.
- AI compares Python outputs to legacy logs and highlights mismatches.

---

#### 5. CI & Regression Strategy

**5.1 Add `pytest` test suite runner.**
- Configure for GitHub Actions or CLI use.

**5.2 Ensure tests fail on any regressions or diff mismatches.**

**5.3 Document how to run:**
```bash
pytest mud/tests/
```

---

### 🧪 Final Output for Step 7:

- All core systems have unit tests with assertions.
- Snapshot tests catch structural changes in room/mob state.
- Scripted session simulates player interaction for regression testing.
- AI-assisted edge cases increase test coverage.
- All tests pass with clean CI output.

---

### ✅ Completion Criteria:

- `pytest` returns 100% pass.
- Known C behaviors are matched (e.g., correct room names, movement, object interactions).
- Snapshots exist for at least 3 representative rooms with mobs/objects.
- Scripted session outputs match expected game responses.
- New features or changes must not break existing tests.

---

### 🛠️ Follow-up Dependency:

- Step 8 (DB migration) should not break any snapshot or behavior tests.

## ✅ Step 8: Migrate Persistent Data to a Structured Database

**Objective**: Replace file-based world loading with a structured SQLAlchemy-backed database. Migrate `.are` file data into tables and create a runtime loader (`load_world_from_db()`) that populates all in-game registries using ORM queries.

---

### 🧠 Codex Must Know:

- World state is currently populated from `.are` flat files into `room_registry`, `mob_registry`, `obj_registry`.
- SQLAlchemy models exist in `mud.db.models`.
- The goal is to make the database the canonical source of truth and eliminate flat file reliance.

---

### 📁 Target File Structure:

```
mud/
├── db/
│   ├── models.py         # ORM declarations
│   ├── session.py        # SQLAlchemy engine/session setup
│   ├── migrate_from_files.py  # One-time migration script
│
├── world/
│   └── world_state.py    # Runtime game state loader
```

---

### ✅ Tasks and Subtasks

#### 1. Setup SQLAlchemy Infrastructure

- Already completed in `session.py` using `SessionLocal()` and `DATABASE_URL`.

---

#### 2. Define ORM Models (`models.py`)

- `Area`, `Room`, `Exit`, `MobPrototype`, `ObjPrototype`
- All use `declarative_base()` with relationships for area/room linkage.

---

#### 3. One-Time Migration from Files

- Already implemented in `migrate_from_files.py`:
  - Loads `.are` files with `load_all_areas()`
  - Converts each entry to ORM instance and persists to DB
  - Uses session management with `SessionLocal()`
  - Prints confirmation when done

---

#### 4. Implement `load_world_from_db()`

**Location**: `mud/world/world_state.py`

```python
from mud.db.session import SessionLocal
from mud.db.models import Room as DBRoom, Exit as DBExit, MobPrototype as DBMob, ObjPrototype as DBObj
from mud.registry import room_registry, mob_registry, obj_registry
from mud.models import Room, MobPrototype, ObjPrototype  # dataclass equivalents

def load_world_from_db():
    session = SessionLocal()

    # 1. Load rooms and build initial registry
    db_rooms = session.query(DBRoom).all()
    for db_room in db_rooms:
        room = Room(
            vnum=db_room.vnum,
            name=db_room.name,
            description=db_room.description,
            sector_type=db_room.sector_type,
            flags=db_room.room_flags,
            exits={}  # will populate in next pass
        )
        room_registry[room.vnum] = room

    # 2. Link exits using to_room_vnum
    db_exits = session.query(DBExit).all()
    for db_exit in db_exits:
        origin_room = session.query(DBRoom).get(db_exit.room_id)
        if origin_room is None:
            continue

        source = room_registry.get(origin_room.vnum)
        target = room_registry.get(db_exit.to_room_vnum)
        if source and target:
            source.exits[db_exit.direction] = target

    # 3. Load mobs
    db_mobs = session.query(DBMob).all()
    for db_mob in db_mobs:
        mob = MobPrototype(
            vnum=db_mob.vnum,
            name=db_mob.name,
            short_description=db_mob.short_desc,
            long_description=db_mob.long_desc,
            level=db_mob.level,
            alignment=db_mob.alignment
        )
        mob_registry[mob.vnum] = mob

    # 4. Load objects
    db_objs = session.query(DBObj).all()
    for db_obj in db_objs:
        obj = ObjPrototype(
            vnum=db_obj.vnum,
            name=db_obj.name,
            short_description=db_obj.short_desc,
            long_description=db_obj.long_desc,
            item_type=db_obj.item_type,
            flags=db_obj.flags,
            values=[db_obj.value0, db_obj.value1, db_obj.value2, db_obj.value3]
        )
        obj_registry[obj.vnum] = obj

    print(f"✅ Loaded {len(room_registry)} rooms, {len(mob_registry)} mobs, {len(obj_registry)} objects.")
    return True
```

---

#### 5. Modify Game Runtime Loader

- In the game entrypoint, replace:
```python
load_from_files("area.lst")
```
- With:
```python
load_world_from_db()
```

---

### ✅ Completion Criteria

- `room_registry`, `mob_registry`, and `obj_registry` are fully populated from database records.
- `room.exits["north"]` is a `Room`, not a vnum.
- All file-based parsing is removed or disabled.
- Server can start cleanly with no `.are` files present.
- Loading time is under 2 seconds for standard MUD datasets.

---

### 🧪 Validation Plan

- Run `pytest tests/` (from Step 7) and confirm no regressions.
- Verify output:
  ```
  ✅ Loaded 370 rooms, 58 mobs, 112 objects.
  ```
- Place a character in room 3001 and run `look()` to ensure data is linked.
- Try walking between rooms using movement commands to validate exits.

---

### 🛠️ Next Step

- ✅ Step 9 will handle saving player state, logout persistence, and eventually an admin panel or DB visualizer.

## ✅ Step 9: Add Character Saving and Persistence

**Objective**: Create persistent storage for players' character state using SQLAlchemy. Characters should be saved to the database on logout and reloaded on login, enabling continuity across sessions and restarts.

---

### 🧠 Codex Must Know:

- Characters are currently in-memory and lost between sessions.
- There is a distinction between:
  - `PlayerAccount`: represents the login credentials or identity.
  - `Character`: represents the avatar in-game (position, HP, inventory, etc).
- SQLAlchemy is used with a `SessionLocal` pattern.
- Dataclasses already exist for runtime character representations (`Character` or `PlayerCharacter`).

---

### ✅ Tasks and Subtasks

#### 1. Extend the ORM: Add Player and Character Tables ✅

**1.1 In `mud/db/models.py` add:**

```python
class PlayerAccount(Base):
    __tablename__ = "player_accounts"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)

    characters = relationship("Character", back_populates="player")

class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    level = Column(Integer)
    hp = Column(Integer)
    room_vnum = Column(Integer)

    player_id = Column(Integer, ForeignKey("player_accounts.id"))
    player = relationship("PlayerAccount", back_populates="characters")
```

> Optional: Add inventory and equipment as JSON or related tables.

---

#### 2. Add Conversion Functions ✅

**2.1 In `mud/models/character.py`:**

```python
def from_orm(db_char: DBCharacter) -> Character:
    return Character(
        name=db_char.name,
        level=db_char.level,
        hp=db_char.hp,
        room=room_registry.get(db_char.room_vnum, default_starting_room)
    )

def to_orm(character: Character, player_id: int) -> DBCharacter:
    return DBCharacter(
        name=character.name,
        level=character.level,
        hp=character.hp,
        room_vnum=character.room.vnum,
        player_id=player_id
    )
```

---

#### 3. Implement Character Load/Save Methods ✅

**3.1 In `mud/account/account_manager.py` or equivalent:**

```python
def load_character(username: str, char_name: str) -> Character:
    session = SessionLocal()
    db_char = session.query(DBCharacter).filter_by(name=char_name).first()
    return from_orm(db_char)

def save_character(character: Character):
    session = SessionLocal()
    db_char = session.query(DBCharacter).filter_by(name=character.name).first()
    if db_char:
        db_char.level = character.level
        db_char.hp = character.hp
        db_char.room_vnum = character.room.vnum
        session.commit()
```

---

#### 4. Hook Into Game Loop ✅

**4.1 On Player Login:**

- After login or `connect`, call `load_character()` using username and desired name.
- Spawn character into the correct room:
```python
char = load_character(username, char_name)
room = room_registry[char.room.vnum]
room.add_char(char)
```

**4.2 On Logout/Disconnect:**

- Call `save_character(char)` before deleting the session.

---

#### 5. Add Dev Utilities for Testing ✅

**5.1 In `mud/db/seed.py`:**

```python
def create_test_account():
    session = SessionLocal()
    account = PlayerAccount(username="admin", password_hash=hashlib.sha256(b"admin").hexdigest())
    char = Character(name="Testman", level=1, hp=100, room_vnum=3001, player=account)
    session.add(account)
    session.add(char)
    session.commit()
```

---

### ✅ Completion Criteria

- Players' characters persist after logout and server restart.
- Login restores characters to the correct room and state.
- Character cannot be duplicated or overwritten accidentally.
- `Character` table in DB reflects runtime changes (level, room, HP).

---

### 🧪 Tests and Verification

- Manually create an account with `create_test_account()`.
- Login as `Testman`, walk into another room, logout.
- Restart server, log back in — confirm state is restored.
- Add pytest: assert saved and reloaded state matches.

---

### 🛠️ Next Step

- [x] Step 10: Add Inventory and Equipment Persistence

## ✅ Step 10: Add Inventory and Equipment Persistence

**Objective**: Enable characters to carry and equip objects that persist in the database. Inventory and equipment should be loaded at login and saved at logout.

---

### 🧠 Codex Must Know:

- Items are currently represented as `ObjPrototype` (for prototypes) and `Object` (for instances).
- Characters have:
  - `inventory: List[Object]`
  - `equipment: Dict[str, Object]`  (e.g., `{"head": <helmet>, "feet": <boots>}`)
- SQLAlchemy is being used with `SessionLocal()`.
- Items may need an `id` separate from their prototype `vnum`.

---

### ✅ Tasks and Subtasks

#### 1. Add `ObjectInstance` ORM Table

**1.1 In `mud/db/models.py`:**

```python
class ObjectInstance(Base):
    __tablename__ = "object_instances"
    id = Column(Integer, primary_key=True)
    prototype_vnum = Column(Integer, ForeignKey("obj_prototypes.vnum"))
    location = Column(String)  # 'inventory', 'equipment:head', etc.
    character_id = Column(Integer, ForeignKey("characters.id"))

    prototype = relationship("ObjPrototype")
    character = relationship("Character", back_populates="objects")
```

**1.2 Extend `Character` model:**

```python
objects = relationship("ObjectInstance", back_populates="character")
```

---

#### 2. Update Runtime Models (if needed)

**2.1 In `mud/models/object.py`:**

```python
@dataclass
class Object:
    instance_id: Optional[int]
    prototype: ObjPrototype
```

**2.2 Character:**

```python
inventory: List[Object]
equipment: Dict[str, Object]
```

---

#### 3. Add Load/Save Functions

**3.1 In `mud/models/conversion.py`:**

```python
def load_objects_for_character(db_char: DBCharacter) -> Tuple[List[Object], Dict[str, Object]]:
    inventory = []
    equipment = {}

    for inst in db_char.objects:
        proto = obj_registry.get(inst.prototype_vnum)
        obj = Object(instance_id=inst.id, prototype=proto)
        if inst.location.startswith("equipment:"):
            slot = inst.location.split(":")[1]
            equipment[slot] = obj
        else:
            inventory.append(obj)

    return inventory, equipment

def save_objects_for_character(session, char: Character, db_char: DBCharacter):
    # Delete old instances
    session.query(DBObjectInstance).filter_by(character_id=db_char.id).delete()

    for obj in char.inventory:
        inst = DBObjectInstance(
            prototype_vnum=obj.prototype.vnum,
            location="inventory",
            character_id=db_char.id
        )
        session.add(inst)

    for slot, obj in char.equipment.items():
        inst = DBObjectInstance(
            prototype_vnum=obj.prototype.vnum,
            location=f"equipment:{slot}",
            character_id=db_char.id
        )
        session.add(inst)
```

---

#### 4. Integrate with Character Load/Save

**4.1 In `load_character()`:**

```python
char = from_orm(db_char)
char.inventory, char.equipment = load_objects_for_character(db_char)
```

**4.2 In `save_character()`:**

```python
save_objects_for_character(session, char, db_char)
session.commit()
```

---

### ✅ Completion Criteria

- Characters log in with correct items in `inventory` and `equipment`.
- Item instances are tied to the character, not just vnum.
- Picking up and equipping items updates the database at logout.
- Items are not duplicated or orphaned in the DB.

---

### 🧪 Tests and Validation

- Equip items in-game, logout, restart, and log back in. Validate state.
- Use `psql` or SQLite browser to inspect `object_instances` table.
- Add `pytest` test to:
  - Create a character.
  - Give them a sword and helmet.
  - Save + reload.
  - Assert restored objects match.

---

### 🔄 Optional Enhancements

- Add `ObjectInstance.extra_flags` for durability, charges, enchantments.
- Allow containers to hold other objects (parent-child relation).
- Add soft-delete (`is_deleted`) for item recovery/testing.

---

### 🛠️ Next Step

- Step 11 will implement **account creation, character selection**, and password authentication to allow proper user onboarding.

## ✅ Step 11: Account Creation and Authentication

**Objective**: Allow users to create accounts with secure passwords, authenticate at login, and manage multiple characters under one account. This replaces manual test-account creation and enables real-world usage.

---

### 🧠 Codex Must Know:

- `PlayerAccount` model already exists with fields:
  - `username: str`
  - `password_hash: str`
  - `characters: List[Character]`
- Passwords must be securely hashed with a salt (e.g., `bcrypt` or `pbkdf2_sha256`).
- Authentication happens **before** a player enters the game world.
- Character creation is a separate flow, gated by an existing account.

---

### ✅ Tasks and Subtasks

#### 1. Add Utility Functions for Hashing and Checking Passwords ✅

**1.1 In `mud/security/hash_utils.py`:**

```python
import hashlib
import os

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + hash.hex()

def verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, hash_hex = stored_hash.split(":")
    salt = bytes.fromhex(salt_hex)
    new_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return new_hash.hex() == hash_hex
```

---

#### 2. Add Account Creation Flow ✅

**2.1 In `mud/account/account_service.py`:**

```python
from mud.db.session import SessionLocal
from mud.db.models import PlayerAccount
from mud.security.hash_utils import hash_password, verify_password

def create_account(username: str, raw_password: str) -> bool:
    session = SessionLocal()
    if session.query(PlayerAccount).filter_by(username=username).first():
        return False  # Already exists
    account = PlayerAccount(
        username=username,
        password_hash=hash_password(raw_password)
    )
    session.add(account)
    session.commit()
    return True
```

---

#### 3. Add Login Flow ✅

```python
def login(username: str, raw_password: str) -> Optional[PlayerAccount]:
    session = SessionLocal()
    account = session.query(PlayerAccount).filter_by(username=username).first()
    if account and verify_password(raw_password, account.password_hash):
        return account
    return None
```

---

#### 4. Character Selection and Creation ✅

```python
def list_characters(account: PlayerAccount) -> List[str]:
    return [char.name for char in account.characters]

def create_character(account: PlayerAccount, name: str, starting_room_vnum: int = 3001) -> bool:
    session = SessionLocal()
    if session.query(Character).filter_by(name=name).first():
        return False  # Name taken
    new_char = Character(name=name, level=1, hp=100, room_vnum=starting_room_vnum, player_id=account.id)
    session.add(new_char)
    session.commit()
    return True
```

---

#### 5. Add a Temporary CLI Login Menu (for testing) ✅

**5.1 In `mud/entrypoint.py` or similar:**

```python
def prompt_login():
    print("Welcome to the Realm.")
    username = input("Username: ")
    password = input("Password: ")

    account = login(username, password)
    if not account:
        print("❌ Invalid login.")
        return None

    print(f"✅ Logged in as {username}")
    return account

def prompt_account_creation():
    print("Create your account:")
    username = input("Username: ")
    password = input("Password: ")
    confirm = input("Confirm Password: ")
    if password != confirm:
        print("❌ Passwords do not match.")
        return None

    success = create_account(username, password)
    if success:
        print("✅ Account created.")
    else:
        print("❌ Username already taken.")
```

---

### ✅ Completion Criteria

- Players can create an account and log in securely.
- Passwords are never stored in plaintext.
- A user can own multiple characters.
- Character creation is restricted to logged-in users.

---

### 🧪 Testing & Verification

- Create two accounts with different passwords.
- Try logging in with wrong password → get failure.
- Create a character, logout, login → see it in selection list.
- Confirm password hash in DB looks like: `salt:hash`.

---

### 🛠️ Next Step

- ✔ Step 12 will introduce **admin tools**, debugging commands (`@who`, `@teleport`, `@spawn`), and in-game state inspection for live world testing.

## ✅ Step 12: Admin Tools and Debug Commands

**Objective**: Add a set of privileged commands for admins to inspect world state, test gameplay, and moderate the game live. These commands are not player-accessible and should respect access levels or account flags.

---

### 🧠 Codex Must Know:

- The command system should already support per-user execution contexts.
- Admins should be able to:
  - See who's online.
  - Teleport to rooms.
  - Spawn NPCs or objects.
  - Save state manually.
- Admin status may be:
  - Hardcoded (`if account.username == "admin"`).
  - Or tracked via a new `is_admin` column in the DB.

---

### ✅ Tasks and Subtasks

#### 1. Add Admin Flag to Account (optional but better)

**1.1 In `mud/db/models.py`:**

```python
is_admin = Column(Boolean, default=False)
```

Set manually for now via DB or `seed.py`.

---

#### 2. Define Admin-Only Command Decorator

**2.1 In `mud/commands/decorators.py`:**

```python
def admin_only(func):
    def wrapper(context, *args, **kwargs):
        if not context.account or not context.account.is_admin:
            context.send("You do not have permission to use this command.")
            return
        return func(context, *args, **kwargs)
    return wrapper
```

---

#### 3. Add Admin Commands

**3.1 In `mud/commands/admin_commands.py`:**

```python
@admin_only
def cmd_who(context, *args):
    context.send("Online Players:")
    for player in get_online_players():
        context.send(f" - {player.name} in room {player.room.vnum}")

@admin_only
def cmd_teleport(context, room_vnum):
    if int(room_vnum) in room_registry:
        context.character.move_to(room_registry[int(room_vnum)])
        context.send(f"Teleported to room {room_vnum}")
    else:
        context.send("Invalid room.")

@admin_only
def cmd_spawn(context, npc_vnum):
    proto = npc_registry.get(int(npc_vnum))
    if not proto:
        context.send("NPC not found.")
        return
    mob = create_mob_from_proto(proto)
    context.character.room.add_npc(mob)
    context.send(f"Spawned {mob.name}.")
```

---

#### 4. Hook into Command Dispatcher

**4.1 In `mud/commands/dispatcher.py`:**

Add mappings like:

```python
commands = {
    "@who": cmd_who,
    "@teleport": cmd_teleport,
    "@spawn": cmd_spawn,
}
```

---

#### 5. Create Debug Save/Load Shortcut (Optional)

```python
@admin_only
def cmd_save(context):
    save_character(context.character)
    context.send("✅ Character saved.")
```

---

### ✅ Completion Criteria

- Admins can execute debug commands in real time.
- Players cannot access these without being flagged.
- Errors are handled gracefully with friendly feedback.
- World state changes (teleport, spawn) are live and visible.

---

### 🧪 Tests and Verification

- Flag a test account as `is_admin = True` in the DB.
- Log in and:
  - Run `@who` → see current players.
  - `@teleport 3001` → verify room change.
  - `@spawn 9001` → check for spawned mob.
- Try these commands on a non-admin account — verify rejection.

---

### 🛠️ Next Step

- ✅ Step 13 added **Agent Integration & World Interface**, so autonomous agents (AI NPCs, world editors) can interface cleanly with the Python runtime.

## ✅ Step 13: Agent Integration & World Interface

**Objective**: Build an abstract interface layer that exposes structured world state and actions. This will let agents observe the game world, plan actions, and issue valid commands — enabling AI-controlled NPCs, automated testing, or LLM-driven world builders.

---

### 🧠 Codex Must Know:

- An “agent” is any external system that needs to read world state and issue actions.
- The MUD runtime should expose:
  - Structured state (room, inventory, surroundings).
  - Valid actions (movement, speech, combat, equip, drop).
  - Feedback (what happened as a result).
- This step **does not require ML or OpenAI API usage** — just a clean abstraction.

---

### ✅ Tasks and Subtasks

#### 1. Define Agent Interface Protocol

**1.1 In `mud/agent/agent_protocol.py`:**

```python
from abc import ABC, abstractmethod
from typing import Dict, List

class AgentInterface(ABC):
    @abstractmethod
    def get_observation(self) -> Dict:
        """Return structured game state view."""
        pass

    @abstractmethod
    def get_available_actions(self) -> List[str]:
        """Return a list of valid actions the agent can choose from."""
        pass

    @abstractmethod
    def perform_action(self, action: str, args: List[str]) -> str:
        """Execute an action in-game. Returns textual feedback."""
        pass
```

---

#### 2. Create an Adapter for Characters

**2.1 In `mud/agent/character_agent.py`:**

```python
class CharacterAgentAdapter(AgentInterface):
    def __init__(self, character):
        self.character = character

    def get_observation(self):
        return {
            "name": self.character.name,
            "room": {
                "vnum": self.character.room.vnum,
                "name": self.character.room.name,
                "description": self.character.room.description,
                "npcs": [npc.name for npc in self.character.room.npcs],
                "players": [p.name for p in self.character.room.players if p != self.character],
                "exits": list(self.character.room.exits.keys()),
            },
            "inventory": [obj.prototype.name for obj in self.character.inventory],
            "equipment": {slot: obj.prototype.name for slot, obj in self.character.equipment.items()},
            "hp": self.character.hp,
            "level": self.character.level
        }

    def get_available_actions(self):
        return ["move", "say", "pickup", "drop", "equip", "attack"]

    def perform_action(self, action, args):
        try:
            if action == "move":
                direction = args[0]
                return self.character.move(direction)
            elif action == "say":
                return self.character.say(" ".join(args))
            elif action == "pickup":
                return self.character.pickup(args[0])
            elif action == "drop":
                return self.character.drop(args[0])
            elif action == "equip":
                return self.character.equip(args[0])
            elif action == "attack":
                return self.character.attack(args[0])
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"⚠️ Error: {str(e)}"
```

---

#### 3. Register an Agent-Controlled NPC

**3.1 Example usage in `mud/devtools/agent_demo.py`:**

```python
def run_agent_demo():
    room = room_registry[3001]
    mob = create_mob_from_proto(npc_registry[9001])
    adapter = CharacterAgentAdapter(mob)
    room.add_npc(mob)

    print(adapter.get_observation())
    print(adapter.perform_action("say", ["I", "am", "alive!"]))
```

---

#### 4. Add Logging (for LLM agent reflection)

**4.1 In `mud/logging/agent_trace.py`:**

```python
def log_agent_action(agent_id, observation, action, result):
    with open(f"logs/agent_{agent_id}.log", "a") as f:
        f.write(f"\nOBS: {observation}\nACT: {action}\nRES: {result}\n{'='*40}\n")
```

Call this after every `perform_action()` in agent loop.

---

### ✅ Completion Criteria

- Any in-game character (or NPC) can be wrapped with an `AgentInterface`.
- The interface returns structured game state as JSON-like dicts.
- Actions can be simulated or executed programmatically.
- Logs show behavior over time for testing or LLM loop tuning.

---

### 🧪 Tests and Validation

- Wrap a live character with `CharacterAgentAdapter`.
- Print their `get_observation()` state.
- Try a `perform_action("say", ["hi there"])` call.
- Wrap a dummy mob and simulate movement across rooms using `perform_action("move", ["north"])`.

---

### 🛠️ Next Step

- Step 14 will address **Deployment, CLI Wrappers, and Dockerization**, to prepare the project for production and developer onboarding.

## 🚀 Step 14: Deployment, CLI Tools, and Dockerization

**Objective**: Finalize the project for real-world use by wrapping it with CLI tools, `.env`-based config, and Docker support. This enables easy server bootstrapping, environment separation, and deployment consistency.

---

### 🧠 Codex Must Know:

- The project is now a modern Python backend with:
  - `SQLAlchemy` for DB.
  - CLI entrypoints.
  - In-memory game state.
- Needs:
  - `mud.py runserver`
  - `mud.py migrate`
  - Docker support.
  - `.env`-based configuration for secrets, ports, DB URL, etc.

---

### ✅ Tasks and Subtasks

#### 1. Add `.env` Support for Config

**1.1 In `mud/config.py`:**

```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///mud.db")
PORT = int(os.getenv("PORT", 5000))
```

**1.2 Create `.env` in project root:**

```env
DATABASE_URL=sqlite:///mud.db
PORT=5000
```

---

#### 2. Create Unified CLI Entrypoint

**2.1 In `mud/__main__.py`:**

```python
import typer
from mud.server import run_game_loop
from mud.db.migrations import run_migrations

cli = typer.Typer()

@cli.command()
def runserver():
    run_game_loop()

@cli.command()
def migrate():
    run_migrations()

if __name__ == "__main__":
    cli()
```

**2.2 Add `__main__.py` to `pyproject.toml`:**

```toml
[tool.poetry.scripts]
mud = "mud.__main__:cli"
```

Now you can run:

```bash
poetry run mud runserver
poetry run mud migrate
```

---

#### 3. Write Migration Script

**3.1 In `mud/db/migrations.py`:**

```python
from mud.db.session import Base, engine

def run_migrations():
    Base.metadata.create_all(bind=engine)
    print("✅ Migrations complete.")
```

---

#### 4. Add Docker Support

**4.1 In `Dockerfile`:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false && poetry install

COPY . .

CMD ["mud", "runserver"]
```

**4.2 In `docker-compose.yml`:**

```yaml
version: "3.8"
services:
  mud:
    build: .
    ports:
      - "${PORT:-5000}:5000"
    env_file:
      - .env
    volumes:
      - .:/app
```

**4.3 Build & Run:**

```bash
docker-compose build
docker-compose up
```

---

#### 5. Optional: Add Health Check or Logs Viewer

**5.1 In `mud/server.py`:**

```python
def run_game_loop():
    print("🌍 Starting MUD server...")
    # game tick, event loop, etc.
```

**5.2 Logs saved under `/logs` from earlier steps.**

---

### ✅ Completion Criteria

- Project starts with `mud runserver` or `docker-compose up`.
- Migrations run cleanly via `mud migrate`.
- Environment config is isolated via `.env`.
- Dockerized build works on any machine.

---

### 🧪 Tests and Verification

- Clone repo fresh on another machine or Docker container.
- Run `mud migrate` → tables created.
- Run `mud runserver` → server boots.
- Run `docker-compose up` → server available on `localhost:5000`.
- Validate `.env` overrides (e.g. try different `PORT`).

---

### 🧭 Project Status: ✅ Core Migration Complete

You have now fully migrated a C-based MUD engine with text and `.h`-based data into:

- 🐍 A modern, modular **Python backend**
- 🗃️ Powered by SQLAlchemy and SQLite/PostgreSQL
- 🧱 Room/NPC/Object parsing via `.are` or DB
- 🧠 Agent-compatible AI layer with structured I/O
- 🚀 Deployable via Docker and CLI tools

---

### 🛠️ Optional Future Enhancements

- 🌐 Web-based Admin UI (Flask + HTMX or FastAPI + React)
- 📡 Multiplayer socket server (e.g., websockets or Telnet adapter)
- 🧑‍💻 Builder tools via text or prompt interface
- 🪄 AI quest/NPC generator via GPT agentic planner
- 📖 Export world state to visual graph (e.g., Graphviz)

---

## 🌐 Step 15 Addendum: Telnet Access via Docker + Test Character Loader

---

### ✅ Part 1: Expose Telnet Port in Docker

Your multiplayer MUD runs on TCP port `5000`. We need to make sure this is accessible when running via Docker.

#### 1.1 Update `.env` (if not already)

```env
PORT=5000
```

#### 1.2 Update `docker-compose.yml`

```yaml
version: "3.8"
services:
  mud:
    build: .
    ports:
      - "${PORT:-5000}:5000"  # expose 5000 for Telnet
    env_file:
      - .env
    volumes:
      - .:/app
    command: poetry run mud socketserver
```

#### 1.3 Test It

```bash
docker-compose up
```

Then in a new terminal:

```bash
telnet localhost 5000
```

You should see:

```
Welcome to the MUD!
Login:
```

---

### ✅ Part 2: Add a Dev Command to Load Test Accounts

We want an easy way to insert test data: account + character.

#### 2.1 In `mud/scripts/load_test_data.py`:

```python
from mud.db.session import Session
from mud.models import PlayerAccount, Character
from mud.world.rooms import load_rooms  # or similar if rooms are preloaded

def load_test_user():
    db = Session()

    # Create test account
    account = PlayerAccount(username="test", email="test@example.com")
    account.set_password("test123")
    db.add(account)
    db.flush()

    # Create character
    char = Character(name="Tester", hp=100, room_vnum=3001, account_id=account.id)
    db.add(char)
    db.commit()
    print("✅ Test user created: login=test / pw=test123")
```

#### 2.2 Register with CLI

In `mud/__main__.py`:

```python
@cli.command()
def loadtestuser():
    from mud.scripts.load_test_data import load_test_user
    load_test_user()
```

Now run:

```bash
poetry run mud migrate
poetry run mud loadtestuser
poetry run mud socketserver
```

---

### 🧪 Confirm Working Setup

1. Connect via:
   ```bash
   telnet localhost 5000
   ```
2. Login:
   ```
   Login: test
   Password: test123
   ```
3. Interact using commands like `look`, `say`, `get`, etc.
4. Connect in another terminal and try again. Both sessions should share world state.

## 🚀 STEP 16: Add WebSocket Adapter for Browser Play & Future Agents

### 🎯 Goal:
Add WebSocket support alongside the Telnet server so players (or bots) can connect via modern web clients. This allows you to later build an in-browser UI or connect autonomous agents over WebSockets.

---

### ✅ Overview:

- Create a lightweight WebSocket server using **FastAPI + `websockets`** or **`starlette.websockets`**
- Accept browser connections
- Reuse existing `PlayerSession` and game loop logic
- Allow each WebSocket client to control a character
- Structure I/O for easy parsing by future LLM-based clients

---

### 🔲 Task 1: Add WebSocket Server

- [x] File: `mud/network/websocket_server.py`
- [x] Use `FastAPI` or `Starlette` to expose `/ws`
- [x] Accept `websocket` connections and hold open
- [x] Upgrade the WebSocket into a `PlayerSession`

Prompt:
```
Use FastAPI to open a /ws WebSocket route. On connection, wrap into a PlayerSession-like object with .send() and .recv().
```

Validation:
- `websocat ws://localhost:8000/ws` opens connection.

---

### 🔲 Task 2: Create WebSocketPlayerSession

- [x] File: `mud/network/websocket_session.py`
- [x] Define a subclass of `PlayerSession` that wraps a `WebSocket` object
- [x] Implement `.send()` and `.recv()` using JSON messages
- [x] Add metadata: `session_type = "websocket"`

Prompt:
```
Subclass PlayerSession using a WebSocket object. All messages should be JSON with fields: type, text, metadata.
```

---

### 🔲 Task 3: Bind to Game Loop

- [x] In `websocket_server.py`, call `handle_session()` as in socket version
- [x] Allow one character per session
- [x] Handle disconnects gracefully

Validation:
- Web client logs in, issues `look`, receives output

---

### 🔲 Task 4: JSON I/O Format

- [x] Standardize message format:
  ```json
  {
    "type": "output",
    "text": "You are standing in a quiet room.",
    "room": 3001,
    "hp": 34
  }
  ```
- [x] Parse inputs as:
  ```json
  {
    "type": "command",
    "text": "say hello"
  }
  ```

Prompt:
```
Wrap all messages in JSON for structured LLM parsing. Include type, content, and optional metadata.
```

---

### 🔲 Task 5: Add CORS and Host Config

- [x] File: `mud/config.py`
- [x] Allow configurable CORS origins via `.env`
- [x] Add `--host 0.0.0.0 --port 8000` for Docker

Validation:
- Browser frontend can connect from a different origin
- No CORS errors

---

### 🔲 Task 6: CLI Entrypoint

- [x] In `mud/__main__.py`, add command:
  ```bash
  poetry run mud websocketserver
  ```
- [x] Serve on `localhost:8000` or `0.0.0.0:8000`

Validation:
- Multiple users connect via `/ws`
- Each has independent session

---

### 🧪 Completion Criteria

- [x] `poetry run mud websocketserver` launches server
- [x] Browser or `websocat` clients can connect to `/ws`
- [x] Each session logs in, enters game loop, and runs commands
- [x] Messages are in structured JSON format
- [x] Works in Docker with port 8000 exposed

---

### 🔮 Optional Extensions

- Add logging of all WebSocket events
- Build a barebones browser UI in React or Svelte
- Support LLM input via message type: `"agent_command"`
- a sample frontend React client
- automatic login via token auth
- agent memory/state integration over `/ws`



### 🧠 future enhancements

Would you like:

- ANSI color output for telnet?
- Scripting interface for programmable NPCs?
- WebSocket adapter for browser-based play?
- Session timeouts & player reconnection support?

Let me know and we’ll queue it up.
