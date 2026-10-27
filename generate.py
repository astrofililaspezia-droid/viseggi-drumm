from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from obspy import UTCDateTime
from obspy.clients.fdsn import Client

out = Path('site'); out.mkdir(exist_ok=True)
now = datetime.now(timezone.utc)
end = now - timedelta(minutes=5)
start = end - timedelta(hours=24)
status = dict(station='IV.LSPZ.00.EHZ', generated_utc=now.isoformat(), ok=False)
try:
    client = Client('https://webservices.ingv.it', timeout=90)
    st = client.get_waveforms('IV','LSPZ','00','EHZ',UTCDateTime(start),UTCDateTime(end))
    st.merge(method=1, fill_value=None)
    fig, axs = plt.subplots(24, 1, figsize=(12, 14))
    fig.patch.set_facecolor('#0b1629')
    # Tracce a quattro colori, come il drum Home Assistant.
    trace_colors = ('#ff344b', '#25ca65', '#e1c83f', '#3488ff')
    for i, ax in enumerate(axs):
        hour_start = start + timedelta(hours=i)
        hour_end = hour_start + timedelta(hours=1)
        ax.set_facecolor('#101e33')
        ax.set_xlim(0, 60)
        ax.set_ylim(-1.4, 1.4)
        ax.set_yticks([])
        ax.set_ylabel(hour_start.strftime('%H:%M'), rotation=0, labelpad=27, color='#b8cce8', fontsize=8)
        ax.set_xticks([0,15,30,45,60]); ax.grid(axis='x', alpha=.2)
        if i != 23: ax.set_xticklabels([])
        else: ax.tick_params(axis='x', colors='#b8cce8')
        for spine in ax.spines.values(): spine.set_visible(False)
        for tr in st:
            segment = tr.copy().trim(UTCDateTime(hour_start), UTCDateTime(hour_end), pad=False)
            if segment.stats.npts < 2: continue
            vals = np.ma.asarray(segment.data, dtype=float).filled(np.nan) if np.ma.isMaskedArray(segment.data) else np.asarray(segment.data, dtype=float)
            stride = max(1, int(np.ceil(len(vals) / 2500)))
            vals = vals[::stride]
            times = np.arange(len(vals)) * stride / segment.stats.sampling_rate / 60 + (segment.stats.starttime.datetime.replace(tzinfo=timezone.utc) - hour_start).total_seconds()/60
            good = np.isfinite(vals)
            if not good.any(): continue
            vals = vals - np.nanmedian(vals[good])
            scale = max(1.0, float(np.nanpercentile(np.abs(vals[good]), 98)))
            ax.plot(times, np.clip(vals / scale, -1.3, 1.3), color=trace_colors[i % len(trace_colors)], lw=.65)
    fig.subplots_adjust(top=.93, bottom=.05, left=.105, right=.97, hspace=.23)
    fig.text(.105,.975,'MONTE VISEGGI  |  DRUM SISMICO 24 ORE',color='white',weight='bold',fontsize=16,va='top')
    fig.text(.105,.949,'INGV · IV.LSPZ.00.EHZ · orari UTC · tracce normalizzate per ora',color='#a6bdd8',fontsize=9,va='top')
    fig.savefig(out/'drum.png',dpi=130,facecolor=fig.get_facecolor())
    plt.close(fig)
    status['ok'] = True
except Exception as e:
    status['error'] = f'{type(e).__name__}: {e}'
    print('ATTENZIONE: acquisizione non riuscita:', status['error'])
(out/'status.json').write_text(json.dumps(status,indent=2,ensure_ascii=False),encoding='utf8')
image = '<img src="drum.png" alt="Drum sismico IV.LSPZ ultime 24 ore" style="max-width:100%;height:auto">' if status['ok'] else '<p>Tracciato non disponibile: impossibile acquisire i dati più recenti da INGV. Nessun dato simulato.</p>'
html = '''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="900"><title>Monte Viseggi: drum LSPZ</title><style>body{margin:0;background:#0b1629;color:#edf5ff;font:16px Arial,sans-serif}main{max-width:1100px;margin:auto;padding:24px}p{color:#bed0e5}</style></head><body><main><h1>Monte Viseggi · Drum sismico 24 ore</h1><p>INGV / Istituto Culturale Astrofili Spezzini · IV.LSPZ · canale EHZ · orari UTC</p>''' + image + '<p>Ultimo tentativo di aggiornamento UTC: '+now.strftime('%Y-%m-%d %H:%M')+'</p><p>Fonte INGV FDSN. Ampiezze normalizzate per ogni ora, non misure calibrate di intensità.</p></main></body></html>'
(out/'index.html').write_text(html,encoding='utf8')
