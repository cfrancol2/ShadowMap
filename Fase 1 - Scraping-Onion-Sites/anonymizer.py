# Módulo de anonimización de PII para la capa de ingesta.


from __future__ import annotations

import hashlib
import re
from typing import Any, Dict


class PIIAnonymizer:
    # Anonimiza campos sensibles usando reemplazo por hash estable

    def __init__(self, salt: str = "titulacion-ti") -> None:
        self.salt = salt
        self.patterns = {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "ipv4": re.compile(
                r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
            ),
            "onion": re.compile(r"\b[a-z2-7]{16,56}\.onion\b", flags=re.IGNORECASE),
            "btc": re.compile(r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b"),
        }

    def _hash(self, value: str) -> str:
        return hashlib.sha256(f"{self.salt}:{value}".encode("utf-8")).hexdigest()[:16]

    def anonymize_username(self, username: str | None) -> str | None:
        if not username:
            return username
        return f"USER_{self._hash(username)}"

    def anonymize_text(self, text: str | None) -> str | None:
        if not text:
            return text

        result = text
        for label, pattern in self.patterns.items():
            for match in pattern.findall(result):
                token = f"{label.upper()}_{self._hash(match)}"
                result = result.replace(match, token)
        return result

    def anonymize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(record)

        # Mantener username original para análisis de tendencias
        # if "username" in out:
        #     out["username"] = self.anonymize_username(out.get("username"))

        for field in ("titulo", "cuerpo", "texto_citado"):
            if field in out:
                out[field] = self.anonymize_text(out.get(field))

        return out
