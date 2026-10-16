"""Deterministic whole-group allocation; no filename-based independence claims."""
import random
from collections import Counter,defaultdict

PRESETS={'standard':[70,20,10],'small':[80,20,0]}

def assign_groups(samples,key,ratios,seed):
    buckets=defaultdict(list)
    for s in samples:buckets[key(s)].append(s)
    keys=sorted(buckets);random.Random(seed).shuffle(keys);keys.sort(key=lambda g:len(buckets[g]),reverse=True)
    names=['train','val','test'];active=[n for n,r in zip(names,ratios) if r>0];targets=dict(zip(names,[len(samples)*r/100 for r in ratios]));counts=Counter();groups=Counter();assignment={}
    def features(rows):
        result=Counter(o['label_id'] for s in rows for o in s['annotation']['objects'])
        result['__normal__']=sum(s['annotation']['image_tag']=='NORMAL' for s in rows);result['__abnormal__']=sum(s['annotation']['image_tag']=='ABNORMAL' for s in rows)
        return result
    totals=features(samples);by_class={n:Counter() for n in names}
    for i,g in enumerate(keys):
        missing=[n for n in active if not groups[n]];options=missing if len(keys)-i<=len(missing) else active
        classes=features(buckets[g])
        def cost(n):
            size=sum(((counts[k]+(len(buckets[g]) if k==n else 0)-targets[k])/max(1,targets[k]))**2 for k in active)
            quality=sum(((by_class[k][c]+(classes[c] if k==n else 0)-totals[c]*ratios[names.index(k)]/100)/max(1,totals[c]))**2 for c in totals for k in active)
            return size+.25*quality
        chosen=min(options,key=cost);assignment[g]=chosen;counts[chosen]+=len(buckets[g]);groups[chosen]+=1;by_class[chosen].update(classes)
    return assignment

def split_statistics(samples,ratios):
    result={};total=len(samples)
    for name,ratio in zip(['train','val','test'],ratios):
        rows=[s for s in samples if s['split']==name]
        cross_sources={s.get('source_group_id',s['media_id']) for s in rows if any(b.get('source_group_id',b['media_id'])==s.get('source_group_id',s['media_id']) and b['split']!=name for b in samples)}
        near=any(a['split']!=b['split'] and (int(a['perceptual_hash'],16)^int(b['perceptual_hash'],16)).bit_count()<=4 for a in rows for b in samples)
        duplicate=len(rows)-len({s['sha256'] for s in rows})
        result[name]={'duplicate_hashes':duplicate,'cross_source_groups':len(cross_sources),'leakage_status':'无样本' if not rows else 'LIMITED' if cross_sources or near or duplicate else 'PASS','target_percent':ratio,'images':len(rows),'actual_percent':len(rows)*100/total if total else 0,'normal':sum(s['annotation']['image_tag']=='NORMAL' for s in rows),'abnormal':sum(s['annotation']['image_tag']=='ABNORMAL' for s in rows),'objects':sum(len(s['annotation']['objects']) for s in rows),'source_groups':len({s.get('source_group_id',s['media_id']) for s in rows}),'classes':dict(Counter(o['label_id'] for s in rows for o in s['annotation']['objects']))}
    return result
