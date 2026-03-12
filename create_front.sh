#!/bin/bash

mkdir -p market_insights/frontend-angular/src/app/services
mkdir -p market_insights/frontend-angular/src/app/components/insight

cd market_insights/frontend-angular

cat > package.json <<'EOF'
{
  "name": "market-insights-ui",
  "version": "1.0.0",
  "scripts": {
    "start": "ng serve --proxy-config proxy.conf.json",
    "build": "ng build"
  },
  "dependencies": {
    "@angular/animations": "^17.0.0",
    "@angular/common": "^17.0.0",
    "@angular/compiler": "^17.0.0",
    "@angular/core": "^17.0.0",
    "@angular/forms": "^17.0.0",
    "@angular/platform-browser": "^17.0.0",
    "@angular/platform-browser-dynamic": "^17.0.0",
    "@angular/router": "^17.0.0",
    "rxjs": "~7.8.0",./c
    "zone.js": "~0.14.0"
  }
}
EOF

cat > proxy.conf.json <<'EOF'
{
  "/api": {
    "target": "http://localhost:8000",
    "secure": false,
    "changeOrigin": true
  }
}
EOF

cat > src/app/services/insight.service.ts <<'EOF'
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class InsightService {

  constructor(private http: HttpClient) {}

  getInsight(ticker: string) {
    return this.http.get(`/api/insights/${ticker}`);
  }

  getFairValue(ticker: string) {
    return this.http.get(`/api/fair-value/${ticker}`);
  }

  getSources(ticker: string) {
    return this.http.get(`/api/rag/sources/${ticker}`);
  }
}
EOF

cat > src/app/components/insight/insight.component.ts <<'EOF'
import { Component } from '@angular/core';
import { InsightService } from '../../services/insight.service';

@Component({
  selector: 'app-insight',
  templateUrl: './insight.component.html'
})
export class InsightComponent {

  ticker = "AAPL";
  insight: any;

  constructor(private service: InsightService) {}

  loadInsight() {
    this.service.getInsight(this.ticker)
      .subscribe(data => this.insight = data);
  }
}
EOF

cat > src/app/components/insight/insight.component.html <<'EOF'
<div style="padding:20px">

<h2>Market Insight</h2>

<input [(ngModel)]="ticker" placeholder="Ticker"/>
<button (click)="loadInsight()">Analyse</button>

<div *ngIf="insight">

<h3>{{insight.ticker}}</h3>

<p><b>Opinion :</b> {{insight.summary?.opinion}}</p>
<p><b>Tendance CT :</b> {{insight.summary?.short_trend}}</p>
<p><b>Tendance LT :</b> {{insight.summary?.long_trend}}</p>

<p><b>Prix :</b> {{insight.last_price}}</p>

<p>{{insight.narrative}}</p>

</div>

</div>
EOF

echo "Projet Angular créé."