"""Схематичная периферическая нервная система для атласа.

Пути нервов строятся по реальным ориентирам модели BodyParts3D: позвоночному каналу
(по межпозвоночным дискам), рёбрам, мышцам и осевым линиям артерий, рядом с которыми
нервы идут в теле. Это учебная схема, а не точная реконструкция.
"""
from geo import *
import numpy as np, re, json, gzip, os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else D

def C(pat):  # центр детали
    v = V(pat); assert v is not None, pat; return v.mean(0)
def B(pat):
    v = V(pat); assert v is not None, pat; return v.min(0), v.max(0)
def CL(pat, n=12):
    v = V(pat); assert v is not None, pat; return centerline(v, n)
def mir(p, s):  # s=+1 левая сторона (x>0), -1 правая
    p = np.array(p, float).copy(); p[..., 0] *= s; return p
def side(pat, s):
    return pat.replace('{S}', 'Left' if s > 0 else 'Right').replace('{s}', 'left' if s > 0 else 'right')

# ---------- позвоночный канал по дискам ----------
DISKS = []
for p in A['parts']:
    m = re.match(r'Intervertebral disk of (\w+) (cervical|thoracic|lumbar) vertebra$', p['en'], re.I)
    if m or p['en'].lower() == 'intervertebral disk of axis':
        v = verts(p)
        DISKS.append(dict(name=p['en'], y=v[:, 1].mean(), zmin=v[:, 2].min(), zmax=v[:, 2].max(),
                          zc=v[:, 2].mean(), half=np.abs(v[:, 0]).max()))
DISKS.sort(key=lambda d: -d['y'])
ORD = ['axis', 'third cervical', 'fourth cervical', 'fifth cervical', 'sixth cervical', 'seventh cervical'] + \
      [f'{w} thoracic' for w in ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh']] + \
      [f'{w} lumbar' for w in ['first', 'second', 'third', 'fourth', 'fifth']]
def disk(label):
    for d in DISKS:
        if label in d['name'].lower(): return d
    raise KeyError(label)
DL = [disk(l) for l in ORD]  # C2/3 … L5/S1, сверху вниз
def canal(d, back=0.010):
    return np.array([0.0, d['y'], d['zmin'] - back])

# уровни спинномозговых нервов → диск, под которым выходит нерв (упрощённо)
# C3..C8 → диски C2/3..C7/T1, T1..T11 → T1/2..T11/12, T12 → T12/L1 (≈ между T12 и L1), L1..L5 → L1/2..L5/S1
T12 = C('Twelfth thoracic vertebra'); L1v = C('First lumbar vertebra')

MED = C('Medulla oblongata')
cord_top = np.array([0, B('Medulla oblongata')[0][1] + 0.004, MED[2] - 0.004])
spine = [cord_top] + [canal(d) for d in DL]
conus_y = (disk('first lumbar')['y'] + C('Second lumbar vertebra')[1]) / 2
SAC = V('^sacrum$'); sac_c = SAC.mean(0)

nerves = []  # dict(key, ru, en, side, pts, r, desc)
def add(key, ru, en, pts, r, s=0, desc=''):
    nerves.append(dict(key=key, ru=ru, en=en, side=s, pts=np.array(pts, float), r=r, desc=desc))

# ---------- спинной мозг и конский хвост ----------
cord = [p for p in spine if p[1] >= conus_y - 0.01]
cord.append(np.array([0, conus_y, canal(disk('first lumbar'))[2]]))
add('spinal_cord', 'Спинной мозг', 'Spinal cord', cord, 0.0045)
for k, dx in enumerate([0.0015, 0.0035]):
    for s in (1, -1):
        pts = [np.array([s * dx * 0.4, conus_y + 0.004, cord[-1][2]])] + \
              [canal(d) + [s * dx, 0, 0] for d in DL if d['y'] < conus_y] + \
              [np.array([s * dx, sac_c[1] + 0.03, sac_c[2] - 0.012]), np.array([s * dx * 0.6, sac_c[1] - 0.04, sac_c[2] - 0.004])]
        add('cauda_equina', 'Конский хвост', 'Cauda equina', pts, 0.0011, s)

# ---------- спинномозговые нервы ----------
def foramen(d, s, lumbar=False):
    x = d['half'] + (0.004 if not lumbar else 0.006)
    return np.array([s * x, d['y'] - 0.002, d['zmin'] - 0.004])
def cord_point(y):
    pts = np.array(cord); i = np.argmin(np.abs(pts[:, 1] - y)); return pts[i]
LEVEL = {}
names_c = ['C3', 'C4', 'C5', 'C6', 'C7', 'C8']
names_t = [f'T{i}' for i in range(1, 12)]
names_l = ['T12', 'L1', 'L2', 'L3', 'L4']
for nm, d in zip(names_c + names_t + names_l, DL):
    LEVEL[nm] = d
LEVEL['L5'] = disk('fifth lumbar')
F = {}
for nm, d in list(LEVEL.items()):
    for s in (1, -1):
        f = foramen(d, s, nm.startswith('L'))
        if nm.startswith('L') or nm == 'T12':
            # корешки поясничных нервов спускаются в канале от конуса
            start = np.array([s * 0.002, conus_y + 0.006, cord[-1][2]])
            pts = [start, np.array([s * 0.003, d['y'] + 0.01, f[2] - 0.002]), f]
        else:
            start = cord_point(d['y'] + 0.012) + [s * 0.003, 0, 0]
            pts = [start, f]
        F[(nm, s)] = f
        add('spinal_root', f'Спинномозговой нерв {nm}', f'Spinal nerve {nm}', pts, 0.0016, s)

# ---------- шейное сплетение ----------
for s in (1, -1):
    scm = C(side('{S} sternocleidomastoid', s))
    for nm in ['C3', 'C4']:
        f = F[(nm, s)]
        add('cervical_plexus', 'Шейное сплетение', 'Cervical plexus',
            [f, f + [s * 0.012, -0.004, 0.012], scm + [s * 0.012, 0.01 * (nm == 'C3'), 0.004]], 0.0011, s)

# ---------- плечевое сплетение и нервы руки ----------
def arm(s):
    ax = CL(side('{S} axillary artery', s), 8)
    br = CL(side('{S} brachial artery', s), 12)
    ra = CL(side('{S} radial artery', s), 12)
    ul = CL(side('{S} ulnar artery', s), 12)
    hum_lo, hum_hi = B(side('{S} humerus', s))
    hum = CL(side('{S} humerus', s), 10)
    plex = ax[len(ax) // 2] + [0, 0.008, -0.006]
    sca = C(side('{S} scalenus anterior', s))
    trunk_mid = np.array([sca[0] + s * 0.012, sca[1] - 0.03, sca[2] - 0.006])
    for nm in ['C5', 'C6', 'C7', 'C8', 'T1']:
        f = F[(nm, s)]
        add('brachial_plexus', 'Плечевое сплетение', 'Brachial plexus', [f, f + [s * 0.012, -0.006, 0.004], trunk_mid, plex], 0.0019, s)
    start = plex
    palm = C(side('{S} superficial palmar arterial arch', s))
    ph = {k: C(f'Proximal phalanx of {side("{s}", s)} {k}') for k in ['thumb', 'index finger', 'middle finger', 'ring finger', 'little finger']}
    fore_mid = (ra[::-1][:len(ul)][::-1] + ul[:len(ra)]) / 2 if len(ra) == len(ul) else ra
    # срединный нерв
    med = [start] + [p + [s * 0.004, 0, 0.006] for p in ax[len(ax) // 2 + 1:]] + [p + [s * 0.005, 0, 0.007] for p in br] + \
          [p + [0, 0, 0.004] for p in fore_mid[1:]] + [palm + [0, 0.01, 0.004]]
    add('median', 'Срединный нерв', 'Median nerve', med, 0.0024, s,
        'Проходит по передней поверхности плеча и предплечья к кисти через запястный канал. Управляет большинством сгибателей предплечья и мышцами возвышения большого пальца, даёт чувствительность ладонной стороне I–III пальцев. Его сдавление в запястье — синдром запястного канала.')
    for k in ['thumb', 'index finger', 'middle finger']:
        add('median_digital', 'Пальцевые ветви срединного нерва', 'Digital branches of median nerve', [palm + [0, 0.01, 0.004], ph[k] + [0, 0, 0.006]], 0.0011, s)
    # локтевой нерв: медиальнее, за медиальным надмыщелком
    epi = np.array([hum_lo[0] if s > 0 else hum_hi[0], hum_lo[1] + 0.012, hum[-1][2] - 0.012])
    ulp = [start] + [p + [-s * 0.008, -0.01 * i, -0.006] for i, p in enumerate(br[: len(br) // 2])] + \
          [epi + [s * 0.003, 0.02, 0], epi] + [p + [-s * 0.004, 0, -0.002] for p in ul[2:]] + [palm + [-s * 0.012, 0.012, 0.0]]
    add('ulnar', 'Локтевой нерв', 'Ulnar nerve', ulp, 0.0022, s,
        'Идёт по медиальной стороне руки и огибает медиальный надмыщелок плеча — это «смешная косточка», удар по которой отдаёт в мизинец. Иннервирует большинство мелких мышц кисти и кожу IV–V пальцев.')
    for k in ['ring finger', 'little finger']:
        add('ulnar_digital', 'Пальцевые ветви локтевого нерва', 'Digital branches of ulnar nerve', [palm + [-s * 0.012, 0.012, 0.0], ph[k] + [0, 0, 0.005]], 0.001, s)
    # лучевой нерв: по спиральной борозде сзади плечевой кости
    mid = hum[len(hum) // 2]
    lat_epi = np.array([hum_hi[0] if s > 0 else hum_lo[0], hum_lo[1] + 0.03, hum[-1][2] + 0.004])
    rad = [start, start + [s * 0.006, -0.02, -0.014], hum[3] + [-s * 0.006, 0, -0.018], mid + [0, 0, -0.016], hum[-3] + [s * 0.014, 0, -0.006],
           lat_epi] + [p + [s * 0.009, 0, -0.001] for p in ra[1:-2]] + [ra[-1] + [s * 0.012, -0.004, -0.012], ph['thumb'] + [0, 0.012, -0.012]]
    add('radial', 'Лучевой нерв', 'Radial nerve', rad, 0.0024, s,
        'Самая толстая ветвь плечевого сплетения. Огибает плечевую кость сзади по спиральной борозде и управляет разгибателями руки — трицепсом, разгибателями запястья и пальцев. При его повреждении кисть «свисает».')
    # мышечно-кожный нерв
    mc = [start, start + [s * 0.01, -0.02, 0.012]] + [p + [0, 0, 0.026] for p in hum[3:-1]] + [lat_epi + [0, 0, 0.018]] + \
         [p + [s * 0.012, 0, 0.004] for p in ra[1:5]]
    add('musculocutaneous', 'Мышечно-кожный нерв', 'Musculocutaneous nerve', mc, 0.0016, s,
        'Прободает клювовидно-плечевую мышцу, иннервирует двуглавую и плечевую мышцы (сгибание в локте), а затем даёт чувствительность латеральной стороне предплечья.')
    # подмышечный нерв
    top = np.array([hum[0][0], hum_hi[1] - 0.04, hum[0][2] - 0.022])
    axn = [start, start + [s * 0.008, -0.012, -0.012], top, top + [s * 0.02, 0.006, 0.008]]
    add('axillary', 'Подмышечный нерв', 'Axillary nerve', axn, 0.0015, s,
        'Огибает хирургическую шейку плечевой кости сзади и иннервирует дельтовидную и малую круглую мышцы — отведение руки в плечевом суставе.')
for s in (1, -1): arm(s)

# ---------- межрёберные нервы ----------
RIB = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth']
def rib_curve(v, s, n=22):
    c = np.array([0, v[:, 1].mean(), -0.01])
    th = np.arctan2(v[:, 2] - c[2], s * v[:, 0])
    pts = []
    for a, b in zip(np.linspace(th.min(), th.max(), n + 1)[:-1], np.linspace(th.min(), th.max(), n + 1)[1:]):
        m = (th >= a) & (th <= b)
        if m.sum() > 2:
            q = v[m]; lo = q[:, 1].min(); pts.append(np.array([q[:, 0].mean(), lo + 0.001, q[:, 2].mean()]))
    pts = np.array(pts)
    if pts[0][2] > pts[-1][2]: pts = pts[::-1]  # сзади → вперёд
    return pts
for i in range(1, 12):
    nm = f'T{i}'
    for s in (1, -1):
        v = V(side(f'{{S}} {RIB[i-1]} rib', s))
        rc = rib_curve(v, s)
        # отступаем внутрь от ребра (нерв лежит в борозде у нижнего края)
        cx = np.array([0, 0, -0.01])
        inward = [p + (cx - p) * np.array([0.06, 0, 0.06]) for p in rc]
        pts = [F[(nm, s)]] + inward[1:]
        if i >= 7:  # нижние нервы продолжаются в переднюю брюшную стенку
            end = inward[-1]
            y = end[1] - 0.012 * (i - 6)
            pts += [np.array([end[0] * 0.75, y, end[2] + 0.004]), np.array([s * 0.02, y - 0.02, end[2] + 0.004])]
        ru = 'Подрёберный нерв' if i == 12 else f'Межрёберный нерв {nm}'
        add('intercostal', ru, f'Intercostal nerve {nm}', pts, 0.0012, s,
            'Межрёберные нервы идут в бороздах под рёбрами вместе с одноимёнными артерией и веной. Иннервируют межрёберные мышцы, кожу груди, а нижние — мышцы и кожу передней брюшной стенки.')
for s in (1, -1):  # T12 — подрёберный
    v = V(side('{S} twelfth rib', s)); rc = rib_curve(v, s)
    pts = [F[('T12', s)]] + [p * [1.06, 1, 1] for p in rc[1:]] + [np.array([s * 0.09, rc[-1][1] - 0.04, 0.03]), np.array([s * 0.04, rc[-1][1] - 0.07, 0.05])]
    add('intercostal', 'Подрёберный нерв', 'Subcostal nerve', pts, 0.0012, s)

# ---------- поясничное и крестцовое сплетения, нервы ноги ----------
def leg(s):
    psoas = CL(side('{S} psoas major', s), 10)
    fa = CL(side('{S} femoral artery', s), 10)
    eia = CL(side('{S} external iliac artery', s), 6)
    pop = CL(side('{S} popliteal artery', s), 10)
    pta = CL(side('{S} posterior tibial artery', s), 12)
    ata = CL(side('{S} anterior tibial artery', s), 12)
    gsv = CL(side('{S} great saphenous vein', s), 24)
    fem = CL(side('{S} femur', s), 14)
    flo, fhi = B(side('{S} femur', s))
    fib_lo, fib_hi = B(side('{S} fibula', s))
    piri = V(side('{S} piriformis', s))
    hip_lo, hip_hi = B(side('{S} hip bone', s))
    # поясничное сплетение — в толще большой поясничной мышцы
    plex = psoas[len(psoas) // 2]
    for nm in ['L1', 'L2', 'L3', 'L4']:
        f = F[(nm, s)]
        add('lumbar_plexus', 'Поясничное сплетение', 'Lumbar plexus', [f, f + [s * 0.01, -0.01, 0.004], plex + [0, 0.01 * (4 - int(nm[1])), 0]], 0.0019, s)
    # бедренный нерв: латеральнее бедренной артерии
    inguinal = eia[-1] + [s * 0.014, 0, 0]
    femn = [plex, psoas[-3] + [s * 0.008, 0, 0.01], inguinal] + [p + [s * 0.012, 0, 0] for p in fa[1:4]]
    add('femoral', 'Бедренный нерв', 'Femoral nerve', femn, 0.0028, s,
        'Крупнейшая ветвь поясничного сплетения. Выходит на бедро под паховой связкой латеральнее бедренной артерии и иннервирует четырёхглавую мышцу — разгибание колена — и кожу передней поверхности бедра.')
    for k, dz in enumerate([0.02, 0.0, -0.01]):  # мышечные ветви к четырёхглавой мышце
        a = fa[3] + [s * 0.012, 0, 0]
        add('femoral_branches', 'Мышечные ветви бедренного нерва', 'Muscular branches of femoral nerve',
            [a, a + [s * (0.02 + 0.01 * k), -0.06 - 0.03 * k, dz + 0.01]], 0.0012, s)
    knee_med = np.array([flo[0] if s > 0 else fhi[0], flo[1] + 0.01, fem[-1][2] + 0.004])
    saph = [fa[3] + [s * 0.006, 0, 0]] + [p + [s * 0.003, 0, -0.004] for p in fa[4:]] + [knee_med] + \
           [p + [0, 0, -0.003] for p in gsv if p[1] < knee_med[1] - 0.03]
    add('saphenous', 'Подкожный нерв', 'Saphenous nerve', saph, 0.0013, s,
        'Самая длинная чувствительная ветвь бедренного нерва. Идёт вместе с большой подкожной веной по внутренней стороне колена и голени до стопы.')
    # запирательный нерв
    obt = C(side('{S} obturator externus', s)); adl = C(side('{S} adductor longus', s))
    obn = [plex, psoas[-4] + [-s * 0.012, 0, -0.016], np.array([s * 0.05, 0.9, -0.02]), obt + [-s * 0.01, 0.006, 0.01], adl + [-s * 0.006, 0.04, 0], adl + [0, -0.06, -0.004]]
    add('obturator', 'Запирательный нерв', 'Obturator nerve', obn, 0.0018, s,
        'Проходит по боковой стенке таза и через запирательное отверстие выходит на внутреннюю поверхность бедра, где иннервирует приводящие мышцы.')
    # латеральный кожный нерв бедра
    asis = np.array([hip_hi[0] if s > 0 else hip_lo[0], hip_hi[1] - 0.03, hip_hi[2] - 0.006])
    lfc = [plex, psoas[3] + [s * 0.03, -0.02, 0.0], asis + [-s * 0.01, -0.005, 0], asis + [-s * 0.006, -0.04, 0.004],
           np.array([fem[len(fem) // 2][0] + s * 0.05, fem[len(fem) // 2][1], fem[len(fem) // 2][2] + 0.02])]
    add('lat_fem_cut', 'Латеральный кожный нерв бедра', 'Lateral femoral cutaneous nerve', lfc, 0.0011, s)
    # подвздошно-паховый нерв (L1)
    ii = [F[('L1', s)], psoas[2] + [s * 0.03, 0, -0.01], np.array([s * (abs(asis[0]) - 0.03), asis[1] + 0.03, asis[2] - 0.02]),
          asis + [-s * 0.02, 0.01, 0.02], np.array([s * 0.035, asis[1] - 0.06, asis[2] + 0.04])]
    add('ilioinguinal', 'Подвздошно-паховый нерв', 'Ilioinguinal nerve', ii, 0.0011, s)
    # крестцовое сплетение и седалищный нерв
    pc = piri.mean(0); plow = piri[piri[:, 1] < np.percentile(piri[:, 1], 20)].mean(0)
    sp = np.array([s * 0.035, pc[1] + 0.004, pc[2] + 0.012])
    sac_front = np.array([s * 0.028, sac_c[1] + 0.02, sac_c[2] + 0.02])
    for nm in ['L4', 'L5']:
        f = F[(nm, s)]
        add('sacral_plexus', 'Пояснично-крестцовый ствол', 'Lumbosacral trunk', [f, f + [s * 0.008, -0.02, 0.012], sac_front + [s * 0.006, 0.02, 0], sp], 0.0022, s)
    for k in range(3):  # передние крестцовые отверстия S1–S3
        y = sac_c[1] + 0.035 - 0.03 * k
        a = np.array([s * 0.016, y, sac_c[2] + 0.004 - 0.012 * k])
        add('sacral_plexus', 'Крестцовое сплетение', 'Sacral plexus', [a, a + [s * 0.01, -0.006, 0.004], sp], 0.0019, s)
    gt = np.array([fhi[0] if s > 0 else flo[0], fhi[1] - 0.04, fem[0][2] - 0.02])
    isch = np.array([s * 0.05, 0.86, -0.06])
    back = [p + [-s * 0.004, 0, -0.026] for p in fem[3:-2]]
    split = pop[1] + [0, 0.02, -0.012]
    sci = [sp, plow + [-s * 0.004, -0.004, 0.006], (gt + isch) / 2 + [0, 0, -0.01]] + back + [split]
    add('sciatic', 'Седалищный нерв', 'Sciatic nerve', sci, 0.0045, s,
        'Самый толстый и длинный нерв тела — толщиной с палец. Выходит из таза под грушевидной мышцей, идёт по задней поверхности бедра и над коленом делится на большеберцовый и общий малоберцовый нервы. Его раздражение вызывает ишиас — боль, отдающую в ногу.')
    for k in range(2):
        a = back[2 + 3 * k]
        add('sciatic_branches', 'Ветви седалищного нерва к мышцам бедра', 'Muscular branches of sciatic nerve', [a, a + [-s * 0.01 * (1 - 2 * k), -0.05, -0.008]], 0.0013, s)
    # большеберцовый нерв
    mal = pta[-1]
    mp = CL(side('{S} medial plantar artery', s), 6); lp = CL(side('{S} lateral plantar artery', s), 6)
    tib = [split] + [p + [0, 0, -0.008] for p in pop[3:]] + [p + [0, 0, -0.006] for p in pta[1:]] + [mal + [0, -0.01, -0.004]]
    add('tibial', 'Большеберцовый нерв', 'Tibial nerve', tib, 0.0032, s,
        'Продолжение седалищного нерва в подколенной ямке. Идёт в глубине задней поверхности голени, огибает медиальную лодыжку и делится на подошвенные нервы. Управляет икроножной мышцей и сгибателями пальцев.')
    add('plantar', 'Медиальный подошвенный нерв', 'Medial plantar nerve', [mal + [0, -0.01, -0.004]] + [p + [0, 0.004, 0] for p in mp], 0.0015, s)
    add('plantar', 'Латеральный подошвенный нерв', 'Lateral plantar nerve', [mal + [0, -0.01, -0.004]] + [p + [0, 0.004, 0] for p in lp], 0.0014, s)
    # общий малоберцовый нерв огибает головку малоберцовой кости
    fh = np.array([fib_hi[0] if s > 0 else fib_lo[0], fib_hi[1] - 0.025, -0.03])
    cf = [split, split + [s * 0.02, -0.03, -0.006], fh + [s * 0.006, 0, -0.004], fh + [s * 0.004, -0.02, 0.016]]
    add('common_fibular', 'Общий малоберцовый нерв', 'Common fibular nerve', cf, 0.0026, s,
        'Огибает головку малоберцовой кости прямо под кожей — поэтому легко травмируется (например, если долго сидеть нога на ногу). Делится на глубокую и поверхностную ветви, поднимающие стопу.')
    dp = CL(side('{S} dorsalis pedis artery', s), 5)
    deep = [cf[-1]] + [p + [s * 0.004, 0, 0.004] for p in ata[2:]] + [p + [0, 0.004, 0.002] for p in dp]
    add('deep_fibular', 'Глубокий малоберцовый нерв', 'Deep fibular nerve', deep, 0.0016, s)
    fib = CL(side('{S} fibula', s), 12)
    sup = [cf[-1]] + [p + [s * 0.012, 0, 0.012] for p in fib[3:-1]] + [dp[-2] + [s * 0.018, 0.012, 0.004]]
    add('superficial_fibular', 'Поверхностный малоберцовый нерв', 'Superficial fibular nerve', sup, 0.0014, s)
    # половой нерв
    pud = V(side('{S} internal pudendal vein', s))
    pud_c = centerline(pud, 6) if pud is not None else None
    pn = [sp, plow + [-s * 0.012, -0.012, -0.004], np.array([s * 0.035, 0.86, -0.05]), np.array([s * 0.02, 0.84, -0.01]), np.array([s * 0.008, 0.848, 0.03])]
    add('pudendal', 'Половой нерв', 'Pudendal nerve', pn, 0.0013, s)
for s in (1, -1): leg(s)

# ---------- блуждающий, диафрагмальный нервы, симпатический ствол ----------
for s in (1, -1):
    ijv = CL(side('{S} internal jugular vein', s), 6)
    cca = CL(side('{S} common carotid artery', s), 6)
    eso = CL('^Esophagus$', 14)
    st = V('^Stomach$')
    jug = np.array([s * 0.022, B('Medulla oblongata')[0][1] + 0.01, -0.02])
    neck = [(a + b) / 2 + [0, 0, -0.008] for a, b in zip(ijv, cca)]
    thor = [p + [s * 0.008, 0, -0.002 * s] for p in eso if p[1] < neck[-1][1] - 0.02]
    stomach = st.mean(0) + [0, 0.02, 0.03 * s]
    vag = [MED + [s * 0.012, 0, 0], jug] + neck + thor + [stomach]
    add('vagus', 'Блуждающий нерв', 'Vagus nerve', vag, 0.0018, s,
        'X пара черепных нервов — самый длинный из них. Выходит из продолговатого мозга, спускается по шее рядом с сонной артерией и внутренней яремной веной и иннервирует сердце, лёгкие, желудок и кишечник. Замедляет сердечный ритм и усиливает пищеварение.')
    # возвратный гортанный нерв
    if s > 0:
        arch = V('^Arch of aorta$'); a = arch[arch[:, 1].argmin()] + [0, -0.006, 0]
    else:
        sa = CL('Right subclavian artery', 6); a = sa[1] + [0, -0.008, 0]
    tr = CL('^Trachea$', 6)
    hook = min(vag, key=lambda p: abs(p[1] - a[1]))
    rln = [hook, a + [s * 0.004, 0, 0.004], a + [s * 0.002, -0.004, -0.012], tr[2] + [s * 0.012, 0, -0.008], tr[0] + [s * 0.011, 0.02, -0.006]]
    add('recurrent_laryngeal', 'Возвратный гортанный нерв', 'Recurrent laryngeal nerve', rln, 0.0011, s,
        'Ветвь блуждающего нерва, которая огибает снизу аорту (слева) или подключичную артерию (справа) и возвращается вверх к гортани. Управляет голосовыми связками.')
    # диафрагмальный нерв
    sca = C(side('{S} scalenus anterior', s))
    hv = V('Heart|ventricle|atrium|^Aorta$|Pulmonary trunk')
    hv = hv[hv[:, 1] < 1.43]
    dia = V('^Diaphragm$')
    path = [F[('C4', s)], sca + [0, 0.02, 0.006], sca + [0, -0.02, 0.008]]
    for y in np.linspace(1.40, 1.28, 6):
        sl = hv[np.abs(hv[:, 1] - y) < 0.01]
        if len(sl): path.append(np.array([sl[:, 0].max() + 0.008 if s > 0 else sl[:, 0].min() - 0.008, y, sl[:, 2].mean() + 0.01]))
    top = dia[(np.abs(dia[:, 0] - s * 0.075) < 0.012)]
    path.append(top[top[:, 1].argmax()] + [0, 0.004, 0])
    add('phrenic', 'Диафрагмальный нерв', 'Phrenic nerve', path, 0.0013, s,
        'Отходит от шейного сплетения (C3–C5), спускается по передней лестничной мышце и сбоку от сердца к диафрагме. Единственный нерв, управляющий главной дыхательной мышцей; икота — непроизвольное сокращение диафрагмы.')
    # симпатический ствол с узлами
    chain = [np.array([s * (d['half'] * 0.75), d['y'], d['zc'] + 0.012]) for d in DL]
    chain = [np.array([s * 0.024, B('Atlas')[0][1], DL[0]['zc'] + 0.012])] + chain + \
            [np.array([s * 0.02, sac_c[1] + 0.03, sac_c[2] + 0.024]), np.array([s * 0.004, sac_c[1] - 0.06, sac_c[2] + 0.012])]
    add('sympathetic_trunk', 'Симпатический ствол', 'Sympathetic trunk', chain, 0.0012, s,
        'Цепочка нервных узлов вдоль позвоночника — часть вегетативной нервной системы. Отвечает за реакцию «бей или беги»: учащает пульс, расширяет зрачки и бронхи, сужает сосуды кожи.')
    for k, p in enumerate(chain[1:-1]):
        add('sympathetic_ganglion', 'Узел симпатического ствола', 'Sympathetic ganglion', [p + [0, 0.003, 0], p - [0, 0.003, 0]], 0.0028, s)

# ---------- черепные нервы, которых нет в исходных данных ----------
for s in (1, -1):
    pons = C('^Pons$') + [s * 0.016, 0, 0.006]
    tb_lo, tb_hi = B(side('{S} temporal bone', s))
    zyg = C(side('{S} zygomatic bone', s))
    mx = C('maxilla')
    ml, mh = B('^Mandible$')
    gang = np.array([s * 0.022, 1.588, 0.002])
    add('trigeminal', 'Тройничный нерв', 'Trigeminal nerve', [pons, gang], 0.0026, s,
        'V пара черепных нервов — главный чувствительный нерв лица. От тройничного узла отходят три ветви: глазная, верхнечелюстная и нижнечелюстная. Также управляет жевательными мышцами.')
    add('trigeminal_v2', 'Верхнечелюстной нерв', 'Maxillary nerve', [gang, gang + [s * 0.004, -0.004, 0.02], np.array([s * 0.026, 1.585, 0.06]), np.array([s * 0.028, 1.58, 0.078])], 0.0016, s)
    add('trigeminal_v3', 'Нижнечелюстной нерв', 'Mandibular nerve',
        [gang, gang + [s * 0.006, -0.02, 0.004], np.array([s * 0.04, 1.545, 0.02]), np.array([s * 0.034, 1.52, 0.045]), np.array([s * 0.02, 1.515, 0.068])], 0.0016, s)
    sty = np.array([s * 0.044, tb_lo[1] + 0.004, -0.02])
    fac = [pons + [0, -0.006, 0], np.array([s * 0.036, 1.588, -0.018]), sty]
    add('facial', 'Лицевой нерв', 'Facial nerve', fac, 0.0018, s,
        'VII пара черепных нервов. Выходит из черепа позади уха и веером расходится по лицу ветвями к мимическим мышцам: лба, век, щёк, губ и шеи. При его воспалении половина лица «застывает».')
    fan = sty + [s * 0.008, -0.002, 0.016]
    add('facial', 'Лицевой нерв', 'Facial nerve', [sty, fan], 0.0016, s)
    for tgt in [[0.05, 1.63, 0.05], [0.055, 1.6, 0.055], [0.05, 1.57, 0.06], [0.04, 1.548, 0.068], [0.046, 1.522, 0.05], [0.04, 1.5, 0.03]]:
        add('facial_branches', 'Ветви лицевого нерва', 'Branches of facial nerve', [fan, (fan + mir(tgt, s)) / 2 + [s * 0.006, 0, 0], mir(tgt, s)], 0.0009, s)
    hyp = [MED + [s * 0.006, -0.01, 0.01], np.array([s * 0.026, 1.53, -0.008]), np.array([s * 0.024, 1.508, 0.02]), np.array([s * 0.01, 1.515, 0.045])]
    add('hypoglossal', 'Подъязычный нерв', 'Hypoglossal nerve', hyp, 0.0013, s,
        'XII пара черепных нервов. Проходит под нижней челюстью и управляет мышцами языка.')
    scm = C(side('{S} sternocleidomastoid', s))
    acc = [MED + [s * 0.01, -0.02, 0], np.array([s * 0.03, 1.55, -0.022]), scm + [0, 0.03, -0.012], scm + [s * 0.016, -0.02, -0.03], np.array([s * 0.07, 1.43, -0.06])]
    add('accessory', 'Добавочный нерв', 'Accessory nerve', acc, 0.0013, s,
        'XI пара черепных нервов. Управляет грудино-ключично-сосцевидной и трапециевидной мышцами — поворот головы и подъём плеч.')

print('nerves', len(nerves))

# ---------- геометрия трубок ----------
def smooth(pts, it=3):
    pts = np.array(pts, float)
    keep = [pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p - keep[-1]) > 1e-4: keep.append(p)
    pts = np.array(keep)
    if len(pts) < 3: return pts
    for _ in range(it):
        q = [pts[0]]
        for a, b in zip(pts[:-1], pts[1:]):
            q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        q.append(pts[-1]); pts = np.array(q)
    return pts
def resample(pts, step=0.004):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    n = max(2, int(d[-1] / step) + 1); t = np.linspace(0, d[-1], n)
    return np.stack([np.interp(t, d, pts[:, i]) for i in range(3)], 1)
def tube(pts, r, seg=8, taper=True):
    pts = resample(smooth(pts), step=max(0.002, r * 1.2))
    n = len(pts)
    T = np.gradient(pts, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-12
    up = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    N = np.cross(T[0], up); N /= np.linalg.norm(N)
    Ns = [N]
    for i in range(1, n):
        v = Ns[-1] - T[i] * np.dot(Ns[-1], T[i]); l = np.linalg.norm(v)
        Ns.append(v / l if l > 1e-9 else Ns[-1])
    Ns = np.array(Ns); Bs = np.cross(T, Ns)
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    rr = np.full(n, r)
    if taper and n > 4: rr *= np.linspace(1.0, 0.65, n)
    P = []; Nn = []
    for i in range(n):
        for a in ang:
            d = np.cos(a) * Ns[i] + np.sin(a) * Bs[i]
            P.append(pts[i] + rr[i] * d); Nn.append(d)
    idx = []
    for i in range(n - 1):
        for j in range(seg):
            a = i * seg + j; b = i * seg + (j + 1) % seg; c = a + seg; d2 = b + seg
            idx += [a, c, b, b, c, d2]
    # заглушки на концах
    for end, sign in ((0, -1), (n - 1, 1)):
        ci = len(P); P.append(pts[end]); Nn.append(T[end] * sign)
        for j in range(seg):
            a = end * seg + j; b = end * seg + (j + 1) % seg
            idx += ([ci, b, a] if sign < 0 else [ci, a, b])
    return np.array(P, np.float32), np.array(Nn, np.float32), np.array(idx, np.uint32)
def sphere(c, r, seg=10):
    P = []; Nn = []
    for i in range(seg + 1):
        th = np.pi * i / seg
        for j in range(seg):
            ph = 2 * np.pi * j / seg
            d = np.array([np.sin(th) * np.cos(ph), np.cos(th), np.sin(th) * np.sin(ph)])
            P.append(c + r * d); Nn.append(d)
    idx = []
    for i in range(seg):
        for j in range(seg):
            a = i * seg + j; b = i * seg + (j + 1) % seg; idx += [a, a + seg, b, b, a + seg, b + seg]
    return np.array(P, np.float32), np.array(Nn, np.float32), np.array(idx, np.uint32)

# ---------- запись в атлас ----------
if '--write' in sys.argv:
    atlas_path = OUT + 'atlas.json'
    atlas = json.load(open(atlas_path))
    atlas['parts'] = [p for p in atlas['parts'] if not p['id'].startswith('RU-')]
    atlas['concepts'] = [c for c in atlas['concepts'] if not c['id'].startswith('RU-')]
    atlas['chunks'] = [c for c in atlas['chunks'] if 'nerves' not in c['url']]
    ci = len(atlas['chunks'])
    buf = bytearray(); parts = []; concepts = {}; tri = 0
    def app(a):
        global buf
        pad = (-len(buf)) % 4; buf += b'\0' * pad; off = len(buf); buf += a.tobytes(); return off
    for k, nv in enumerate(nerves):
        if nv['key'] == 'sympathetic_ganglion':
            c = nv['pts'].mean(0); P, Nn, I = sphere(c, nv['r'])
        else:
            P, Nn, I = tube(nv['pts'], nv['r'], seg=8 if nv['r'] > 0.0014 else 6)
        pid = f'RU-N{k:03d}'
        sfx = ' (лев.)' if nv['side'] > 0 else ' (прав.)' if nv['side'] < 0 else ''
        esfx = ('Left ' if nv['side'] > 0 else 'Right ' if nv['side'] < 0 else '')
        n16 = np.clip(np.round(Nn * 32767), -32767, 32767).astype(np.int16)
        part = dict(id=pid, name=nv['ru'] + sfx, en=esfx + nv['en'], conceptId=f"RU-{nv['key']}", system='nervous', chunk=ci,
                    positions=app(P), normals=app(n16), indices=app(I), vertexCount=len(P), indexCount=len(I),
                    bounds=[P.min(0).round(6).tolist(), P.max(0).round(6).tolist()], schematic=True)
        tri += len(I) // 3
        parts.append(part)
        c = concepts.setdefault(nv['key'], dict(id=f"RU-{nv['key']}", name=nv['ru'] if nv['key'] not in ('spinal_root', 'intercostal') else
                                ('Спинномозговые нервы' if nv['key'] == 'spinal_root' else 'Межрёберные нервы'),
                                en=nv['en'] if nv['key'] not in ('spinal_root', 'intercostal') else ('Spinal nerves' if nv['key'] == 'spinal_root' else 'Intercostal nerves'),
                                elements=[], desc=nv['desc'], schematic=True))
        c['elements'].append(pid)
        if nv['desc'] and not c.get('desc'): c['desc'] = nv['desc']
    # отдельные понятия для каждого межрёберного и спинномозгового нерва
    for p in parts:
        if p['conceptId'] in ('RU-spinal_root', 'RU-intercostal'):
            base = re.sub(r' \((лев|прав)\.\)$', '', p['name'])
            key = 'RU-' + re.sub(r'\W+', '-', p['en'].replace('Left ', '').replace('Right ', ''))
            c = concepts.setdefault(key, dict(id=key, name=base, en=p['en'].replace('Left ', '').replace('Right ', ''), elements=[], schematic=True,
                                              desc=concepts[p['conceptId'][3:]]['desc'] if p['conceptId'] == 'RU-intercostal' else
                                              'Спинномозговой нерв выходит из позвоночного канала через межпозвоночное отверстие и несёт как двигательные, так и чувствительные волокна к своему участку тела.'))
            c['elements'].append(p['id'])
    concepts['spinal_root']['desc'] = 'Из спинного мозга выходят 31 пара спинномозговых нервов. Каждый покидает позвоночный канал через межпозвоночное отверстие; в шее, пояснице и крестце они сплетаются в сплетения, из которых формируются нервы рук и ног.'
    allc = dict(id='RU-peripheral', name='Периферическая нервная система', en='Peripheral nervous system',
                elements=[p['id'] for p in parts if p['conceptId'] != 'RU-spinal_cord'], schematic=True,
                desc='Нервы, соединяющие головной и спинной мозг с телом: 31 пара спинномозговых нервов с их сплетениями, черепные нервы и вегетативный симпатический ствол.')
    concepts['peripheral'] = allc
    name = 'models/nerves.bin'
    open(OUT + 'nerves.bin', 'wb').write(buf)
    gz = gzip.compress(bytes(buf), 9); open(OUT + 'nerves.bin.gz', 'wb').write(gz)
    atlas['chunks'].append(dict(url=name, bytes=len(buf), gzip=name + '.gz', gzipBytes=len(gz)))
    atlas['parts'] += parts
    atlas['concepts'] += list(concepts.values())
    for c in atlas['concepts']:  # добавить в «нервную систему»
        if (c.get('en') or '').lower() == 'nervous system':
            c['elements'] = [e for e in c['elements'] if not e.startswith('RU-')] + [p['id'] for p in parts]
    atlas['triangles'] = atlas.get('triangles', 0) + tri
    json.dump(atlas, open(atlas_path, 'w'), ensure_ascii=False, separators=(',', ':'))
    print('parts', len(parts), 'concepts', len(concepts), 'tri', tri, 'bytes', len(buf), 'gz', len(gz))
