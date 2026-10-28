"""Read-only PRL payout limits. No wallet signing, trading or transaction APIs."""
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import urllib.parse
import urllib.request


def interpret(balance, payouts):
    def value(key):
        n=Decimal(str(balance[key]))
        if not n.is_finite() or n<0:raise ValueError('Invalid pool amount: '+key)
        return n
    total,confirmed,pending,threshold=(value(k) for k in ('total','confirmed','unconfirmed','threshold'))
    if threshold<=0 or threshold>100000 or abs(total-confirmed-pending)>Decimal('0.0000001'):
        raise ValueError('Inconsistent pool balances or invalid threshold')
    count=payouts['count']
    if isinstance(count,bool) or not isinstance(count,int) or count<0:raise ValueError('Invalid payout count')
    return dict(total=str(total),confirmed=str(confirmed),unconfirmed=str(pending),
                threshold=str(threshold),payout_count=count,
                goal_reached=count>0 or total>=threshold)


def remaining_seconds(state_path, now=None):
    state=json.loads(Path(state_path).read_text(encoding='utf-8-sig'))
    deadline=datetime.fromisoformat(state['MiningDeadline'])
    if deadline.tzinfo is None:raise ValueError('Saved experience deadline must have a timezone')
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('Current time must have a timezone')
    return max(0,int((deadline-now).total_seconds()))


def fetch(wallet):
    encoded=urllib.parse.quote(wallet,safe='')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data=[]
    for endpoint in ('balance','payouts'):
        url=f'https://pool.kryptex.com/prl/api/v1/miner/{endpoint}/{encoded}'
        with opener.open(urllib.request.Request(url,headers={'User-Agent':'Xiaotutou-Pearl-Source/1.0'}),timeout=8) as response:
            data.append(json.load(response,parse_float=Decimal))
    return interpret(*data)
