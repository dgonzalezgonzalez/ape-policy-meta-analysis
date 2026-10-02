"""Vector figures with explicit samples, scales and interval definitions."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from paths import OUTPUT

def main():
    figdir=OUTPUT/'figures'; figdir.mkdir(exist_ok=True)
    R=json.loads((OUTPUT/'results.json').read_text())
    d=pd.read_csv(OUTPUT/'analysis_sample.csv')
    plt.rcParams.update({'font.family':'serif','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
        'pdf.fonttype':42,'savefig.bbox':'tight'})
    fig,axes=plt.subplots(1,2,figsize=(6.5,3.0),sharey=True)
    for ax,est,title in zip(axes,['binary','continuous'],['Binary treatments','Continuous exposures']):
        a=np.sort(d.loc[d.estimand.eq(est),'abs_sde'].to_numpy())
        ax.step(np.maximum(a,.001),np.arange(1,len(a)+1)/len(a),where='post',color='black',lw=1.4)
        ax.set_xscale('log'); ax.set_xlim(.001,5); ax.set_ylim(0,1.01)
        ax.set_xticks([.001,.01,.1,1,5],['.001','.01','.1','1','5'])
        ax.set_title(title + ' (N=' + str(len(a)) + ')',fontsize=10)
        ax.set_xlabel('Absolute SDE (log scale)'); ax.grid(axis='y',color='.88',lw=.6)
    axes[0].set_ylabel('Fraction at or below magnitude')
    fig.tight_layout(); fig.savefig(figdir/'magnitude_cdf.pdf',metadata={'CreationDate':None,'ModDate':None}); plt.close(fig)
    labels={'health_human_capital':'Health and human capital','labor_income':'Labour and income',
        'environment_energy':'Environment and energy','taxation_prices':'Taxation and prices',
        'regulation_competition':'Regulation and competition','housing_infrastructure':'Housing and infrastructure',
        'finance_governance':'Finance and governance','other':'Other'}
    summaries=pd.DataFrame(R['domains'])
    fig,axes=plt.subplots(1,2,figsize=(7,4.1),sharex=True)
    domains=list(labels)
    for ax,est,title in zip(axes,['binary','continuous'],['Binary treatments','Continuous exposures']):
        s=summaries[summaries.estimand.eq(est)].set_index('domain')
        for i,domain in enumerate(domains):
            if domain in s.index:
                r=s.loc[domain]
                ax.plot([r.ci_lo,r.ci_hi],[i,i],color='black',lw=1.1)
                ax.plot(r.estimate,i,'o',color='black',ms=4)
                ax.text(.97,i,'N='+str(int(r.k)),ha='right',va='center',transform=ax.get_yaxis_transform(),fontsize=8,
                        bbox={'facecolor':'white','edgecolor':'none','pad':1})
        ax.axvline(0,color='.5',ls='--',lw=.8); ax.set_yticks(range(len(domains)))
        ax.set_yticklabels([labels[x] for x in domains] if est=='binary' else ['']*len(domains),fontsize=9)
        ax.invert_yaxis(); ax.set_title(title,fontsize=10); ax.set_xlabel('Favourable-direction SDE')
    all_lo=summaries.ci_lo.min(); all_hi=summaries.ci_hi.max()
    axes[0].set_xlim(all_lo-.1,all_hi+.12)
    fig.tight_layout(); fig.savefig(figdir/'domains.pdf',metadata={'CreationDate':None,'ModDate':None}); plt.close(fig)
    print('Generated two vector figures')

if __name__=='__main__':
    main()
