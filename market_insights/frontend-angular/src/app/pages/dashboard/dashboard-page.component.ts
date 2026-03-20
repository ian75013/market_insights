import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { MetricCardComponent } from '../../components/metric-card/metric-card.component';
import { InsightApiService } from '../../services/insight-api.service';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [CommonModule, FormsModule, MetricCardComponent],
  template: `
    <div class="container">
      <div class="toolbar card">
        <div>
          <div class="label">Market Insight Studio</div>
          <h1 style="margin:6px 0 0 0">Hybrid Insight Dashboard</h1>
          <div class="muted">Technique, juste valeur, RAG et analyse comparable dans une interface unique.</div>
        </div>
        <div class="row">
          <input [(ngModel)]="ticker" placeholder="Ticker (AAPL, MSFT...)" />
          <select [(ngModel)]="provider">
            <option value="sample">sample</option>
            <option value="stooq">stooq</option>
            <option value="ibkr">ibkr</option>
          </select>
          <button (click)="loadAll()">Charger l'analyse</button>
          <button class="secondary" (click)="runEtl()">Lancer ETL</button>
        </div>
      </div>

      <div class="grid grid-4" *ngIf="hybrid">
        <app-metric-card label="Ticker" [value]="hybrid.ticker"></app-metric-card>
        <app-metric-card label="Verdict" [value]="hybrid.verdict"></app-metric-card>
        <app-metric-card label="Prix actuel" [value]="fmt(hybrid.hybrid?.current_price)"></app-metric-card>
        <app-metric-card label="Upside modèle" [value]="fmt(hybrid.hybrid?.upside_pct) + '%'" hint="Juste valeur vs prix courant"></app-metric-card>
      </div>

      <div class="grid grid-2" *ngIf="hybrid">
        <div class="card">
          <div class="section-title">
            <h2>Résumé exécutif</h2>
            <span class="tag" [class.green]="hybrid.verdict==='bullish'" [class.red]="hybrid.verdict==='bearish'" [class.amber]="hybrid.verdict==='neutral'">
              {{ hybrid.verdict }}
            </span>
          </div>
          <p>{{ hybrid.executive_summary }}</p>
          <div class="row">
            <span class="tag">Opinion: {{ hybrid.hybrid?.opinion }}</span>
            <span class="tag">Confiance: {{ pct(hybrid.hybrid?.confidence) }}</span>
          </div>
        </div>
        <div class="card">
          <div class="section-title">
            <h2>Fair Value</h2>
            <span class="tag">modèle</span>
          </div>
          <div class="grid grid-2">
            <div>
              <div class="label">Juste valeur</div>
              <div class="value">{{ fmt(fairValue?.fair_value) }}</div>
            </div>
            <div>
              <div class="label">Méthode</div>
              <div class="value" style="font-size:18px">{{ fairValue?.method || 'baseline' }}</div>
            </div>
          </div>
          <div class="muted" style="margin-top:12px">{{ fairValue?.explanation || 'Estimation modèle à comparer au scénario technique.' }}</div>
        </div>
      </div>

      <div class="grid grid-3" *ngIf="hybrid">
        <div class="card">
          <div class="section-title"><h3>Analyse comparable</h3><span class="tag">technique</span></div>
          <div class="list">
            <div class="list-item"><b>Opinion</b><br>{{ comparable?.summary?.opinion || hybrid.comparable?.summary?.opinion }}</div>
            <div class="list-item"><b>Tendance CT</b><br>{{ comparable?.summary?.short_trend || hybrid.comparable?.summary?.short_trend }}</div>
            <div class="list-item"><b>Tendance LT</b><br>{{ comparable?.summary?.long_trend || hybrid.comparable?.summary?.long_trend }}</div>
            <div class="list-item"><b>Narrative</b><br>{{ comparable?.narrative || hybrid.comparable?.narrative }}</div>
          </div>
        </div>
        <div class="card">
          <div class="section-title"><h3>Catalyseurs RAG</h3><span class="tag">context</span></div>
          <div class="list">
            <div class="list-item" *ngFor="let c of hybrid.rag?.top_catalysts">{{ c }}</div>
          </div>
        </div>
        <div class="card">
          <div class="section-title"><h3>Risques</h3><span class="tag">watchlist</span></div>
          <div class="list">
            <div class="list-item" *ngFor="let r of hybrid.rag?.top_risks">{{ r }}</div>
          </div>
        </div>
      </div>

      <div class="grid grid-2" *ngIf="hybrid">
        <div class="card">
          <div class="section-title"><h3>Niveaux techniques</h3><span class="tag">supports / résistances</span></div>
          <div class="grid grid-2">
            <div class="list-item"><b>Support</b><br>{{ fmt(technical?.levels?.support) }}</div>
            <div class="list-item"><b>Résistance</b><br>{{ fmt(technical?.levels?.resistance) }}</div>
            <div class="list-item"><b>Objectif 1</b><br>{{ fmt(technical?.levels?.target_1) }}</div>
            <div class="list-item"><b>Objectif 2</b><br>{{ fmt(technical?.levels?.target_2) }}</div>
          </div>
        </div>
        <div class="card">
          <div class="section-title"><h3>Signaux</h3><span class="tag">engine</span></div>
          <pre class="chart">{{ technical?.signals | json }}</pre>
        </div>
      </div>

      <div class="card" *ngIf="sources?.sources?.length">
        <div class="section-title"><h3>Sources RAG</h3><span class="tag">traceability</span></div>
        <div class="list">
          <div class="list-item" *ngFor="let s of sources.sources">
            <b>{{ s.title || s.source || 'source' }}</b>
            <div class="muted">{{ s.snippet || s.summary || 'Aperçu indisponible' }}</div>
          </div>
        </div>
      </div>

      <div class="card" *ngIf="message">
        <div class="section-title"><h3>Journal</h3></div>
        <div>{{ message }}</div>
      </div>
    </div>
  `,
})
export class DashboardPageComponent {
  private api = inject(InsightApiService);

  ticker = 'AAPL';
  provider = 'sample';
  message = 'Prêt.';

  hybrid: any;
  fairValue: any;
  comparable: any;
  technical: any;
  sources: any;

  runEtl() {
    this.message = `ETL en cours pour ${this.ticker} via ${this.provider}...`;
    this.api.runEtl(this.ticker, this.provider).subscribe({
      next: (res) => this.message = `ETL terminé: ${JSON.stringify(res)}`,
      error: (err) => this.message = `Erreur ETL: ${err?.error?.detail || err.message}`,
    });
  }

  loadAll() {
    this.message = `Chargement de l'analyse hybride pour ${this.ticker}...`;
    forkJoin({
      hybrid: this.api.getHybrid(this.ticker),
      fairValue: this.api.getFairValue(this.ticker),
      comparable: this.api.getComparable(this.ticker),
      technical: this.api.getInsight(this.ticker),
      sources: this.api.getSources(this.ticker),
    }).subscribe({
      next: ({ hybrid, fairValue, comparable, technical, sources }) => {
        this.hybrid = hybrid;
        this.fairValue = fairValue;
        this.comparable = comparable;
        this.technical = technical;
        this.sources = sources;
        this.message = `Analyse chargée pour ${this.ticker}.`;
      },
      error: (err) => {
        this.message = `Erreur de chargement: ${err?.error?.detail || err.message}`;
      },
    });
  }

  fmt(v: any): string {
    const n = Number(v);
    return Number.isFinite(n) ? n.toFixed(2) : '-';
  }

  pct(v: any): string {
    const n = Number(v);
    return Number.isFinite(n) ? `${Math.round(n * 100)}%` : '-';
  }
}
