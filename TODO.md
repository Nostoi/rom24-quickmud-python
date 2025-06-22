# TODO

- [x] Step 1: Define Python Data Models (Autonomous Codex Execution)

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

