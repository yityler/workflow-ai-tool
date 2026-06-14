## Question 2: 
Python Challenge: Log Analyzer

Each LLM is given a list of server log entries:

```python
logs = [
  "2026-06-14 10:01:23 ERROR User login failed user_id=12",
  "2026-06-14 10:01:25 INFO User login success user_id=15",
  "2026-06-14 10:02:10 ERROR Database timeout",
  "2026-06-14 10:03:00 ERROR User login failed user_id=12",
]

```

Tasks:
Write a Python function that:

1. Counts how many logs are of each level (`INFO`, `ERROR`, etc.)
2. Finds the most common error message (ignore timestamps and user_id values)
3. Extracts all unique `user_id`s involved in ERROR logs
Output format requirement:
Return ONLY a Python dictionary in this exact structure:

```python
{
  "counts": {"INFO": 1, "ERROR": 3},
  "top_error": "User login failed",
  "error_users": {12}
}

```
## Responses

Claude:

```python
import re
from collections import Counter

def analyze_logs(logs):
    counts = Counter()
    error_messages = []
    error_users = set()

    for line in logs:
        date, time, level, rest = line.split(maxsplit=3)
        counts[level] += 1

        if level == "ERROR":
            match = re.search(r'user_id=(\d+)', rest)
            if match:
                error_users.add(int(match.group(1)))
                message = re.sub(r'\s*user_id=\d+', '', rest).strip()
            else:
                message = rest.strip()
            error_messages.append(message)

    top_error = Counter(error_messages).most_common(1)[0][0] if error_messages else None

    return {
        "counts": dict(counts),
        "top_error": top_error,
        "error_users": error_users
    }
```

Running this on the provided `logs` returns:

```python
{
  'counts': {'ERROR': 3, 'INFO': 1},
  'top_error': 'User login failed',
  'error_users': {12}
}
```
Gemini:
```python
def analyze_logs(logs):
    counts = {}
    error_msgs = {}
    error_users = set()

    for log in logs:
        parts = log.split()
        if len(parts) < 3:
            continue
            
        level = parts[2]
        counts[level] = counts.get(level, 0) + 1
        
        if level == "ERROR":
            msg_parts = []
            for part in parts[3:]:
                if part.startswith("user_id="):
                    user_id = int(part.split("=")[1])
                    error_users.add(user_id)
                else:
                    msg_parts.append(part)
            
            base_msg = " ".join(msg_parts)
            error_msgs[base_msg] = error_msgs.get(base_msg, 0) + 1
            
    top_error = max(error_msgs, key=error_msgs.get) if error_msgs else None
    
    return {
        "counts": counts,
        "top_error": top_error,
        "error_users": error_users
    }

# Example usage based on your provided data
logs = [
  "2026-06-14 10:01:23 ERROR User login failed user_id=12",
  "2026-06-14 10:01:25 INFO User login success user_id=15",
  "2026-06-14 10:02:10 ERROR Database timeout",
  "2026-06-14 10:03:00 ERROR User login failed user_id=12",
]

# print(analyze_logs(logs))
# Output: {'counts': {'ERROR': 3, 'INFO': 1}, 'top_error': 'User login failed', 'error_users': {12}}

```
Grok:
**Solution**

```python
from collections import Counter
from typing import List, Dict, Set, Any


def analyze_logs(logs: List[str]) -> Dict[str, Any]:
    """
    Analyzes server log entries.

    Returns:
        {
            "counts": {"INFO": int, "ERROR": int, ...},
            "top_error": str,           # most common error message (without user_id)
            "error_users": set[int]     # unique user_ids from ERROR logs
        }
    """
    level_counts = Counter()
    error_core_messages = Counter()
    error_users: Set[int] = set()

    for line in logs:
        if not line.strip():
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        level = parts[2]
        level_counts[level] += 1

        if level == "ERROR":
            message_parts = parts[3:]
            core_parts = []

            for token in message_parts:
                if token.startswith("user_id="):
                    try:
                        uid = int(token.split("=", 1)[1])
                        error_users.add(uid)
                    except (ValueError, IndexError):
                        pass
                else:
                    core_parts.append(token)

            core_message = " ".join(core_parts)
            if core_message:
                error_core_messages[core_message] += 1

    counts = dict(level_counts)
    top_error = error_core_messages.most_common(1)[0][0] if error_core_messages else ""

    return {
        "counts": counts,
        "top_error": top_error,
        "error_users": error_users
    }
```

### How to use

```python
logs = [
    "2026-06-14 10:01:23 ERROR User login failed user_id=12",
    "2026-06-14 10:01:25 INFO User login success user_id=15",
    "2026-06-14 10:02:10 ERROR Database timeout",
    "2026-06-14 10:03:00 ERROR User login failed user_id=12",
]

result = analyze_logs(logs)
print(result)
```

**Output:**
```python
{'counts': {'ERROR': 3, 'INFO': 1}, 'top_error': 'User login failed', 'error_users': {12}}
```

## Summary
Each LLM used different methods but arrived at the right solution. 

Claude ranked highest in this task because of its 
- clean-code readability
- use of regex patterns (Ex: re.search(r'user_id=(\d+)', rest)
- assumption of unstructured data (Ex: split(maxsplit=3) instead of relying on fixed indices like part[2])

Grok and Gemini, on the other hand, assume the logs have a fixed structure and write their code accordingly

Therefore, Claude's response would be superior for real-world application because of it ability to detect and decode 
variable logs more efficiently.
