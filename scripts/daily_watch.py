"""Script exécutable pour le déclenchement de la veille quotidienne automatique.

Peut être invoqué par le Planificateur de tâches Windows, cron ou GitHub Actions :
    python scripts/daily_watch.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import storage
from services.alerts import run_all_alerts


def main():
    print("=" * 60)
    print("Cap Marchés · Exécution de la veille quotidienne automatique")
    print("=" * 60)

    searches = storage.list_saved_searches()
    active_alerts = [s for s in searches if s.get("alerts_enabled")]
    print(f"Recherches sauvegardées : {len(searches)} (dont {len(active_alerts)} avec alertes activées)")

    if not active_alerts:
        print("Aucune alerte active configurée. Activez des veilles depuis l'interface.")
        return

    results = run_all_alerts(force_all=False)
    for res in results:
        print(f"\n🔍 Veille : {res['search_name']}")
        print(f"   Opportunités analysées : {res['total_found']}")
        print(f"   Nouvelles opportunités détectées : {res['new_count']}")
        print(f"   Statut de diffusion : {res['status']} (canal: {res['channel']})")

    stats = storage.seen_stats()
    print("\n" + "-" * 60)
    print(f"Bilan base locale : {stats['seen_total']} marchés indexés | {stats['sirene_cached']} acheteurs en cache Sirene")
    print("=" * 60)


if __name__ == "__main__":
    main()
