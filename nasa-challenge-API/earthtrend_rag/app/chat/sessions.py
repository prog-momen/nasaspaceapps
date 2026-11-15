"""In-memory, bounded, isolated chat sessions. Nothing is shared between sessions; history and memory are capped."""
from __future__ import annotations

import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

MAX_SESSIONS = 40
SESSION_TTL_S = 6 * 3600
MAX_TURNS = 100          # turns kept (the model reads as many as fit in the context budget, see agent.CONTEXT_TOKENS)
MAX_TEXT = 4000          # characters kept per stored message


@dataclass
class Session:
    id: str
    created: float = field(default_factory=time.time)
    touched: float = field(default_factory=time.time)
    history: list[dict] = field(default_factory=list)          # {"role": "user"|"assistant", "text": str, "meta": {...}}
    memory: dict = field(default_factory=dict)                 # location, period, variable, last_tool -- only what the LAST turn actually used
    busy: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, role: str, text: str, meta: dict | None = None) -> None:
        self.history.append({"role": role, "text": text[:MAX_TEXT], "meta": meta or {}})
        del self.history[:-2 * MAX_TURNS]
        self.touched = time.time()

    def reset(self) -> None:
        self.history.clear()
        self.memory.clear()
        self.touched = time.time()


class SessionStore:
    def __init__(self, max_sessions: int = MAX_SESSIONS, ttl: float = SESSION_TTL_S):
        self._s: "OrderedDict[str, Session]" = OrderedDict()
        self._lock = threading.Lock()
        self.max, self.ttl = max_sessions, ttl

    def get(self, sid: str | None, create: bool = True) -> Session | None:
        with self._lock:
            now = time.time()
            for k in [k for k, v in self._s.items() if now - v.touched > self.ttl]:
                del self._s[k]
            if sid and sid in self._s:
                self._s.move_to_end(sid)
                return self._s[sid]
            if not create:
                return None
            s = Session(id=uuid.uuid4().hex[:16])
            self._s[s.id] = s
            while len(self._s) > self.max:
                self._s.popitem(last=False)
            return s

    def drop(self, sid: str) -> bool:
        with self._lock:
            return self._s.pop(sid, None) is not None

    def __len__(self) -> int:
        return len(self._s)
