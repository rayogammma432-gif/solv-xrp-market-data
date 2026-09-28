#!/usr/bin/env python3
import getpass
import json
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"


def main():
    if not CONFIG.exists():
        raise SystemExit(f"No existe {CONFIG}. Primero configura el recolector.")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    token = getpass.getpass("Pega el token del bot de Telegram (no se mostrará): ").strip()
    if not token:
        raise SystemExit("Token vacío.")

    s = requests.Session()
    base = f"https://api.telegram.org/bot{token}"

    me = s.get(base + "/getMe", timeout=20)
    me.raise_for_status()
    me_data = me.json()
    if not me_data.get("ok"):
        raise SystemExit(f"Token inválido: {me_data}")

    username = me_data["result"].get("username", "")
    print(f"Bot verificado: @{username}")
    print("Ahora abre ese bot en Telegram, pulsa START y envía /start.")
    input("Cuando lo hayas hecho, presiona Enter aquí... ")

    upd = s.get(base + "/getUpdates", params={"limit": 100, "timeout": 2}, timeout=10)
    upd.raise_for_status()
    data = upd.json()
    if not data.get("ok"):
        raise SystemExit(f"getUpdates falló: {data}")

    chats = []
    seen = set()
    for item in data.get("result", []):
        msg = item.get("message") or item.get("edited_message")
        if not msg:
            continue
        chat = msg.get("chat") or {}
        cid = chat.get("id")
        if cid is None or cid in seen:
            continue
        seen.add(cid)
        label = (
            chat.get("username")
            or " ".join(x for x in [chat.get("first_name"), chat.get("last_name")] if x)
            or chat.get("title")
            or str(cid)
        )
        chats.append((cid, label))

    if not chats:
        raise SystemExit("No encontré ningún chat. Envía /start al bot y vuelve a ejecutar este script.")

    if len(chats) == 1:
        chat_id, label = chats[0]
    else:
        print("Chats encontrados:")
        for i, (cid, label) in enumerate(chats, 1):
            print(f"{i}. {label} ({cid})")
        raw = input("Selecciona número: ").strip()
        idx = int(raw) - 1
        chat_id, label = chats[idx]

    cfg["telegram"] = {
        "enabled": True,
        "assets": ["solv"],
        "bot_token": token,
        "chat_id": str(chat_id),
    }

    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    test = s.post(
        base + "/sendMessage",
        json={
            "chat_id": str(chat_id),
            "text": "✅ Alertas SOLV/XRP conectadas al Motorola. Detector preliminar activo al reiniciar el recolector.",
        },
        timeout=20,
    )
    test.raise_for_status()
    tdata = test.json()
    if not tdata.get("ok"):
        raise SystemExit(f"No pude enviar prueba: {tdata}")

    print(f"Telegram configurado para: {label}")
    print("Token y chat_id quedaron guardados SOLO en termux/config.json.")
    print("Ahora reinicia el recolector para activar las alertas.")


if __name__ == "__main__":
    main()
