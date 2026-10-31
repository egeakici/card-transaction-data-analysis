"""All paper figures share one style, 300-dpi PNG and vector PDF exports."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from .common import CONFIG,OUT

plt.style.use(CONFIG/'paper.mplstyle')


def save(fig,name):
    fig.savefig(OUT/'figures'/f'{name}.png',dpi=300,bbox_inches='tight')
    fig.savefig(OUT/'figures'/f'{name}.pdf',bbox_inches='tight',metadata={'Creator':'data_profile; seed=42'})
    plt.close(fig)


def heatmap(values,rows,columns,title,name,cbar='Share',vmin=None,vmax=None):
    fig,ax=plt.subplots(figsize=(max(6,len(columns)*.55),max(4,len(rows)*.35)))
    image=ax.imshow(np.asarray(values,dtype=float),aspect='auto',cmap='viridis',vmin=vmin,vmax=vmax)
    ax.set(xticks=range(len(columns)),xticklabels=columns,yticks=range(len(rows)),yticklabels=rows,title=title)
    plt.setp(ax.get_xticklabels(),rotation=70,ha='right')
    fig.colorbar(image,ax=ax,label=cbar,shrink=.8);save(fig,name)


def bar(values,labels,title,name,xlabel='Transactions',log=False):
    fig,ax=plt.subplots(figsize=(8,max(4,len(labels)*.3)))
    ax.barh(list(reversed(labels)),list(reversed(values)),color='#346e91')
    if log:ax.set_xscale('log')
    ax.set(title=title,xlabel=xlabel);save(fig,name)
