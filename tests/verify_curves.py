import sys, asyncio
sys.path.insert(0, 'D:/referral_engine/src')
from referral_engine import storage

async def main():
    curves = await storage.list_curves()
    print(f"Total curves in DB: {len(curves)}")
    stats = await storage.get_stats()
    print(f"Stats: {stats['total']} total, by archetype: {stats['by_archetype']}")
    for c in curves:
        print(f"  {c['user_id']:<16} {c['archetype']:<14} reach={c['reach_score']:>3} adv={c['advocacy_score']:>3} pcu={c['pcu']:>5} budget={c['total_budget']:>10.2f} steps={c['step_count']:>5}")

asyncio.run(main())
