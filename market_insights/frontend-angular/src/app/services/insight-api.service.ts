import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class InsightApiService {
  private http = inject(HttpClient);

  runEtl(ticker: string, provider: string) {
    return this.http.post(`/api/etl/run?ticker=${encodeURIComponent(ticker)}&provider=${encodeURIComponent(provider)}`, {});
  }

  getInsight(ticker: string) {
    return this.http.get<any>(`/api/insights/${encodeURIComponent(ticker)}`);
  }

  getComparable(ticker: string) {
    return this.http.get<any>(`/api/insights/${encodeURIComponent(ticker)}/comparable`);
  }

  getHybrid(ticker: string) {
    return this.http.get<any>(`/api/insights/${encodeURIComponent(ticker)}/hybrid`);
  }

  getFairValue(ticker: string) {
    return this.http.get<any>(`/api/fair-value/${encodeURIComponent(ticker)}`);
  }

  getSources(ticker: string) {
    return this.http.get<any>(`/api/rag/sources/${encodeURIComponent(ticker)}`);
  }
}
