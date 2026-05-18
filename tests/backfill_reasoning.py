"""Backfill reasoning for all users without it."""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from referral_engine import storage

async def main():
    progress = await storage.list_progress()
    updated = 0
    for p in progress:
        if p.get('reasoning', '').strip():
            continue
        curve = await storage.load_curve(p['user_id'])
        if not curve:
            continue
        reasoning = (
            f"Tier={p['archetype']} Reach={p.get('curves_reach', curve.get('reach_score','?'))} "
            f"Adv={p.get('curves_adv', curve.get('advocacy_score','?'))} "
            f"PCU={p['referrals_target']} "
            f"Penalty={((1-p['penalty_factor'])*100):.0f}% "
            f"Budget={curve.get('total_budget',0):.0f} "
            f"Steps={curve.get('step_count','?')} — "
            f"{p['archetype']} curve with {curve.get('step_count','?')} steps targeting {p['referrals_target']} referrals. "
            f"Penalty at {((1-p['penalty_factor'])*100):.0f}% reduction. "
            f"Hook reward at first step, valley tests commitment, surge builds momentum, plateau caps at target."
        )
        await storage.save_progress(p['user_id'], {**p, 'reasoning': reasoning, 'updated_at': p.get('updated_at','')})
        updated += 1
        print(f'  Updated: {p["user_id"]}')
    
    if not updated:
        print('All users already have reasoning.')
    else:
        print(f'\nUpdated {updated} users with reasoning.')

asyncio.run(main())
